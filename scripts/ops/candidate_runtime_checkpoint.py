#!/usr/bin/env python3
"""Operator-owned cold-volume rollback checkpoints; never stops/starts services."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import subprocess
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = 1
STORES = {
    "postgres": ("db", "/var/lib/postgresql/data"),
    "redis": ("redis", "/data"),
    "neo4j": ("neo4j", "/data"),
}
ALL_STORES = (*STORES, "chroma")
REPO = Path(__file__).resolve().parents[2]
IMAGE_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,100}\Z")
ID_RE = re.compile(r"cp-[a-zA-Z0-9_-]{1,120}\Z")
# Read-only source or explicitly selected target mounts; no networking/socket.
ARCHIVER = r"""
import hashlib, json, os, pathlib, shutil, stat, sys, tarfile
root = pathlib.Path('/store')
def inventory():
    rows = []
    for p in [root, *sorted(root.rglob('*'))]:
        st = p.lstat()
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
            raise SystemExit('unsupported non-regular storage member')
        row = {'name': '.' if p == root else p.relative_to(root).as_posix(),
               'mode': stat.S_IMODE(st.st_mode), 'uid': st.st_uid,
               'gid': st.st_gid, 'kind': 'file' if p.is_file() else 'dir'}
        if p.is_file():
            digest = hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda: f.read(1024*1024), b''):
                    digest.update(chunk)
            row.update(size=st.st_size, sha256=digest.hexdigest())
        rows.append(row)
    return rows
mode = sys.argv[1]
if mode == 'capture':
    inventory()  # Reject links/devices/sockets before producing archive bytes.
    with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz', format=tarfile.PAX_FORMAT) as tar:
        for p in [root, *sorted(root.rglob('*'))]:
            tar.add(p, arcname='.' if p == root else p.relative_to(root).as_posix(), recursive=False)
elif mode == 'inventory':
    print(json.dumps(inventory(), sort_keys=True))
elif mode == 'restore':
    # Host validation completed before this helper/target mutation. Revalidate here.
    with tarfile.open('/checkpoint/archive.tar.gz', 'r:gz') as tar:
        seen = set()
        for m in tar.getmembers():
            p = pathlib.PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or not (m.isfile() or m.isdir()) or m.name in seen:
                raise SystemExit('unsafe archive member')
            seen.add(m.name)
        for p in root.iterdir():
            if p.is_dir() and not p.is_symlink(): shutil.rmtree(p)
            else: p.unlink()
        tar.extractall(root, numeric_owner=True, filter='fully_trusted')
    print(json.dumps(inventory(), sort_keys=True))
else:
    raise SystemExit('unsupported mode')
