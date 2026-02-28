import logging

logger = logging.getLogger(__name__)

import json
from collections import deque
from typing import Any

try:
    import faiss  # type: ignore
except ImportError:
    faiss = None  # type: ignore
import numpy as np
from memoryos.utils import (
    ensure_directory_exists,
    get_timestamp,
    normalize_vector,
)

from .embedders.base import (
    MemoryOSEmbedder,
    get_embedder_model_name,
    get_embedder_provider_name,
)


def _normalize_embed_vector(raw: Any) -> np.ndarray:
    vec = np.asarray(raw, dtype=np.float32)
    if vec.ndim == 0:
        return np.array([], dtype=np.float32)
    if vec.ndim > 1:
        vec = vec.reshape(-1)
    return vec


class _LegacyEmbeddingAdapter:
    """Temporary adapter for deprecated memoryos.utils.get_embedding fallback."""

    name = "legacy_get_embedding"
    model_name = None

    def embed(self, text: str) -> list[float]:
        from memoryos.utils import get_embedding

        vec = get_embedding(text)
        return _normalize_embed_vector(vec).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


def _emit_dimension_skip_events(
    *,
    module: str,
    query_dim: int,
    mismatch_counts: dict[int, int],
    provider: str,
    model: str | None,
    candidate_count: int,
) -> None:
    skipped_total = int(sum(mismatch_counts.values()))
    if candidate_count > 0:
        try:
            from guardian.core.metrics import (
                MEMORYOS_EMBEDDING_CANDIDATES_TOTAL,
                MEMORYOS_EMBEDDING_DIMENSION_SKIPS_TOTAL,
            )

            MEMORYOS_EMBEDDING_CANDIDATES_TOTAL.labels(module=module).inc(
                candidate_count
            )
            if skipped_total:
                MEMORYOS_EMBEDDING_DIMENSION_SKIPS_TOTAL.labels(
                    module=module
                ).inc(skipped_total)
        except Exception:
            pass

    if skipped_total <= 0:
        return

    skip_ratio = (
        float(skipped_total) / float(candidate_count)
        if candidate_count > 0
        else 1.0
    )
    for candidate_dim, count in sorted(mismatch_counts.items()):
        payload = {
            "module": module,
            "query_dim": int(query_dim),
            "candidate_dim": int(candidate_dim),
            "provider": provider,
            "model": model,
            "skipped_count": int(count),
            "candidate_count": int(candidate_count),
            "skip_ratio": skip_ratio,
        }
        logger.warning(
            "memoryos.embedding.dimension_skip %s",
            json.dumps(payload, sort_keys=True),
        )

    if candidate_count > 0 and skip_ratio > 0.30:
        logger.warning(
            "memoryos.embedding.high_skip_ratio %s",
            json.dumps(
                {
                    "module": module,
                    "query_dim": int(query_dim),
                    "provider": provider,
                    "model": model,
                    "skipped_count": int(skipped_total),
                    "candidate_count": int(candidate_count),
                    "skip_ratio": skip_ratio,
                },
                sort_keys=True,
            ),
        )


