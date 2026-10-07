from __future__ import annotations

import copy
import importlib.util
import json
import os
import tarfile
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "candidate_checkpoint", ROOT / "scripts/ops/candidate_runtime_checkpoint.py"
)
assert SPEC and SPEC.loader
cp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cp)
IMAGE = "sha256:" + "a" * 64


def sample(project="fixture"):
    volumes = {}
    containers = []
    for index, (store, service, target) in enumerate(
        [
            ("postgres", "db", "/var/lib/postgresql/data"),
            ("redis", "redis", "/data"),
            ("neo4j", "neo4j", "/data"),
            ("chroma", "backend", "/app/.chroma"),
        ]
    ):
        name = project + "_" + store
        ls = {"com.docker.compose.project": project}
        if store == "chroma":
            ls |= {
                "codexify.storage.contract": "ADR-101",
                "codexify.storage.project": project,
                "codexify.storage.admission_id": "nonce",
            }
        volumes[name] = {
            "Name": name,
            "Driver": "local",
            "Scope": "local",
            "Options": None,
            "CreatedAt": "2026-10-07T00:00:00Z",
            "Mountpoint": "/var/lib/docker/volumes/" + name,
            "Labels": ls,
        }
        containers.append(
            {
                "Id": str(index),
                "Image": IMAGE,
                "RestartCount": 0,
                "Config": {
                    "Labels": {
                        "com.docker.compose.project": project,
                        "com.docker.compose.service": service,
                    }
                },
                "State": {
                    "Running": False,
                    "Paused": False,
                    "Status": "exited",
                    "ExitCode": 0,
                    "OOMKilled": False,
                    "StartedAt": "start",
                    "FinishedAt": "finish",
                },
                "Mounts": [
                    {
                        "Type": "volume",
                        "Name": name,
                        "Destination": target,
                        "Source": volumes[name]["Mountpoint"],
                        "RW": True,
                    }
                ],
            }
        )
    return containers, volumes


class FakeDocker:
    def __init__(self):
        self.cs, self.vs = sample()
        self.commands = []

    def containers(self):
        return copy.deepcopy(self.cs)

    def volume(self, name):
        if name not in self.vs:
            raise cp.CheckpointError("missing volume")
        return copy.deepcopy(self.vs[name])

    def image(self, image):
        cp.require(cp.IMAGE_RE.fullmatch(image), "pinned image required")
        return {"Id": image}

    def run(self, *args, **kwargs):
        self.commands.append(args)
        if args[0] == "logs":
            return (
                "User requested shutdown\nDB saved on disk\nRedis is now ready to exit"
            )
        raise cp.CheckpointError("injected capture failure")


def manifest_checkpoint(base: Path):
    root = base / "fixture" / "cp-unit"
    root.mkdir(parents=True)
    manifest = {
        "schema": 1,
        "checkpoint_id": "cp-unit",
        "project": "fixture",
        "helper_image": IMAGE,
        "create_result": "PASS",
        "validation_result": "PASS",
        "stores": {},
        "files": {},
    }
    _, volumes = sample()
    for store in cp.ALL_STORES:
        source = base / ("payload-" + store)
        source.mkdir()
        (source / "data").write_text("original " + store)
        if store == "chroma":
            v = volumes["fixture_chroma"]
            marker = {
                "contract": "ADR-101",
                "project": "fixture",
                "volume": v["Name"],
                "created_at": v["CreatedAt"],
                "admission_id": "nonce",
            }
            (source / ".codexify-storage-admission.json").write_text(json.dumps(marker))
        archive = root / (store + ".tar.gz")
        with tarfile.open(archive, "w:gz") as tar:
            for p in [source, *sorted(source.iterdir())]:
                tar.add(p, arcname="." if p == source else p.name, recursive=False)
        manifest["stores"][store] = {
            "volume": cp.public_volume(volumes["fixture_" + store]),
            "archive": archive.name,
            "inventory": cp.archive_inventory(archive),
        }
    (root / "runtime-config.json").write_text("{}")
    for p in root.iterdir():
        manifest["files"][p.name] = {"bytes": p.stat().st_size, "sha256": cp.digest(p)}
    publish_manifest(root, manifest)
    return root, manifest


def publish_manifest(root, manifest):
    (root / "manifest.json").write_text(json.dumps(manifest))
    (root / "COMPLETE").write_text(
        json.dumps({"schema": 1, "manifest_sha256": cp.digest(root / "manifest.json")})
    )


def test_cli_requires_destination_and_never_infers_latest():
    with pytest.raises(SystemExit):
        cp.main(["plan", "--project", "fixture", "--helper-image", IMAGE])
    with pytest.raises(SystemExit):
        cp.main(["restore", "--project", "fixture", "--source-project", "fixture"])