"""


class CheckpointError(RuntimeError):
    pass


def require(condition: Any, message: str) -> None:
    if not condition:
        raise CheckpointError(message)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class Docker:
    def run(self, *args: str, timeout: int = 60, output: Any = None) -> str:
        try:
            result = subprocess.run(
                ["docker", *args],
                stdout=output or subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=True,
            )
        except (subprocess.SubprocessError, OSError, KeyboardInterrupt) as exc:
            # A timed-out Docker CLI does not prove its helper stopped. Clean only
            # the unique helper we launched, after rechecking its ownership label.
            if args and args[0] == "run" and "--name" in args:
                name = args[args.index("--name") + 1]
                if name.startswith("codexify-checkpoint-helper-"):
                    with contextlib.suppress(Exception):
                        probe = subprocess.run(
                            ["docker", "inspect", name],
                            capture_output=True,
                            timeout=15,
                            check=True,
                        )
                        resource = json.loads(probe.stdout)[0]
                        if (
                            labels(resource).get("codexify.proof")
                            == "candidate-checkpoint"
                        ):
                            subprocess.run(
                                ["docker", "rm", "-f", resource["Id"]],
                                capture_output=True,
                                timeout=30,
                                check=True,
                            )
            # Docker diagnostics/command environment may contain credentials.
            raise CheckpointError("Docker operation failed; inspect privately") from exc
        return "" if output else result.stdout.decode()

    def json(self, *args: str) -> Any:
        return json.loads(self.run(*args))

    def containers(self) -> list[dict]:
        ids = self.run("ps", "-aq").split()
        return self.json("inspect", *ids) if ids else []

    def volume(self, name: str) -> dict:
        values = self.json("volume", "inspect", name)
        require(len(values) == 1, "ambiguous volume")
        v = values[0]
        require(
            v["Driver"] == "local" and not v.get("Options"),
            "only Docker-managed local, non-bind volumes are supported",
        )
        return v

    def image(self, image: str) -> dict:
        require(IMAGE_RE.fullmatch(image), "explicit immutable image ID is required")
        values = self.json("image", "inspect", image)
        require(
            len(values) == 1 and values[0]["Id"] == image,
            "pinned image must already exist locally",
        )
        return values[0]


def labels(c: dict) -> dict:
    return c.get("Config", {}).get("Labels") or {}


def owner(c: dict) -> str | None:
    return labels(c).get("com.docker.compose.project")


def project_name(value: str) -> str:
    require(NAME_RE.fullmatch(value), "invalid explicit project identity")
    return value


def public_volume(v: dict) -> dict:
    ls = v.get("Labels") or {}
    return {
        k: v.get(k) for k in ("Name", "Driver", "Scope", "CreatedAt", "Mountpoint")
    } | {
        "labels": {
            k: ls[k]
            for k in (
                "com.docker.compose.project",
                "codexify.storage.contract",
                "codexify.storage.project",
                "codexify.storage.admission_id",
            )
            if k in ls
        }
    }


def inspect_project(docker: Docker, project: str, *, closed: bool = False) -> dict:
    project_name(project)
    all_containers = docker.containers()
    selected = [c for c in all_containers if owner(c) == project]
    require(selected, "explicit project has no containers")
    services: dict[str, dict] = {}
    for c in selected:
        name = labels(c).get("com.docker.compose.service")
        require(name and name not in services, "missing/ambiguous service identity")
        services[name] = c
    volumes: dict[str, dict] = {}
    for store, (service, target) in STORES.items():
        require(service in services, f"missing {store} service")
        mounts = [m for m in services[service]["Mounts"] if m["Destination"] == target]
        require(
            len(mounts) == 1 and mounts[0]["Type"] == "volume",
            f"missing/ambiguous {store} volume",
        )
        volumes[store] = docker.volume(mounts[0]["Name"])
    chroma_names = {
        m["Name"]
        for c in selected
        for m in c["Mounts"]
        if m["Destination"] == "/app/.chroma" and m["Type"] == "volume"
    }
    require(len(chroma_names) == 1, "missing/ambiguous admitted Chroma volume")
    volumes["chroma"] = docker.volume(chroma_names.pop())
    admission = volumes["chroma"].get("Labels") or {}
    require(
        admission.get("codexify.storage.contract") == "ADR-101"
        and admission.get("codexify.storage.project") == project
        and admission.get("codexify.storage.admission_id"),
        "wrong Chroma admission owner",
    )
    names = {v["Name"] for v in volumes.values()}
    require(len(names) == 4, "stores must use four distinct volumes")
    for c in all_containers:
        if any(m.get("Name") in names for m in c["Mounts"]):
            require(
                owner(c) == project, "protected volume attached to unrelated project"
            )
    if closed:
        for c in selected:
            state = c["State"]
            require(
                not state["Running"]
                and not state.get("Paused")
                and state["Status"] == "exited"
                and state["ExitCode"] == 0
                and not state.get("OOMKilled"),
                "all application/storage services must be stopped cleanly",
            )
        # Redis is in-memory; a cold volume alone would omit unpersisted keys.
        redis = services["redis"]
        log = docker.run("logs", "--since", redis["State"]["StartedAt"], redis["Id"])
        require(
            0
            <= log.rfind("User requested shutdown")
            < log.rfind("DB saved on disk")
            < log.rfind("Redis is now ready to exit"),
            "Redis clean shutdown with final persisted RDB is unproven",
        )
    return {"project": project, "containers": selected, "volumes": volumes}


def within(path: Path, base: Path) -> bool:
    return path == base or base in path.parents


def no_symlinks(path: Path) -> None:
    require(path.is_absolute(), "absolute destination/checkpoint path is required")
    require(
        not any(p.is_symlink() for p in (path, *path.parents)),
        "symlinked checkpoint paths are forbidden",
    )


def safe_destination(value: str | Path, snapshot: dict | None = None) -> Path:
    path = Path(value)
    no_symlinks(path)
    path = path.resolve()
    forbidden = [
        Path("/private/tmp"),
        Path("/tmp").resolve(),
        Path("/var/lib/docker/volumes"),
        REPO.resolve(),
    ]
    with contextlib.suppress(subprocess.SubprocessError, OSError):
        result = subprocess.check_output(
            ["git", "-C", str(REPO), "worktree", "list", "--porcelain"], text=True
        )
        forbidden.extend(
            Path(line[9:]).resolve()
            for line in result.splitlines()
            if line.startswith("worktree ")
        )
    if snapshot:
        for v in snapshot["volumes"].values():
            forbidden.append(Path(v["Mountpoint"]))
        for c in snapshot["containers"]:
            wd = labels(c).get("com.docker.compose.project.working_dir")
            if wd:
                forbidden.append(Path(wd).resolve())
            for m in c["Mounts"]:
                if m["RW"]:
                    forbidden.append(Path(m["Destination"]))
                    source = m["Source"].removeprefix("/host_mnt")
                    forbidden.append(Path(source).resolve())
    require(
        path not in (Path("/"), Path("/Volumes"), Path("/Volumes/Dev_SSD")),
        "broad destination root is forbidden",
    )
    require(
        not any(within(path, base) for base in forbidden),
        "destination is inside temporary/source/worktree/runtime storage",
    )
    return path


def identity(snapshot: dict) -> dict:
    return {
        "containers": sorted(
            (
                c["Id"],
                c["Image"],
                c["State"]["StartedAt"],
                c["State"].get("FinishedAt"),
                c["RestartCount"],
            )
            for c in snapshot["containers"]
        ),
        "volumes": {k: public_volume(v) for k, v in snapshot["volumes"].items()},
    }


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def archive_inventory(path: Path) -> list[dict]:
    rows = []
    seen = set()
    with tarfile.open(path, "r:gz") as archive:
        for m in archive.getmembers():
            name = PurePosixPath(m.name)
            require(
                not name.is_absolute()
                and ".." not in name.parts
                and (m.isfile() or m.isdir())
                and str(name) not in seen,
                "unsafe/duplicate archive member",
            )
            seen.add(str(name))
            row = {
                "name": "." if str(name) == "." else str(name),
                "mode": m.mode,
                "uid": m.uid,
                "gid": m.gid,
                "kind": "file" if m.isfile() else "dir",
            }
            if m.isfile():
                h = hashlib.sha256()
                f = archive.extractfile(m)
                require(f is not None, "unreadable archive member")
                with f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                row.update(size=m.size, sha256=h.hexdigest())
            rows.append(row)
    require(rows and rows[0]["name"] == ".", "missing archive root")
    by_name = {row["name"]: row for row in rows}
    for name in by_name:
        for parent in PurePosixPath(name).parents:
            if str(parent) in by_name:
                require(
                    by_name[str(parent)]["kind"] == "dir", "archive file is a parent"
                )
    return sorted(rows, key=lambda row: row["name"])


def helper_args(
    image: str, volume: str, mode: str, archive: Path | None = None
) -> list[str]:
    name = "codexify-checkpoint-helper-" + uuid.uuid4().hex
    args = [
        "run",
        "--rm",
        "--pull=never",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--user",
        "0:0",
        "--cpus=1",
        "--memory=512m",
        "--pids-limit=64",
        "--label",
        "codexify.proof=candidate-checkpoint",
        "--mount",
        f"type=volume,source={volume},target=/store,volume-nocopy"
        + (",readonly" if mode != "restore" else ""),
    ]
    if archive:
        args += [
            "--mount",
            f"type=bind,source={archive},target=/checkpoint/archive.tar.gz,readonly",
        ]
    return args + ["--entrypoint", "python", image, "-c", ARCHIVER, mode]


def check_chroma_archive(path: Path, volume: dict, project: str) -> None:
    with tarfile.open(path, "r:gz") as tar:
        member = tar.extractfile(".codexify-storage-admission.json")
        require(member is not None, "missing Chroma admission marker")
        with member:
            marker = json.load(member)
    ls = volume["labels"] if "labels" in volume else volume.get("Labels", {})
    require(
        marker.get("contract") == "ADR-101"
        and marker.get("project") == project
        and marker.get("volume") == volume["Name"]
        and marker.get("admission_id") == ls.get("codexify.storage.admission_id")
        and marker.get("created_at") == volume["CreatedAt"],
        "Chroma archive marker/volume admission mismatch",
    )


def verify_payload(root: Path, manifest: dict) -> None:
    require(
        manifest.get("schema") == SCHEMA
        and manifest.get("create_result") == "PASS"
        and manifest.get("validation_result") == "PASS",
        "invalid checkpoint schema/result",
    )
    project_name(manifest["project"])
    require(ID_RE.fullmatch(manifest["checkpoint_id"]), "invalid checkpoint identity")
    require(
        IMAGE_RE.fullmatch(manifest["helper_image"]), "invalid checkpoint helper image"
    )
    require(set(manifest["stores"]) == set(ALL_STORES), "missing required store")
    expected = {f"{store}.tar.gz" for store in ALL_STORES} | {"runtime-config.json"}
    require(set(manifest["files"]) == expected, "missing/unknown checkpoint artifacts")
    for name, meta in manifest["files"].items():
        path = root / name
        require(path.is_file() and not path.is_symlink(), "missing artifact")
        require(
            path.stat().st_size == meta["bytes"] and digest(path) == meta["sha256"],
            "checkpoint integrity mismatch",
        )
    for store in ALL_STORES:
        data = manifest["stores"][store]
        require(data["archive"] == f"{store}.tar.gz", "invalid store artifact binding")
        require(
            archive_inventory(root / data["archive"]) == data["inventory"],
            "archive metadata/content mismatch",
        )
    check_chroma_archive(
        root / "chroma.tar.gz",
        manifest["stores"]["chroma"]["volume"],
        manifest["project"],
    )


def validate_checkpoint(path: str | Path, project: str) -> dict:
    root = safe_destination(path)
    require(
        root.is_dir() and ID_RE.fullmatch(root.name), "incomplete/missing checkpoint"
    )
    try:
        manifest = json.loads((root / "manifest.json").read_text())
        complete = json.loads((root / "COMPLETE").read_text())
        require(
            root.name == manifest["checkpoint_id"]
            and root.parent.name == project
            and manifest["project"] == project,
            "checkpoint project/identity mismatch",
        )
        require(
            complete
            == {"schema": SCHEMA, "manifest_sha256": digest(root / "manifest.json")},
            "invalid completion marker/manifest hash",
        )
        require(
            not (root / "manifest.json").is_symlink()
            and not (root / "COMPLETE").is_symlink(),
            "symlinked checkpoint metadata",
        )
        require(
            {p.name for p in root.iterdir()}
            == set(manifest["files"]) | {"manifest.json", "COMPLETE"},
            "unexpected checkpoint members",
        )
        verify_payload(root, manifest)
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as exc:
        raise CheckpointError("invalid/incomplete checkpoint") from exc
    return manifest


def plan(docker: Docker, project: str, destination: str, helper_image: str) -> dict:
    snapshot = inspect_project(docker, project)
    dest = safe_destination(destination, snapshot)
    docker.image(helper_image)
    blockers = []
    if any(c["State"]["Running"] for c in snapshot["containers"]):
        blockers.append("application/storage writers remain running; create refuses")
    return {
        "status": "BLOCKED" if blockers else "PLANNED",
        "project": project,
        "OBSERVED": {
            "services": [
                {
                    "service": labels(c)["com.docker.compose.service"],
                    "container": c["Id"],
                    "image": c["Image"],
                    "running": c["State"]["Running"],
                }
                for c in snapshot["containers"]
            ],
            "volumes": {k: public_volume(v) for k, v in snapshot["volumes"].items()},
        },
        "PLANNED": {
            "destination": str(dest / project),
            "helper_image": helper_image,
            "archives": [f"{store}.tar.gz" for store in ALL_STORES],
            "ordering": [
                "operator establishes exclusive custody and closes new admission",
                "drain accepted work under original deadlines; retain non-chat queue work",
                "stop application writers with proven terminal disposition",
                "stop Postgres, Redis (final RDB save), Neo4j cleanly",
                "create verifies stopped/exclusive attachments before cold capture",
                "validate completed checkpoint; return original posture separately",
            ],
            "actions": [
                "read-only volume helpers archive four stopped stores",
                "hash/archive validation, fsync, atomic immutable publication",
            ],
            "source_sizes": "not probed while live; archive sizes recorded after closure",
        },
        "BLOCKED": blockers,
        "release_posture": "HOLD",
    }


def create(
    docker: Docker,
    project: str,
    destination: str,
    helper_image: str,
    confirm: str,
    schema_revision: str,
    *,
    checkpoint_id: str | None = None,
    source_revision: str | None = None,
    client_revision: str | None = None,
    queue_observations: list[str] | None = None,
    timeout: int = 300,
) -> dict:
    require(
        confirm == f"checkpoint:{project}",
        "explicit custody/closure confirmation is required",
    )
    require(
        re.fullmatch(r"[a-zA-Z0-9_,.-]{1,128}", schema_revision),
        "observed PostgreSQL schema revision is required",
    )
    for revision in (source_revision, client_revision):
        require(
            revision is None or re.fullmatch(r"[0-9a-f]{7,64}", revision),
            "invalid source/client pin",
        )
    queues = {}
    for observation in queue_observations or []:
        require(
            re.fullmatch(r"[a-zA-Z0-9_:.-]{1,128}=[0-9]{1,12}", observation),
            "queue observations must be explicit queue=count pairs",
        )
        queue, count = observation.split("=")
        require(queue not in queues, "duplicate queue observation")
        queues[queue] = int(count)
    snapshot = inspect_project(docker, project, closed=True)
    dest = safe_destination(destination, snapshot)
    docker.image(helper_image)
    now = datetime.now(timezone.utc)
    cid = (
        checkpoint_id
        or f"cp-{now:%Y%m%dT%H%M%S%fZ}-{hashlib.sha256(project.encode()).hexdigest()[:8]}-{uuid.uuid4().hex[:8]}"
    )
    require(ID_RE.fullmatch(cid), "invalid checkpoint ID; latest is never inferred")
    parent = dest / project
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    no_symlinks(parent)
    require(
        parent.stat().st_uid == os.getuid() and parent.stat().st_mode & 0o077 == 0,
        "checkpoint parent must be operator-owned and private",
    )
    with (parent / ".checkpoint.lock").open("a+b") as lock:
        os.chmod(parent / ".checkpoint.lock", 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        final = parent / cid
        staging = parent / (".incomplete-" + cid)
        require(
            not final.exists() and not staging.exists(),
            "checkpoint identity already exists",
        )
        staging.mkdir(mode=0o700)
        manifest = {
            "schema": SCHEMA,
            "checkpoint_id": cid,
            "created_at_utc": now.isoformat(),
            "project": project,
            "helper_image": helper_image,
            "repository_revision": subprocess.check_output(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
            ).strip(),
            "source_revision": source_revision,
            "prepared_client_revision": client_revision,
            "postgres_schema_revision": {
                "value": schema_revision,
                "evidence": "explicit operator read-only pre-closure observation",
            },
            "create_result": "PASS",
            "validation_result": "PASS",
            "files": {},
            "stores": {},
            "services": [
                {
                    "name": labels(c)["com.docker.compose.service"],
                    "container_id": c["Id"],
                    "image_id": c["Image"],
                    "mounts": c["Mounts"],
                }
                for c in snapshot["containers"]
            ],
            "queue_observations": {
                "counts": queues,
                "evidence": "operator pre-closure observations"
                if queues
                else "not supplied",
                "closure_authority": "none; persisted Redis captured cold",
            },
            "closure": identity(snapshot),
        }
        # Contains sensitive runtime Env/config; protected artifact, never manifest/output.
        write_json(
            staging / "runtime-config.json", {"containers": snapshot["containers"]}
        )
        for store, volume in snapshot["volumes"].items():
            require(
                identity(inspect_project(docker, project, closed=True))
                == identity(snapshot),
                "source custody changed during capture",
            )
            archive = staging / f"{store}.tar.gz"
            with archive.open("xb") as stream:
                os.chmod(archive, 0o600)
                docker.run(
                    *helper_args(helper_image, volume["Name"], "capture"),
                    timeout=timeout,
                    output=stream,
                )
                stream.flush()
                os.fsync(stream.fileno())
            manifest["stores"][store] = {
                "volume": public_volume(volume),
                "archive": archive.name,
                "inventory": archive_inventory(archive),
            }
        require(
            identity(inspect_project(docker, project, closed=True))
            == identity(snapshot),
            "source custody changed after capture",
        )
        for artifact in staging.iterdir():
            manifest["files"][artifact.name] = {
                "bytes": artifact.stat().st_size,
                "sha256": digest(artifact),
            }
        verify_payload(staging, manifest)
        write_json(staging / "manifest.json", manifest)
        write_json(
            staging / "COMPLETE",
            {"schema": SCHEMA, "manifest_sha256": digest(staging / "manifest.json")},
        )
        for artifact in staging.iterdir():
            os.chmod(artifact, 0o400)
        fsync_dir(staging)
        os.chmod(staging, 0o500)
        require(not final.exists(), "checkpoint identity collision")
        staging.rename(final)
        fsync_dir(parent)
    validate_checkpoint(final, project)
    return {
        "status": "PASS",
        "checkpoint": str(final),
        "checkpoint_id": cid,
        "manifest_sha256": digest(final / "manifest.json"),
    }


def target_volumes(
    docker: Docker, manifest: dict, project: str, targets: dict, isolated: bool
) -> dict:
    project_name(project)
    require(
        set(targets) == set(ALL_STORES) and len(set(targets.values())) == 4,
        "explicit unambiguous four-store target mapping required",
    )
    source = manifest["project"]
    require(
        (project == source and not isolated) or (project != source and isolated),
        "restore project mismatch; cross-project restore requires isolated mode",
    )
    result = {}
    source_names = {s["volume"]["Name"] for s in manifest["stores"].values()}
    containers = docker.containers()
    service_images = {
        entry["name"]: entry["image_id"] for entry in manifest.get("services", [])
    }
    for c in containers:
        if owner(c) == project:
            require(
                not c["State"]["Running"] and not c["State"].get("Paused"),
                "all target project services must be stopped",
            )
            service = labels(c).get("com.docker.compose.service")
            require(
                not service_images
                or (
                    service in service_images and c["Image"] == service_images[service]
                ),
                "target runtime service/image differs from checkpoint",
            )
    for store, name in targets.items():
        require(
            isinstance(name, str)
            and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,200}", name),
            "invalid target volume name",
        )
        v = docker.volume(name)
        if isolated:
            require(
                name not in source_names
                and (v.get("Labels") or {}).get("com.docker.compose.project")
                == project,
                "isolated target volume is not explicitly owned by target project",
            )
        else:
            require(
                public_volume(v) == manifest["stores"][store]["volume"],
                "original target volume identity mismatch",
            )
        for c in containers:
            if any(m.get("Name") == name for m in c["Mounts"]):
                require(
                    owner(c) == project
                    and not c["State"]["Running"]
                    and not c["State"].get("Paused"),
                    "target writer/unrelated attachment is active",
                )
        result[store] = v
    return result


def restore(
    docker: Docker,
    source_project: str,
    project: str,
    checkpoint: str,
    targets: dict,
    confirm: str,
    *,
    isolated: bool = False,
    timeout: int = 300,
) -> dict:
    manifest = validate_checkpoint(checkpoint, source_project)
    require(
        confirm == f"restore:{source_project}:{manifest['checkpoint_id']}:{project}",
        "explicit source/checkpoint/target confirmation required",
    )
    root = Path(checkpoint)
    before = {p.name: digest(p) for p in root.iterdir()}
    docker.image(manifest["helper_image"])
    volumes = target_volumes(docker, manifest, project, targets, isolated)
    for store in ALL_STORES:
        require(
            target_volumes(docker, manifest, project, targets, isolated) == volumes,
            "restore target custody changed",
        )
        raw = docker.run(
            *helper_args(
                manifest["helper_image"],
                targets[store],
                "restore",
                root / f"{store}.tar.gz",
            ),
            timeout=timeout,
        )
        rows = sorted(json.loads(raw), key=lambda row: row["name"])
        require(
            rows == manifest["stores"][store]["inventory"],
            "restored volume readback mismatch",
        )
    require(
        target_volumes(docker, manifest, project, targets, isolated) == volumes,
        "restore target custody changed after restoration",
    )
    require(
        before == {p.name: digest(p) for p in root.iterdir()},
        "checkpoint changed during restore",
    )
    validate_checkpoint(root, source_project)
    return {
        "status": "PASS",
        "target_project": project,
        "checkpoint_id": manifest["checkpoint_id"],
        "checkpoint_unchanged": True,
        "restored_stores": list(ALL_STORES),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("plan", "create", "validate", "restore"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        if name in ("plan", "create"):
            p.add_argument("--destination", required=True)
            p.add_argument("--helper-image", required=True)
        if name == "create":
            p.add_argument("--confirm", required=True)
            p.add_argument("--schema-revision", required=True)
            p.add_argument("--checkpoint-id")
            p.add_argument("--source-revision")
            p.add_argument("--client-revision")
            p.add_argument("--queue-observation", action="append", default=[])
        if name in ("validate", "restore"):
            p.add_argument("--checkpoint", required=True)
        if name == "restore":
            p.add_argument("--source-project", required=True)
            p.add_argument("--targets", type=Path, required=True)
            p.add_argument("--confirm", required=True)
            p.add_argument("--isolated", action="store_true")
    args = parser.parse_args(argv)
    try:
        project_name(args.project)
        docker = Docker()
        if args.operation == "plan":
            result = plan(docker, args.project, args.destination, args.helper_image)
        elif args.operation == "create":
            result = create(
                docker,
                args.project,
                args.destination,
                args.helper_image,
                args.confirm,
                args.schema_revision,
                checkpoint_id=args.checkpoint_id,
                source_revision=args.source_revision,
                client_revision=args.client_revision,
                queue_observations=args.queue_observation,
            )
        elif args.operation == "validate":
            m = validate_checkpoint(args.checkpoint, args.project)
            result = {
                "status": "PASS",
                "checkpoint_id": m["checkpoint_id"],
                "project": m["project"],
            }
        else:
            result = restore(
                docker,
                args.source_project,
                args.project,
                args.checkpoint,
                json.loads(args.targets.read_text()),
                args.confirm,
                isolated=args.isolated,
            )
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (
        CheckpointError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        tarfile.TarError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": str(exc)
                    if isinstance(exc, CheckpointError)
                    else "invalid input or operation failure; inspect privately",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
