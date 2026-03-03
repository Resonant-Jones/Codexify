import json
import logging
from pathlib import Path
from typing import Dict, List

import typer

from guardian.vector.store import VectorStore

app = typer.Typer(name="ingest")
logger = logging.getLogger(__name__)
_LOGGED_FRONTMATTER_FAILURES: set[str] = set()


def _yield_md_files(root: Path):
    for p in root.rglob("*.md"):
        if p.is_file():
            yield p


def _warn_frontmatter_parse_failed(path: str) -> None:
    if path in _LOGGED_FRONTMATTER_FAILURES:
        return
    _LOGGED_FRONTMATTER_FAILURES.add(path)
    logger.warning("frontmatter_parse_failed:%s", path)


def _parse_frontmatter(text: str, *, path: str) -> Dict:
    # Parse frontmatter only when file starts with a leading fence.
    if text.startswith("---"):
        first_newline = text.find("\n")
        if first_newline != -1 and text[:first_newline].strip() == "---":
            end = text.find("\n---\n", first_newline + 1)
            if end != -1:
                try:
                    import yaml  # type: ignore

                    fm = yaml.safe_load(text[first_newline + 1 : end]) or {}
                    if not isinstance(fm, dict):
                        raise ValueError(
                            "frontmatter must parse to a mapping"
                        )
                    content = text[end + 5 :]
                    return {"frontmatter": fm, "content": content}
                except Exception:
                    _warn_frontmatter_parse_failed(path)
                    return {"frontmatter": {}, "content": text}
    return {"frontmatter": {}, "content": text}


@app.command("ingest-obsidian")
def ingest_obsidian(dir: str):
    root = Path(dir)
    store = VectorStore()
    items: List[Dict] = []
    for md in _yield_md_files(root):
        t = md.read_text(encoding="utf-8", errors="ignore")
        parsed = _parse_frontmatter(t, path=str(md))
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
