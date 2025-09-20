import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .embeds import Embedder


class VectorStore:
    def __init__(self, index_dir: Optional[str] = None) -> None:
        self.index_dir = index_dir or os.getenv("GUARDIAN_INDEX_DIR", "guardian_index")
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        self.db_path = str(Path(self.index_dir) / "index.sqlite")
        self.embedder = Embedder()
        self._init()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT,
                    meta TEXT,
                    embedding TEXT
                )
                """
            )
            conn.commit()

    def add_texts(self, items: List[Dict[str, Any]]) -> int:
        texts = [i.get("text", "") for i in items]
        embeds = self.embedder.embed(texts)
        with self._conn() as conn:
            c = conn.cursor()
            for i, e in zip(items, embeds):
                c.execute(
                    "INSERT INTO vector_items (text, meta, embedding) VALUES (?, ?, ?)",
                    (
                        i.get("text", ""),
                        json.dumps(i.get("meta", {}), ensure_ascii=False),
                        json.dumps(e),
                    ),
                )
            conn.commit()
        return len(items)

    def _cosine(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        # vectors already normalized; just guard lengths
        return dot

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        qv = self.embedder.embed([query])[0]
        rows: List[Dict[str, Any]] = []
        with self._conn() as conn:
            c = conn.cursor()
            for text, meta, emb_s in c.execute(
                "SELECT text, meta, embedding FROM vector_items"
            ):
                emb = json.loads(emb_s)
                score = float(self._cosine(qv, emb))
                rows.append(
                    {"text": text, "meta": json.loads(meta or "{}"), "score": score}
                )
        rows.sort(key=lambda r: r["score"], reverse=True)
        return rows[: max(1, k)]

    def health(self) -> Dict[str, Any]:
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1")
            return {"status": "ok", "backend": self.embedder.backend}
        except Exception as e:
            return {"status": "error", "error": str(e)}
