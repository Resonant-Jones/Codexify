from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


def repo_root() -> Path:
    return Path.cwd()


def common_datas(root: Path | None = None) -> list[tuple[str, str]]:
    repo = root or repo_root()
    datas: list[tuple[str, str]] = [
        (str(repo / "config" / "public_routes.yaml"), "config"),
        (str(repo / "docs" / "builtin-help" / "codexify-guide.md"), "docs/builtin-help"),
        (str(repo / "guardian" / "contracts.py"), "bootstrap/guardian"),
        (
            str(repo / "guardian" / "contracts" / "imprint_snapshot.py"),
            "bootstrap/guardian/contracts",
        ),
        (
            str(repo / "guardian" / "contracts" / "imprint_proposal.py"),
            "bootstrap/guardian/contracts",
        ),
    ]
    datas.extend(
        (
            str(path),
            "config/supported_profiles",
        )
        for path in sorted((repo / "config" / "supported_profiles").glob("*.yaml"))
    )
    return datas


def backend_hiddenimports() -> list[str]:
    return [
        "backend.rag.chatgpt_migration",
        "chromadb.api.rust",
        "chromadb.telemetry.product",
        "chromadb.telemetry.product.posthog",
        "guardian.contracts",
        "guardian.contracts.imprint_proposal",
        "guardian.contracts.imprint_snapshot",
        *collect_submodules("guardian.contracts"),
    ]


def runtime_hiddenimports() -> list[str]:
    return [
        *backend_hiddenimports(),
        "alembic",
        "alembic.command",
        "alembic.config",
        "backend.compiled_backend_entry",
        "backend.scripts.seed_defaults",
        "guardian.scripts.ensure_embed_model",
        "guardian.workers.chat_worker",
        "guardian.workers.document_embed_worker",
        "guardian.workers.chat_embedding_worker",
        "guardian.workers.warmup_worker",
    ]