@pytest.mark.parametrize(
    "path",
    [
        "/private/tmp/checkpoints",
        "/tmp/checkpoints",
        "/var/lib/docker/volumes/source/child",
        str(ROOT / "checkpoints"),
    ],
)
def test_unsafe_destination(path):
    with pytest.raises(cp.CheckpointError):
        cp.safe_destination(path)


def test_destination_inside_source_and_symlink(tmp_path):
    docker = FakeDocker()
    docker.cs[0]["Mounts"].append(
        {
            "RW": True,
            "Source": str(tmp_path / "source"),
            "Destination": "/runtime-source",
            "Type": "bind",
        }
    )
    snap = cp.inspect_project(docker, "fixture")
    with pytest.raises(cp.CheckpointError):
        cp.safe_destination(tmp_path / "source" / "checkpoint", snap)
    (tmp_path / "link").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(cp.CheckpointError):
        cp.safe_destination(tmp_path / "link" / "cp", snap)


def test_wrong_project_missing_volume_and_unrelated_attachment():
    docker = FakeDocker()
    with pytest.raises(cp.CheckpointError):
        cp.inspect_project(docker, "unrelated")
    del docker.vs["fixture_postgres"]
    with pytest.raises(cp.CheckpointError):
        cp.inspect_project(docker, "fixture")
    docker = FakeDocker()
    unrelated = copy.deepcopy(docker.cs[0])
    unrelated["Config"]["Labels"]["com.docker.compose.project"] = "unrelated"
    docker.cs.append(unrelated)
    with pytest.raises(cp.CheckpointError):
        cp.inspect_project(docker, "fixture", closed=True)
    assert not docker.commands


@pytest.mark.parametrize("change", ["running", "oom", "exit", "redis-no-final-save"])
def test_cold_create_requires_actual_writer_closure(change):
    docker = FakeDocker()
    if change == "running":
        docker.cs[0]["State"]["Running"] = True
    elif change == "oom":
        docker.cs[0]["State"]["OOMKilled"] = True
    elif change == "exit":
        docker.cs[0]["State"]["ExitCode"] = 137
    else:
        docker.run = lambda *args, **kwargs: "Ready to accept connections"
    with pytest.raises(cp.CheckpointError):
        cp.inspect_project(docker, "fixture", closed=True)


def test_checkpoint_integrity_and_completeness(tmp_path):
    root, manifest = manifest_checkpoint(tmp_path)
    assert cp.validate_checkpoint(root, "fixture")["checkpoint_id"] == "cp-unit"
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(root, "other-project")
    (root / "COMPLETE").unlink()
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(root, "fixture")
    publish_manifest(root, manifest)
    (root / "manifest.json").write_text("{invalid")
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(root, "fixture")
    publish_manifest(root, manifest)
    (root / "postgres.tar.gz").write_bytes(b"corruption")
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(root, "fixture")


def test_missing_required_archive_is_never_restorable(tmp_path):
    root, _ = manifest_checkpoint(tmp_path)
    (root / "neo4j.tar.gz").unlink()
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(root, "fixture")


def test_schema_and_staging_directory_rejected(tmp_path):
    root, manifest = manifest_checkpoint(tmp_path)
    manifest["schema"] = 99
    publish_manifest(root, manifest)
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(root, "fixture")
    staging = root.with_name(".incomplete-cp-unit")
    root.rename(staging)
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(staging, "fixture")


def test_restore_guards_before_any_mutation(tmp_path):
    root, manifest = manifest_checkpoint(tmp_path)
    docker = FakeDocker()
    targets = {k: "fixture_" + k for k in cp.ALL_STORES}
    with pytest.raises(cp.CheckpointError):
        cp.restore(docker, "fixture", "fixture", str(root), targets, "wrong")
    with pytest.raises(cp.CheckpointError):
        cp.restore(docker, "other", "fixture", str(root), targets, "wrong")
    with pytest.raises(cp.CheckpointError):
        cp.target_volumes(docker, manifest, "other", targets, False)
    docker.cs[0]["State"]["Running"] = True
    with pytest.raises(cp.CheckpointError):
        cp.target_volumes(docker, manifest, "fixture", targets, False)
    assert not docker.commands


