"""Artifact catalog — correlation pass over scraper + recon outputs.

Reads existing scraper artifacts and conversation index to produce
enriched artifact indexes and a keystone conversation ranking.

No new extraction. No DB. No models. Pure correlation.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- Patterns ---

_CODE_KEYWORDS = re.compile(
    r"\b(Codexify|Guardian)\b", re.IGNORECASE
)
_COMMIT_PATTERN = re.compile(
    r"(?im)^(?:#{1,6}\s*)?Commit[\s:]|git\s+commit|committed\s+in\s+[0-9a-f]{7}",
)


# --- Data ---


@dataclass
class ArtifactRecord:
    artifact_id: str
    artifact_type: str
    conversation_id: str
    title: str
    message_count: int = 0
    contains_code: bool = False
    contains_commit: bool = False
    created_at: str = ""
    source_path: str = ""
    codexify_mentions: int = 0
    guardian_mentions: int = 0
    confidence: float = 1.0

    def to_row(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "conversation_id": self.conversation_id,
            "title": self.title,
            "message_count": self.message_count,
            "contains_code": str(self.contains_code).lower(),
            "contains_commit": str(self.contains_commit).lower(),
            "created_at": self.created_at,
            "source_path": self.source_path,
            "codexify_mentions": self.codexify_mentions,
            "guardian_mentions": self.guardian_mentions,
            "confidence": self.confidence,
        }


@dataclass
class KeystoneConversation:
    conversation_id: str
    title: str
    message_count: int
    task_prompt_count: int = 0
    summary_count: int = 0
    partial_count: int = 0
    contains_code: bool = False
    contains_commit: bool = False
    codexify_mentions: int = 0
    guardian_mentions: int = 0
    keyword_density: float = 0.0
    keystone_score: float = 0.0

    def to_row(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "message_count": self.message_count,
            "task_prompt_count": self.task_prompt_count,
            "summary_count": self.summary_count,
            "partial_count": self.partial_count,
            "contains_code": str(self.contains_code).lower(),
            "contains_commit": str(self.contains_commit).lower(),
            "codexify_mentions": self.codexify_mentions,
            "guardian_mentions": self.guardian_mentions,
            "keyword_density": round(self.keyword_density, 6),
            "keystone_score": round(self.keystone_score, 2),
        }


# --- Catalog builder ---


class ArtifactCatalog:
    """Correlate scraper artifacts with conversation index."""

    def __init__(self) -> None:
        self.artifacts: list[ArtifactRecord] = []
        self.keystones: list[KeystoneConversation] = []

    def build(
        self,
        scraper_dir: str | Path,
        conversation_index_path: str | Path,
    ) -> None:
        scraper = Path(scraper_dir).expanduser().resolve()
        index_path = Path(conversation_index_path).expanduser().resolve()

        # Load conversation index
        conv_index = self._load_conversation_index(index_path)

        # Scan scraper artifacts
        artifact_dirs = {
            "codexify_task_prompt": scraper / "codexify_task_prompts",
            "task_summary": scraper / "task_summaries",
            "execution_contract": scraper / "execution_contracts",
            "unknown_or_partial": scraper / "unknown_or_partial_matches",
        }

        # Collect per-conversation stats for keystone scoring
        conv_stats: dict[
            str, dict[str, Any]
        ] = defaultdict(
            lambda: {
                "task_prompt_count": 0,
                "summary_count": 0,
                "partial_count": 0,
                "codexify_mentions": 0,
                "guardian_mentions": 0,
                "contains_commit": False,
                "artifacts": [],
            }
        )

        for artifact_type, artifact_dir in artifact_dirs.items():
            if not artifact_dir.exists():
                continue
            for json_file in sorted(artifact_dir.glob("*.json")):
                record = self._process_artifact(
                    json_file, artifact_type, artifact_dir, conv_index
                )
                if record:
                    self.artifacts.append(record)
                    cid = record.conversation_id
                    cs = conv_stats[cid]
                    if artifact_type == "codexify_task_prompt":
                        cs["task_prompt_count"] += 1
                    elif artifact_type == "task_summary":
                        cs["summary_count"] += 1
                    elif artifact_type == "unknown_or_partial":
                        cs["partial_count"] += 1
                    cs["codexify_mentions"] += record.codexify_mentions
                    cs["guardian_mentions"] += record.guardian_mentions
                    if record.contains_commit:
                        cs["contains_commit"] = True
                    cs["artifacts"].append(record)

        # Build keystone scores
        self.keystones = self._build_keystones(conv_stats, conv_index)

    def _load_conversation_index(
        self, path: Path
    ) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        if not path.exists():
            return index
        with path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                cid = row.get("conversation_id", "").strip()
                if cid:
                    index[cid] = row
        return index

    def _process_artifact(
        self,
        json_path: Path,
        artifact_type: str,
        artifact_dir: Path,
        conv_index: dict[str, dict[str, Any]],
    ) -> ArtifactRecord | None:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        metadata = data.get("metadata", {})
        conv_id = (metadata.get("source_conversation_id") or "").strip()
        if not conv_id:
            return None

        artifact_id = metadata.get("artifact_id", json_path.stem)
        created_at = metadata.get("source_created_at", "")
        source_path = metadata.get("source_file_path", "")
        confidence = float(metadata.get("confidence", 1.0))

        # Look up conversation metadata
        conv_row = conv_index.get(conv_id, {})
        title = conv_row.get("title", "").strip()
        try:
            message_count = int(conv_row.get("message_count", 0))
        except (ValueError, TypeError):
            message_count = 0
        contains_code = conv_row.get("contains_code", "false").lower() == "true"

        # Read raw text for keyword + commit detection
        md_path = artifact_dir / f"{artifact_id}.md"
        raw_text = ""
        if md_path.exists():
            raw_text = md_path.read_text(encoding="utf-8", errors="replace")

        codexify_mentions = len(
            re.findall(r"\bCodexify\b", raw_text, re.IGNORECASE)
        )
        guardian_mentions = len(
            re.findall(r"\bGuardian\b", raw_text, re.IGNORECASE)
        )
        contains_commit = bool(_COMMIT_PATTERN.search(raw_text))

        return ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            conversation_id=conv_id,
            title=title,
            message_count=message_count,
            contains_code=contains_code,
            contains_commit=contains_commit,
            created_at=created_at,
            source_path=source_path,
            codexify_mentions=codexify_mentions,
            guardian_mentions=guardian_mentions,
            confidence=confidence,
        )

    def _build_keystones(
        self,
        conv_stats: dict[str, dict[str, Any]],
        conv_index: dict[str, dict[str, Any]],
    ) -> list[KeystoneConversation]:
        keystones: list[KeystoneConversation] = []

        # Compute raw density for normalization
        densities: list[float] = []
        for cid, cs in conv_stats.items():
            conv_row = conv_index.get(cid, {})
            try:
                msg_count = int(conv_row.get("message_count", 1))
            except (ValueError, TypeError):
                msg_count = 1
            density = (cs["codexify_mentions"] + cs["guardian_mentions"]) / msg_count
            densities.append(density)

        max_density = max(densities) if densities else 1.0

        for cid, cs in conv_stats.items():
            conv_row = conv_index.get(cid, {})
            title = conv_row.get("title", "").strip()
            try:
                msg_count = int(conv_row.get("message_count", 1))
            except (ValueError, TypeError):
                msg_count = 1
            contains_code = (
                conv_row.get("contains_code", "false").lower() == "true"
            )

            raw_density = (
                cs["codexify_mentions"] + cs["guardian_mentions"]
            ) / msg_count
            norm_density = raw_density / max_density if max_density > 0 else 0.0

            score = (
                cs["task_prompt_count"]
                + cs["summary_count"]
                + (1 if contains_code else 0)
                + (1 if cs["contains_commit"] else 0)
                + norm_density
            )

            keystones.append(
                KeystoneConversation(
                    conversation_id=cid,
                    title=title,
                    message_count=msg_count,
                    task_prompt_count=cs["task_prompt_count"],
                    summary_count=cs["summary_count"],
                    partial_count=cs["partial_count"],
                    contains_code=contains_code,
                    contains_commit=cs["contains_commit"],
                    codexify_mentions=cs["codexify_mentions"],
                    guardian_mentions=cs["guardian_mentions"],
                    keyword_density=raw_density,
                    keystone_score=score,
                )
            )

        keystones.sort(key=lambda k: k.keystone_score, reverse=True)
        return keystones


# --- Output writers ---

_ARTIFACT_CATALOG_FIELDS = [
    "artifact_id",
    "artifact_type",
    "conversation_id",
    "title",
    "message_count",
    "contains_code",
    "contains_commit",
    "created_at",
    "source_path",
    "codexify_mentions",
    "guardian_mentions",
    "confidence",
]

_KEYSTONE_FIELDS = [
    "conversation_id",
    "title",
    "message_count",
    "task_prompt_count",
    "summary_count",
    "partial_count",
    "contains_code",
    "contains_commit",
    "codexify_mentions",
    "guardian_mentions",
    "keyword_density",
    "keystone_score",
]


def write_artifact_catalog(
    artifacts: list[ArtifactRecord], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ARTIFACT_CATALOG_FIELDS)
        writer.writeheader()
        for a in sorted(artifacts, key=lambda a: (a.artifact_type, a.artifact_id)):
            writer.writerow(a.to_row())


def write_task_prompt_index(
    artifacts: list[ArtifactRecord], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    task_prompts = [
        a for a in artifacts if a.artifact_type == "codexify_task_prompt"
    ]
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ARTIFACT_CATALOG_FIELDS)
        writer.writeheader()
        for a in sorted(
            task_prompts, key=lambda a: a.message_count, reverse=True
        ):
            writer.writerow(a.to_row())


def write_task_summary_index(
    artifacts: list[ArtifactRecord], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summaries = [
        a for a in artifacts if a.artifact_type == "task_summary"
    ]
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ARTIFACT_CATALOG_FIELDS)
        writer.writeheader()
        for a in sorted(
            summaries, key=lambda a: a.message_count, reverse=True
        ):
            writer.writerow(a.to_row())


def write_keystone_conversations(
    keystones: list[KeystoneConversation], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_KEYSTONE_FIELDS)
        writer.writeheader()
        for k in keystones:
            writer.writerow(k.to_row())


def build_artifact_catalog(
    scraper_dir: str | Path = "export_scraper",
    conversation_index_path: str | Path = "export_archaeology/conversation_index.csv",
    output_dir: str | Path = "export_archaeology",
) -> dict[str, int]:
    catalog = ArtifactCatalog()
    catalog.build(scraper_dir, conversation_index_path)
    out = Path(output_dir)

    write_artifact_catalog(catalog.artifacts, out / "artifact_catalog.csv")
    write_task_prompt_index(catalog.artifacts, out / "task_prompt_index.csv")
    write_task_summary_index(catalog.artifacts, out / "task_summary_index.csv")
    write_keystone_conversations(
        catalog.keystones, out / "keystone_conversations.csv"
    )

    return {
        "total_artifacts": len(catalog.artifacts),
        "task_prompts": sum(
            1
            for a in catalog.artifacts
            if a.artifact_type == "codexify_task_prompt"
        ),
        "task_summaries": sum(
            1
            for a in catalog.artifacts
            if a.artifact_type == "task_summary"
        ),
        "partial_matches": sum(
            1
            for a in catalog.artifacts
            if a.artifact_type == "unknown_or_partial"
        ),
        "unique_conversations": len(catalog.keystones),
        "keystone_conversations": len(catalog.keystones),
    }
