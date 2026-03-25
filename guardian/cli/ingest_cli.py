import json
from pathlib import Path
from typing import Dict, List

import typer

from guardian.obsidian.indexer import (
    _build_obsidian_items,
    _obsidian_source_id,
    _parse_frontmatter,
    _yield_md_files,
    index_obsidian_vault,
)
from guardian.vector.store import VectorStore

app = typer.Typer(name="ingest")


@app.command("ingest-obsidian")
def ingest_obsidian(
    dir: str,
    prune: bool = typer.Option(
        False,
        "--prune",
        help="Remove Obsidian entries under this vault root that are no longer present.",
    ),
):
    if not isinstance(prune, bool):
        prune = False
    summary = index_obsidian_vault(dir)
    root = summary.get("vault_root") or str(Path(dir).resolve())
    ingested = summary.get("indexed", 0)
    deleted = summary.get("deleted", 0)
    typer.echo(
        json.dumps(
            {
                "ingested": ingested,
                "dir": str(root),
                "prune": prune,
                "pruned": deleted,
                "namespace": summary.get("namespace"),
                "scanned": summary.get("scanned"),
                "failures": summary.get("failures"),
            },
            ensure_ascii=False,
        )
    )


@app.command("ingest-conversations")
def ingest_conversations(dir: str):
    root = Path(dir)
    store = VectorStore()
    items: List[Dict] = []
    for p in root.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        # Expect list of messages with {message, role, ts, thread}
        if isinstance(data, list):
            for m in data:
                text = str(m.get("message") or "")
                meta = {k: m.get(k) for k in ("role", "ts", "thread")}
                meta["path"] = str(p)
                items.append({"text": text, "meta": meta})
    n = store.add_texts(items)
    typer.echo(
        json.dumps({"ingested": n, "dir": str(root)}, ensure_ascii=False)
    )


if __name__ == "__main__":
    app()