class LongTermMemory:
    def __init__(
        self,
        file_path,
        knowledge_capacity=100,
        embedder: MemoryOSEmbedder | None = None,
    ):
        self.file_path = file_path
        ensure_directory_exists(self.file_path)
        self.knowledge_capacity = knowledge_capacity
        self.embedder = embedder or _LegacyEmbeddingAdapter()
        self.embedding_provider = get_embedder_provider_name(self.embedder)
        self.embedding_model = get_embedder_model_name(self.embedder)
        self.user_profiles = (
            {}
        )  # {user_id: {data: "profile_string", "last_updated": "timestamp"}}
        # Use deques for knowledge bases to easily manage capacity
        self.knowledge_base = deque(
            maxlen=self.knowledge_capacity
        )  # For general/user private knowledge
        self.assistant_knowledge = deque(
            maxlen=self.knowledge_capacity
        )  # For assistant specific knowledge
        self.conversation_summaries = {}
        self.conversations = deque(
            maxlen=self.knowledge_capacity
        )  # Store raw conversation records (optionally upserted by id)
        self.load()

    def update_user_profile(self, user_id, new_data, merge=True):
        if (
            merge
            and user_id in self.user_profiles
            and self.user_profiles[user_id].get("data")
        ):  # Check if data exists
            current_data = self.user_profiles[user_id]["data"]
            if isinstance(current_data, str) and isinstance(new_data, str):
                updated_data = f"{current_data}\n\n--- Updated on {get_timestamp()} ---\n{new_data}"
            else:  # Fallback to overwrite if types are not strings or for more complex merge
                updated_data = new_data
        else:
            # If merge=False or no existing data, replace with new data
            updated_data = new_data

        self.user_profiles[user_id] = {
            "data": updated_data,
            "last_updated": get_timestamp(),
        }
        logger.info(
            f"LongTermMemory: Updated user profile for {user_id} (merge={merge})."
        )
        self.save()

    def get_raw_user_profile(self, user_id):
        return self.user_profiles.get(user_id, {}).get(
            "data", None
        )  # Return None if not found

    def get_user_profile_data(self, user_id):
        return self.user_profiles.get(user_id, {})

    def add_knowledge_entry(
        self, knowledge_text, knowledge_deque: deque, type_name="knowledge"
    ):
        if not knowledge_text or knowledge_text.strip().lower() in [
            "",
            "none",
            "- none",
            "- none.",
        ]:
            logger.info(
                f"LongTermMemory: Empty {type_name} received, not saving."
            )
            return

        # If deque is full, the oldest item is automatically removed when appending.
        vec_raw = _normalize_embed_vector(self.embedder.embed(knowledge_text))
        vec = normalize_vector(vec_raw).tolist()
        entry = {
            "knowledge": knowledge_text,
            "timestamp": get_timestamp(),
            "knowledge_embedding": vec,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_dim": int(vec_raw.shape[0]) if vec_raw.size else 0,
        }
        knowledge_deque.append(entry)
        logger.info(
            f"LongTermMemory: Added {type_name}. Current count: {len(knowledge_deque)}."
        )
        self.save()

    def add_user_knowledge(self, knowledge_text):
        self.add_knowledge_entry(
            knowledge_text, self.knowledge_base, "user knowledge"
        )

    def add_assistant_knowledge(self, knowledge_text):
        self.add_knowledge_entry(
            knowledge_text, self.assistant_knowledge, "assistant knowledge"
        )

    def get_user_knowledge(self):
        return list(self.knowledge_base)

    def get_assistant_knowledge(self):
        return list(self.assistant_knowledge)

    def _search_knowledge_deque(
        self, query, knowledge_deque: deque, threshold=0.1, top_k=5
    ):
        if not knowledge_deque:
            return []

        if faiss is None:
            logger.error(
                "FAISS library not available. Install faiss-cpu to enable vector search."
            )
            return []

        query_vec_raw = _normalize_embed_vector(self.embedder.embed(query))
        query_vec = normalize_vector(query_vec_raw)
        query_dim = int(query_vec.shape[0]) if query_vec.size else 0

        embeddings = []
        valid_entries = []
        mismatch_counts: dict[int, int] = {}
        candidate_count = len(knowledge_deque)
        for entry in knowledge_deque:
            if "knowledge_embedding" in entry and entry["knowledge_embedding"]:
                candidate_vec = np.array(
                    entry["knowledge_embedding"], dtype=np.float32
                )
                candidate_dim = (
                    int(entry.get("embedding_dim"))
                    if entry.get("embedding_dim") is not None
                    else int(candidate_vec.shape[0])
                )
                if candidate_dim != query_dim:
                    mismatch_counts[candidate_dim] = (
                        mismatch_counts.get(candidate_dim, 0) + 1
                    )
                    continue
                embeddings.append(candidate_vec)
                valid_entries.append(entry)
            else:
                logger.warning(
                    f"Warning: Entry without embedding found in knowledge_deque: {entry.get('knowledge','N/A')[:50]}"
                )

        _emit_dimension_skip_events(
            module="long_term.search_knowledge",
            query_dim=query_dim,
            mismatch_counts=mismatch_counts,
            provider=self.embedding_provider,
            model=self.embedding_model,
            candidate_count=candidate_count,
        )

        if not embeddings:
            return []

        embeddings_np = np.array(embeddings, dtype=np.float32)
        if embeddings_np.ndim == 1:  # Single item case
            if embeddings_np.shape[0] == 0:
                return []  # Empty embeddings
            embeddings_np = embeddings_np.reshape(1, -1)

        if embeddings_np.shape[0] == 0:  # No valid embeddings
            return []

        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatIP(dim)  # Using Inner Product for similarity
        index.add(embeddings_np)

        query_arr = np.array([query_vec], dtype=np.float32)
        distances, indices = index.search(
            query_arr, min(top_k, len(valid_entries))
        )  # Search at most k or length of valid_entries

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # faiss returns -1 for no valid index
                similarity_score = float(
                    distances[0][i]
                )  # For IndexFlatIP, distance is the dot product (similarity)
                if similarity_score >= threshold:
                    results.append(
                        valid_entries[idx]
                    )  # Add the original entry dict

        return results  # FAISS with IndexFlatIP already returns sorted by descending similarity

    def search_user_knowledge(self, query, threshold=0.1, top_k=5):
        results = self._search_knowledge_deque(
            query, self.knowledge_base, threshold, top_k
        )
        logger.info(
            f"LongTermMemory: Searched user knowledge for '{query[:30]}...'. Found {len(results)} matches."
        )
        return results

    def search_assistant_knowledge(self, query, threshold=0.1, top_k=5):
        results = self._search_knowledge_deque(
            query, self.assistant_knowledge, threshold, top_k
        )
        logger.info(
            f"LongTermMemory: Searched assistant knowledge for '{query[:30]}...'. Found {len(results)} matches."
        )
        return results

    def save(self):
        data = {
            "user_profiles": self.user_profiles,
            "knowledge_base": list(
                self.knowledge_base
            ),  # Convert deques to lists for JSON serialization
            "assistant_knowledge": list(self.assistant_knowledge),
            "conversation_summaries": getattr(
                self, "conversation_summaries", {}
            ),
            "conversations": list(self.conversations),
        }
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.exception(
                f"Error saving LongTermMemory to {self.file_path}: {e}"
            )

    def load(self):
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
                self.user_profiles = data.get("user_profiles", {})
                # Load into deques, respecting maxlen
                kb_data = data.get("knowledge_base", [])
                self.knowledge_base = deque(
                    kb_data, maxlen=self.knowledge_capacity
                )

                ak_data = data.get("assistant_knowledge", [])
                self.assistant_knowledge = deque(
                    ak_data, maxlen=self.knowledge_capacity
                )

                self.conversation_summaries = data.get(
                    "conversation_summaries", {}
                )
                conv_data = data.get("conversations", [])
                self.conversations = deque(
                    conv_data, maxlen=self.knowledge_capacity
                )

            logger.info(f"LongTermMemory: Loaded from {self.file_path}.")
        except FileNotFoundError:
            logger.info(
                f"LongTermMemory: No history file found at {self.file_path}. Initializing new memory."
            )
        except json.JSONDecodeError:
            logger.warning(
                f"LongTermMemory: Error decoding JSON from {self.file_path}. Initializing new memory."
            )
        except Exception as e:
            logger.exception(
                f"LongTermMemory: An unexpected error occurred during load from {self.file_path}: {e}. Initializing new memory."
            )

    def store_conversation_summary(self, conversation_id, summary_text):
        """Store a summary for a given conversation."""
        self.conversation_summaries[conversation_id] = {
            "summary": summary_text,
            "timestamp": get_timestamp(),
        }
        logger.info(
            f"LongTermMemory: Stored summary for conversation {conversation_id}."
        )
        self.save()

    def get_conversation_summary(self, conversation_id):
        """Retrieve the summary for a given conversation."""
        return (
            getattr(self, "conversation_summaries", {})
            .get(conversation_id, {})
            .get("summary", None)
        )

    def store_conversation(self, conversation):
        """Store or replace a full conversation record.

        Expected shape (flexible):
            {
                "conversation_id": str,      # required
                "messages": list,            # optional but recommended
                ...                            # any other metadata
            }
        """
        if not isinstance(conversation, dict):
            logger.error("LongTermMemory: store_conversation expects a dict.")
            return
        conv_id = conversation.get("conversation_id")
        if not conv_id:
            logger.error(
                "LongTermMemory: store_conversation requires 'conversation_id'."
            )
            return

        # Remove any existing record with the same id (upsert behavior)
        try:
            self.conversations = deque(
                [
                    c
                    for c in self.conversations
                    if c.get("conversation_id") != conv_id
                ],
                maxlen=self.knowledge_capacity,
            )
        except Exception:
            # If anything odd happens, fall back to rebuilding
            tmp = []
            for c in list(self.conversations):
                try:
                    if c.get("conversation_id") != conv_id:
                        tmp.append(c)
                except Exception:
                    continue
            self.conversations = deque(tmp, maxlen=self.knowledge_capacity)

        # Attach/refresh timestamp and append
        record = dict(conversation)
        record.setdefault("timestamp", get_timestamp())
        self.conversations.append(record)
        logger.info(
            f"LongTermMemory: Stored conversation {conv_id} (size={len(self.conversations)})."
        )
        self.save()

    def get_conversations(self, conversation_id=None):
        """Return all conversations or a specific one by id."""
        if conversation_id is None:
            return list(self.conversations)
        for c in self.conversations:
            if c.get("conversation_id") == conversation_id:
                return c
        return None

    def upsert_conversation(self, conversation):
        """Alias for store_conversation for clarity."""
        return self.store_conversation(conversation)
