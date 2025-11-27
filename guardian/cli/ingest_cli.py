import json
from pathlib import Path
from typing import Dict, List

import typer

from guardian.vector.store import VectorStore

app = typer.Typer(name="ingest")


def _yield_md_files(root: Path):
    for p in root.rglob("*.md"):
        if p.is_file():
            yield p


def _parse_frontmatter(text: str) -> Dict:
    # Minimal frontmatter parser: expects leading --- lines
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            import yaml  # type: ignore

            fm = yaml.safe_load(text[4:end]) or {}
            content = text[end + 5 :]
            return {"frontmatter": fm, "content": content}
    return {"frontmatter": {}, "content": text}


@app.command("ingest-obsidian")
def ingest_obsidian(dir: str):
    root = Path(dir)
    store = VectorStore()
    items: List[Dict] = []
    for md in _yield_md_files(root):
        t = md.read_text(encoding="utf-8", errors="ignore")
        parsed = _parse_frontmatter(t)
        fm = parsed["frontmatter"]
        title = fm.get("title") or md.stem
        tags = fm.get("tags") or []
        items.append(
            {
                "text": parsed["content"],
                "meta": {"path": str(md), "tags": tags, "title": title},
            }
        )
    n = store.add_texts(items)
    typer.echo(
        json.dumps({"ingested": n, "dir": str(root)}, ensure_ascii=False)
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