def test_partial_capture_retained_and_id_cannot_be_reused(tmp_path):
    docker = FakeDocker()
    dest = tmp_path / "checkpoint-root"
    with pytest.raises(cp.CheckpointError, match="injected"):
        cp.create(
            docker,
            "fixture",
            str(dest),
            IMAGE,
            "checkpoint:fixture",
            "fixture_schema",
            checkpoint_id="cp-fixed",
        )
    partial = dest / "fixture" / ".incomplete-cp-fixed"
    assert partial.is_dir() and not (partial / "COMPLETE").exists()
    with pytest.raises(cp.CheckpointError):
        cp.validate_checkpoint(partial, "fixture")
    before = list(docker.commands)
    with pytest.raises(cp.CheckpointError, match="already exists"):
        cp.create(
            docker,
            "fixture",
            str(dest),
            IMAGE,
            "checkpoint:fixture",
            "fixture_schema",
            checkpoint_id="cp-fixed",
        )
    assert all(command[0] == "logs" for command in docker.commands[len(before) :])


def test_archive_path_escape_rejected(tmp_path):
    path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        member = tarfile.TarInfo("../escape")
        tar.addfile(member)
    with pytest.raises(cp.CheckpointError):
        cp.archive_inventory(path)


def test_mutable_helper_image_refused_before_docker_access():
    with pytest.raises(cp.CheckpointError):
        cp.Docker().image("codexify-backend-runtime:latest")


def test_completed_checkpoint_identity_never_reused(tmp_path):
    docker = FakeDocker()
    (tmp_path / "fixture" / "cp-fixed").mkdir(parents=True)
    (tmp_path / "fixture").chmod(0o700)
    sentinel = tmp_path / "fixture" / "cp-fixed" / "sentinel"
    sentinel.write_text("unchanged")
    with pytest.raises(cp.CheckpointError, match="already exists"):
        cp.create(
            docker,
            "fixture",
            str(tmp_path),
            IMAGE,
            "checkpoint:fixture",
            "fixture_schema",
            checkpoint_id="cp-fixed",
        )
    assert sentinel.read_text() == "unchanged"
    assert all(command[0] == "logs" for command in docker.commands)


def test_redis_prior_save_cannot_prove_final_shutdown():
    docker = FakeDocker()
    docker.run = (
        lambda *args,
        **kwargs: "DB saved on disk\nUser requested shutdown\nRedis is now ready to exit"
    )
    with pytest.raises(cp.CheckpointError):
        cp.inspect_project(docker, "fixture", closed=True)


def test_queue_observations_reject_unstructured_or_duplicate_input(tmp_path):
    for observations in (["credentials"], ["queue=0", "queue=1"]):
        with pytest.raises(cp.CheckpointError):
            cp.create(
                FakeDocker(),
                "fixture",
                str(tmp_path),
                IMAGE,
                "checkpoint:fixture",
                "fixture_schema",
                queue_observations=observations,
            )


def wait_for(action, *, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return action()
        except cp.CheckpointError:
            time.sleep(2)
    pytest.fail("fixture service failed to become ready in bound")


CHROMA_FIXTURE = r"""
import json, os, pathlib, signal, sys, time
import chromadb
from chromadb.config import Settings
signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
root = pathlib.Path('/app/.chroma')
client = chromadb.PersistentClient(path=str(root), settings=Settings(anonymized_telemetry=False))
if os.environ['FIXTURE_WRITE'] == '1':
    (root/'.codexify-storage-admission.json').write_text(os.environ['FIXTURE_ADMISSION'])
    client.get_or_create_collection('checkpoint_fixture').add(ids=['fixture'], embeddings=[[1.,0.,0.]], documents=['original'])
else:
    assert client.get_collection('checkpoint_fixture').get(ids=['fixture'])['documents'] == ['original']
print('fixture-ready', flush=True)
while True: time.sleep(1)
"""


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("CODEXIFY_CHECKPOINT_PROOF_ROOT"),
    reason="explicit isolated proof destination required",
)
def test_disposable_four_store_round_trip():
    """Actual installed runtime formats; no real-candidate mutation or image pulls."""
    docker = cp.Docker()
    dest = Path(os.environ["CODEXIFY_CHECKPOINT_PROOF_ROOT"])
    cp.safe_destination(dest)
    token = uuid.uuid4().hex[:12]
    source = "cfy-checkpoint-proof-" + token
    target = "cfy-checkpoint-restore-" + token
    helper = "sha256:bcb55917283fc2d6f23b7891b11c06fcebb5ec811e82eb5d62491e09b404ccb6"
    images = {
        store: docker.json("image", "inspect", tag)[0]["Id"]
        for store, tag in [
            ("postgres", "postgres:15"),
            ("redis", "redis:7-alpine"),
            ("neo4j", "neo4j:5"),
        ]
    }
    images["chroma"] = helper
    for image in images.values():
        docker.image(image)
    volumes = {}
    container_names = []
    owned_volumes = []
    report = {"source_project": source, "target_project": target, "images": images}

    def make_volumes(project, admitted=False):
        result = {}
        for store in cp.ALL_STORES:
            name = project + "_" + store
            args = [
                "volume",
                "create",
                "--label",
                f"com.docker.compose.project={project}",
            ]
            if store == "chroma" and admitted:
                args += [
                    "--label",
                    "codexify.storage.contract=ADR-101",
                    "--label",
                    f"codexify.storage.project={project}",
                    "--label",
                    f"codexify.storage.admission_id={token}",
                ]
            docker.run(*args, name)
            owned_volumes.append((name, project))
            result[store] = name
        return result

    def start(project, vs, write=False):
        for store in cp.ALL_STORES:
            service = "backend" if store == "chroma" else cp.STORES[store][0]
            name = project + "-" + service
            mount = "/app/.chroma" if store == "chroma" else cp.STORES[store][1]
            args = [
                "run",
                "-d",
                "--pull=never",
                "--name",
                name,
                "--network=none",
                "--hostname",
                name,
                "--add-host",
                name + ":127.0.0.1",
                "--cpus=1",
                "--memory=1536m" if store == "neo4j" else "--memory=768m",
                "--label",
                f"com.docker.compose.project={project}",
                "--label",
                f"com.docker.compose.service={service}",
                "--mount",
                f"type=volume,source={vs[store]},target={mount},volume-nocopy",
            ]
            if store == "postgres":
                args += [
                    "-e",
                    "POSTGRES_USER=codexify_fixture",
                    "-e",
                    "POSTGRES_DB=fixture",
                    "-e",
                    "POSTGRES_HOST_AUTH_METHOD=trust",
                    images[store],
                ]
            elif store == "redis":
                args += [images[store], "redis-server", "--save", "60", "1"]
            elif store == "neo4j":
                logs = project + "_neo4j_logs"
                docker.run(
                    "volume",
                    "create",
                    "--label",
                    f"com.docker.compose.project={project}",
                    logs,
                )
                owned_volumes.append((logs, project))
                args += [
                    "--mount",
                    f"type=volume,source={logs},target=/logs,volume-nocopy",
                    "-e",
                    "NEO4J_server_default__listen__address=0.0.0.0",
                    "-e",
                    "NEO4J_AUTH=none",
                    "-e",
                    "NEO4J_server_memory_heap_initial__size=256m",
                    "-e",
                    "NEO4J_server_memory_heap_max__size=512m",
                    "-e",
                    "NEO4J_server_memory_pagecache_size=128m",
                    images[store],
                ]
            else:
                metadata = docker.volume(vs[store])
                admission = {
                    "contract": "ADR-101",
                    "project": project,
                    "volume": vs[store],
                    "created_at": metadata["CreatedAt"],
                    "admission_id": token,
                }
                args += [
                    "--user",
                    "0:0",
                    "-e",
                    f"FIXTURE_WRITE={int(write)}",
                    "-e",
                    "FIXTURE_ADMISSION=" + json.dumps(admission),
                    "--entrypoint",
                    "python",
                    images[store],
                    "-c",
                    CHROMA_FIXTURE,
                ]
            docker.run(*args)
            container_names.append((name, project))
        wait_for(
            lambda: docker.run(
                "exec",
                project + "-db",
                "pg_isready",
                "-U",
                "codexify_fixture",
                "-d",
                "fixture",
            )
        )
        wait_for(lambda: docker.run("exec", project + "-redis", "redis-cli", "PING"))
        wait_for(
            lambda: docker.run(
                "exec",
                project + "-neo4j",
                "cypher-shell",
                "--format",
                "plain",
                "RETURN 1;",
            )
        )
        wait_for(
            lambda: cp.require(
                "fixture-ready" in docker.run("logs", project + "-backend"),
                "Chroma not ready",
            )
        )

    def pg(project, sql):
        return docker.run(
            "exec",
            project + "-db",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "codexify_fixture",
            "-d",
            "fixture",
            "-AtX",
            "-c",
            sql,
        )

    def stop(project):
        for name, owner in container_names:
            if owner == project:
                docker.run("stop", "--time", "60", name, timeout=75)

    try:
        volumes = make_volumes(source, True)
        start(source, volumes, True)
        pg(
            source,
            "CREATE TABLE checkpoint_fixture(value text); INSERT INTO checkpoint_fixture VALUES ('original'); CREATE TABLE alembic_version(version_num text); INSERT INTO alembic_version VALUES ('fixture_schema');",
        )
        docker.run(
            "exec",
            source + "-redis",
            "redis-cli",
            "SET",
            "checkpoint_fixture",
            "original",
            "EX",
            "3600",
        )
        expiry = docker.run(
            "exec", source + "-redis", "redis-cli", "PEXPIRETIME", "checkpoint_fixture"
        ).strip()
        docker.run(
            "exec",
            source + "-neo4j",
            "cypher-shell",
            "CREATE (:CheckpointFixture {value:'original'});",
        )
        observed = cp.plan(docker, source, str(dest), helper)
        assert observed["status"] == "BLOCKED"
        stop(source)
        created = cp.create(
            docker,
            source,
            str(dest),
            helper,
            "checkpoint:" + source,
            "fixture_schema",
            queue_observations=["fixture-queue=0"],
        )
        checkpoint = Path(created["checkpoint"])
        manifest = cp.validate_checkpoint(checkpoint, source)
        assert all(p.stat().st_mode & 0o222 == 0 for p in checkpoint.iterdir())
        assert checkpoint.stat().st_mode & 0o222 == 0
        hashes = {p.name: cp.digest(p) for p in checkpoint.iterdir()}
        # Real mutation of disposable source after checkpoint, all four stores.
        for name, project in container_names:
            if project == source:
                docker.run("start", name)
        wait_for(lambda: pg(source, "SELECT 1"))
        wait_for(
            lambda: docker.run("exec", source + "-neo4j", "cypher-shell", "RETURN 1;")
        )
        pg(source, "UPDATE checkpoint_fixture SET value='mutated';")
        docker.run(
            "exec",
            source + "-redis",
            "redis-cli",
            "SET",
            "checkpoint_fixture",
            "mutated",
        )
        docker.run(
            "exec",
            source + "-neo4j",
            "cypher-shell",
            "MATCH (n:CheckpointFixture) SET n.value='mutated';",
        )
        docker.run(
            "exec",
            source + "-backend",
            "python",
            "-c",
            "import chromadb; c=chromadb.PersistentClient(path='/app/.chroma'); c.get_collection('checkpoint_fixture').update(ids=['fixture'],documents=['mutated'],embeddings=[[0.0,1.0,0.0]])",
        )
        stop(source)
        targets = make_volumes(target)
        result = cp.restore(
            docker,
            source,
            target,
            str(checkpoint),
            targets,
            f"restore:{source}:{created['checkpoint_id']}:{target}",
            isolated=True,
        )
        assert result["checkpoint_unchanged"]
        assert hashes == {p.name: cp.digest(p) for p in checkpoint.iterdir()}
        start(target, targets, False)
        assert pg(target, "SELECT value FROM checkpoint_fixture;").strip() == "original"
        assert (
            docker.run(
                "exec",
                target + "-redis",
                "redis-cli",
                "--raw",
                "GET",
                "checkpoint_fixture",
            ).strip()
            == "original"
        )
        assert (
            docker.run(
                "exec",
                target + "-redis",
                "redis-cli",
                "PEXPIRETIME",
                "checkpoint_fixture",
            ).strip()
            == expiry
        )
        graph = docker.run(
            "exec",
            target + "-neo4j",
            "cypher-shell",
            "--format",
            "plain",
            "MATCH (n:CheckpointFixture) RETURN n.value;",
        )
        assert "original" in graph and "mutated" not in graph
        chroma = docker.run(
            "exec",
            target + "-backend",
            "python",
            "-c",
            "import chromadb; c=chromadb.PersistentClient(path='/app/.chroma'); assert c.get_collection('checkpoint_fixture').get(ids=['fixture'])['documents']==['original']; print('PASS')",
        )
        assert "PASS" in chroma
        assert (
            cp.validate_checkpoint(checkpoint, source)["stores"] == manifest["stores"]
        )
        assert hashes == {p.name: cp.digest(p) for p in checkpoint.iterdir()}
        report |= {
            "create": created,
            "restore": result,
            "readback": dict.fromkeys(cp.ALL_STORES, "PASS"),
            "checkpoint_hashes_before_after": hashes,
            "redis_absolute_expiry_ms": expiry,
        }
        (dest / "fixture-proof.json").write_text(json.dumps(report, indent=2) + "\n")
    finally:
        for name, project in reversed(container_names):
            with pytest.MonkeyPatch.context():
                values = docker.json("inspect", name)
                assert len(values) == 1 and cp.owner(values[0]) == project
                docker.run("rm", "-f", "-v", name)
        for name, project in reversed(owned_volumes):
            assert (
                docker.volume(name)["Labels"]["com.docker.compose.project"] == project
            )
            docker.run("volume", "rm", name)
