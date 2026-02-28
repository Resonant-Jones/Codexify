import heapq
import json
import logging
from collections import defaultdict
from typing import Any

import faiss
import numpy as np

logger = logging.getLogger(__name__)

from .embedders.base import (
    MemoryOSEmbedder,
    get_embedder_model_name,
    get_embedder_provider_name,
)
from .utils import (
    OpenAIClient,
    compute_time_decay,
    ensure_directory_exists,
    generate_id,
    get_timestamp,
    llm_extract_keywords,
    normalize_vector,
)

# Heat computation constants (can be tuned or made configurable)
HEAT_ALPHA = 1.0
HEAT_BETA = 1.0
HEAT_GAMMA = 1
RECENCY_TAU_HOURS = 24  # For R_recency calculation in compute_segment_heat


def _normalize_embed_vector(raw: Any) -> np.ndarray:
    vec = np.asarray(raw, dtype=np.float32)
    if vec.ndim == 0:
        return np.array([], dtype=np.float32)
    if vec.ndim > 1:
        vec = vec.reshape(-1)
    return vec


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


def compute_segment_heat(
    session,
    alpha=HEAT_ALPHA,
    beta=HEAT_BETA,
    gamma=HEAT_GAMMA,
    tau_hours=RECENCY_TAU_HOURS,
):
    N_visit = session.get("N_visit", 0)
    L_interaction = session.get("L_interaction", 0)

    # Calculate recency based on last_visit_time
    R_recency = 1.0  # Default if no last_visit_time
    if session.get("last_visit_time"):
        R_recency = compute_time_decay(
            session["last_visit_time"], get_timestamp(), tau_hours
        )

    session["R_recency"] = R_recency  # Update session's recency factor
    return alpha * N_visit + beta * L_interaction + gamma * R_recency


class MidTermMemory:
    def __init__(
        self,
        file_path: str,
        client: OpenAIClient,
        embedder: MemoryOSEmbedder,
        max_capacity=2000,
    ):
        self.file_path = file_path
        ensure_directory_exists(self.file_path)
        self.client = client
        self.embedder = embedder
        self.embedding_provider = get_embedder_provider_name(embedder)
        self.embedding_model = get_embedder_model_name(embedder)
        self.max_capacity = max_capacity
        self.sessions = {}  # {session_id: session_object}
        self.access_frequency = defaultdict(
            int
        )  # {session_id: access_count_for_lfu}
        self.heap = (
            []
        )  # Min-heap storing (-H_segment, session_id) for hottest segments
        self.load()

    def get_page_by_id(self, page_id):
        for session in self.sessions.values():
            for page in session.get("details", []):
                if page.get("page_id") == page_id:
                    return page
        return None

    def update_page_connections(self, prev_page_id, next_page_id):
        if prev_page_id:
            prev_page = self.get_page_by_id(prev_page_id)
            if prev_page:
                prev_page["next_page"] = next_page_id
        if next_page_id:
            next_page = self.get_page_by_id(next_page_id)
            if next_page:
                next_page["pre_page"] = prev_page_id
        # self.save() # Avoid saving on every minor update; save at higher level operations

    def evict_lfu(self):
        if not self.access_frequency or not self.sessions:
            return

        lfu_sid = min(self.access_frequency, key=self.access_frequency.get)
        logger.info(
            f"MidTermMemory: LFU eviction. Session {lfu_sid} has lowest access frequency."
        )

        if lfu_sid not in self.sessions:
            del self.access_frequency[
                lfu_sid
            ]  # Clean up access frequency if session already gone
            self.rebuild_heap()
            return

        session_to_delete = self.sessions.pop(lfu_sid)  # Remove from sessions
        del self.access_frequency[lfu_sid]  # Remove from LFU tracking

        # Clean up page connections if this session's pages were linked
        for page in session_to_delete.get("details", []):
            prev_page_id = page.get("pre_page")
            next_page_id = page.get("next_page")
            # If a page from this session was linked to an external page, nullify the external link
            if prev_page_id and not self.get_page_by_id(
                prev_page_id
            ):  # Check if prev page is still in memory
                # This case should ideally not happen if connections are within sessions or handled carefully
                pass
            if next_page_id and not self.get_page_by_id(next_page_id):
                pass
            # More robustly, one might need to search all other sessions if inter-session linking was allowed
            # For now, assuming internal consistency or that MemoryOS class manages higher-level links

        self.rebuild_heap()
        self.save()
        logger.info(f"MidTermMemory: Evicted session {lfu_sid}.")

    def add_session(self, summary, details):
        session_id = generate_id("session")
        summary_raw = _normalize_embed_vector(self.embedder.embed(summary))
        summary_vec = normalize_vector(summary_raw).tolist()
        summary_dim = int(summary_raw.shape[0]) if summary_raw.size else 0
        summary_keywords = list(
            llm_extract_keywords(summary, client=self.client)
        )

        processed_details = []
        for page_data in details:
            page_id = page_data.get("page_id", generate_id("page"))
            full_text = f"User: {page_data.get('user_input','')} Assistant: {page_data.get('agent_response','')}"
            inp_raw = _normalize_embed_vector(self.embedder.embed(full_text))
            inp_vec = normalize_vector(inp_raw).tolist()
            inp_dim = int(inp_raw.shape[0]) if inp_raw.size else 0
            page_keywords = list(
                llm_extract_keywords(full_text, client=self.client)
            )

            processed_page = {
                **page_data,  # Carry over existing fields like user_input, agent_response, timestamp
                "page_id": page_id,
                "page_embedding": inp_vec,
                "page_keywords": page_keywords,
                "preloaded": page_data.get(
                    "preloaded", False
                ),  # Preserve if passed
                "analyzed": page_data.get(
                    "analyzed", False
                ),  # Preserve if passed
                "embedding_provider": self.embedding_provider,
                "embedding_model": self.embedding_model,
                "embedding_dim": inp_dim,
                # pre_page, next_page, meta_info are handled by DynamicUpdater
            }
            processed_details.append(processed_page)

        current_ts = get_timestamp()
        session_obj = {
            "id": session_id,
            "summary": summary,
            "summary_keywords": summary_keywords,
            "summary_embedding": summary_vec,
            "details": processed_details,
            "L_interaction": len(processed_details),
            "R_recency": 1.0,  # Initial recency
            "N_visit": 0,
            "H_segment": 0.0,  # Initial heat, will be computed
            "timestamp": current_ts,  # Creation timestamp
            "last_visit_time": current_ts,  # Also initial last_visit_time for recency calc
            "access_count_lfu": 0,  # For LFU eviction policy
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_dim": summary_dim,
        }
        session_obj["H_segment"] = compute_segment_heat(session_obj)
        self.sessions[session_id] = session_obj
        self.access_frequency[session_id] = 0  # Initialize for LFU
        heapq.heappush(
            self.heap, (-session_obj["H_segment"], session_id)
        )  # Use negative heat for max-heap behavior

        logger.info(
            f"MidTermMemory: Added new session {session_id}. Initial heat: {session_obj['H_segment']:.2f}."
        )
        if len(self.sessions) > self.max_capacity:
            self.evict_lfu()
        self.save()
        return session_id

    def rebuild_heap(self):
        self.heap = []
        for sid, session_data in self.sessions.items():
            # Ensure H_segment is up-to-date before rebuilding heap if necessary
            # session_data["H_segment"] = compute_segment_heat(session_data)
            heapq.heappush(self.heap, (-session_data["H_segment"], sid))
        # heapq.heapify(self.heap) # Not needed if pushing one by one
        # No save here, it's an internal operation often followed by other ops that save

    def insert_pages_into_session(
        self,
        summary_for_new_pages,
        keywords_for_new_pages,
        pages_to_insert,
        similarity_threshold=0.6,
        keyword_similarity_alpha=1.0,
    ):
        if not self.sessions:  # If no existing sessions, just add as a new one
            logger.info(
                "MidTermMemory: No existing sessions. Adding new session directly."
            )
            return self.add_session(summary_for_new_pages, pages_to_insert)

        new_summary_vec = _normalize_embed_vector(
            self.embedder.embed(summary_for_new_pages)
        )
        new_summary_vec = normalize_vector(new_summary_vec)
        new_summary_dim = (
            int(new_summary_vec.shape[0]) if new_summary_vec.size else 0
        )

        best_sid = None
        best_overall_score = -1
        mismatch_counts: dict[int, int] = defaultdict(int)
        compared_sessions = 0

        for sid, existing_session in self.sessions.items():
            existing_summary_vec = np.array(
                existing_session["summary_embedding"], dtype=np.float32
            )
            existing_dim = (
                int(existing_session.get("embedding_dim"))
                if existing_session.get("embedding_dim") is not None
                else int(existing_summary_vec.shape[0])
            )
            compared_sessions += 1
            if existing_dim != new_summary_dim:
                mismatch_counts[existing_dim] += 1
                continue
            semantic_sim = float(np.dot(existing_summary_vec, new_summary_vec))

            # Keyword similarity (Jaccard index based)
            existing_keywords = set(
                existing_session.get("summary_keywords", [])
            )
            new_keywords_set = set(keywords_for_new_pages)
            s_topic_keywords = 0
            if existing_keywords and new_keywords_set:
                intersection = len(
                    existing_keywords.intersection(new_keywords_set)
                )
                union = len(existing_keywords.union(new_keywords_set))
                if union > 0:
                    s_topic_keywords = intersection / union

            overall_score = (
                semantic_sim + keyword_similarity_alpha * s_topic_keywords
            )

            if overall_score > best_overall_score:
                best_overall_score = overall_score
                best_sid = sid

        _emit_dimension_skip_events(
            module="mid_term.insert_pages",
            query_dim=new_summary_dim,
            mismatch_counts=mismatch_counts,
            provider=self.embedding_provider,
            model=self.embedding_model,
            candidate_count=compared_sessions,
        )

        if best_sid and best_overall_score >= similarity_threshold:
            logger.info(
                f"MidTermMemory: Merging pages into session {best_sid}. Score: {best_overall_score:.2f} (Threshold: {similarity_threshold})"
            )
            target_session = self.sessions[best_sid]

            processed_new_pages = []
            for page_data in pages_to_insert:
                page_id = page_data.get(
                    "page_id", generate_id("page")
                )  # Use existing or generate new ID
                full_text = f"User: {page_data.get('user_input','')} Assistant: {page_data.get('agent_response','')}"
                inp_raw = _normalize_embed_vector(
                    self.embedder.embed(full_text)
                )
                inp_vec = normalize_vector(inp_raw).tolist()
                inp_dim = int(inp_raw.shape[0]) if inp_raw.size else 0
                page_keywords_current = list(
                    llm_extract_keywords(full_text, client=self.client)
                )

                processed_page = {
                    **page_data,  # Carry over existing fields
                    "page_id": page_id,
                    "page_embedding": inp_vec,
                    "page_keywords": page_keywords_current,
                    "embedding_provider": self.embedding_provider,
                    "embedding_model": self.embedding_model,
                    "embedding_dim": inp_dim,
                    # analyzed, preloaded flags should be part of page_data if set
                }
                target_session["details"].append(processed_page)
                processed_new_pages.append(processed_page)

            target_session["L_interaction"] += len(pages_to_insert)
            target_session[
                "last_visit_time"
            ] = get_timestamp()  # Update last visit time on modification
            target_session["H_segment"] = compute_segment_heat(target_session)
            target_session["embedding_provider"] = self.embedding_provider
            target_session["embedding_model"] = self.embedding_model
            target_session["embedding_dim"] = new_summary_dim
            self.rebuild_heap()  # Rebuild heap as heat has changed
            self.save()
            return best_sid
        else:
            logger.info(
                f"MidTermMemory: No suitable session to merge (best score {best_overall_score:.2f} < threshold {similarity_threshold}). Creating new session."
            )
            return self.add_session(summary_for_new_pages, pages_to_insert)

    def search_sessions(
        self,
        query_text,
        segment_similarity_threshold=0.1,
        page_similarity_threshold=0.1,
        top_k_sessions=5,
        keyword_alpha=1.0,
        recency_tau_search=3600,
    ):
        if not self.sessions:
            return []

        query_raw = _normalize_embed_vector(self.embedder.embed(query_text))
        query_vec = normalize_vector(query_raw)
        query_dim = int(query_vec.shape[0]) if query_vec.size else 0
        query_keywords = set(
            llm_extract_keywords(query_text, client=self.client)
        )

        session_ids = list(self.sessions.keys())
        if not session_ids:
            return []

        summary_embeddings_list = []
        searchable_session_ids = []
        mismatch_counts: dict[int, int] = defaultdict(int)
        for session_id in session_ids:
            session = self.sessions[session_id]
            summary_vec = np.array(
                session.get("summary_embedding", []), dtype=np.float32
            )
            summary_dim = (
                int(session.get("embedding_dim"))
                if session.get("embedding_dim") is not None
                else int(summary_vec.shape[0])
            )
            if summary_dim != query_dim:
                mismatch_counts[summary_dim] += 1
                continue
            searchable_session_ids.append(session_id)
            summary_embeddings_list.append(summary_vec)

        _emit_dimension_skip_events(
            module="mid_term.search_sessions.summary",
            query_dim=query_dim,
            mismatch_counts=mismatch_counts,
            provider=self.embedding_provider,
            model=self.embedding_model,
            candidate_count=len(session_ids),
        )

        if not searchable_session_ids:
            return []

        summary_embeddings_np = np.array(
            summary_embeddings_list, dtype=np.float32
        )

        dim = summary_embeddings_np.shape[1]
        index = faiss.IndexFlatIP(dim)  # Inner product for similarity
        index.add(summary_embeddings_np)

        query_arr_np = np.array([query_vec], dtype=np.float32)
        distances, indices = index.search(
            query_arr_np, min(top_k_sessions, len(searchable_session_ids))
        )

        results = []
        current_time_str = get_timestamp()

        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue

            session_id = searchable_session_ids[idx]
            session = self.sessions[session_id]
            semantic_sim_score = float(
                distances[0][i]
            )  # This is the dot product

            # Keyword similarity for session summary
            session_keywords = set(session.get("summary_keywords", []))
            s_topic_keywords = 0
            if query_keywords and session_keywords:
                intersection = len(
                    query_keywords.intersection(session_keywords)
                )
                union = len(query_keywords.union(session_keywords))
                if union > 0:
                    s_topic_keywords = intersection / union

            # Time decay for session recency in search scoring
            # time_decay_factor = compute_time_decay(session["timestamp"], current_time_str, tau_hours=recency_tau_search)

            # Combined score for session relevance
            session_relevance_score = (
                semantic_sim_score + keyword_alpha * s_topic_keywords
            )

            if session_relevance_score >= segment_similarity_threshold:
                matched_pages_in_session = []
                page_mismatch_counts: dict[int, int] = defaultdict(int)
                page_candidate_count = 0
                for page in session.get("details", []):
                    page_embedding = np.array(
                        page["page_embedding"], dtype=np.float32
                    )
                    page_dim = (
                        int(page.get("embedding_dim"))
                        if page.get("embedding_dim") is not None
                        else int(page_embedding.shape[0])
                    )
                    page_candidate_count += 1
                    if page_dim != query_dim:
                        page_mismatch_counts[page_dim] += 1
                        continue
                    # page_keywords = set(page.get("page_keywords", []))

                    page_sim_score = float(np.dot(page_embedding, query_vec))
                    # Can also add keyword sim for pages if needed, but keeping it simpler for now

                    if page_sim_score >= page_similarity_threshold:
                        matched_pages_in_session.append(
                            {"page_data": page, "score": page_sim_score}
                        )

                _emit_dimension_skip_events(
                    module="mid_term.search_sessions.pages",
                    query_dim=query_dim,
                    mismatch_counts=page_mismatch_counts,
                    provider=self.embedding_provider,
                    model=self.embedding_model,
                    candidate_count=page_candidate_count,
                )

                if matched_pages_in_session:
                    # Update session access stats
                    session["N_visit"] += 1
                    session["last_visit_time"] = current_time_str
                    session["access_count_lfu"] = (
                        session.get("access_count_lfu", 0) + 1
                    )
                    self.access_frequency[session_id] = session[
                        "access_count_lfu"
                    ]
                    session["H_segment"] = compute_segment_heat(session)
                    self.rebuild_heap()  # Heat changed

                    results.append(
                        {
                            "session_id": session_id,
                            "session_summary": session["summary"],
                            "session_relevance_score": session_relevance_score,
                            "matched_pages": sorted(
                                matched_pages_in_session,
                                key=lambda x: x["score"],
                                reverse=True,
                            ),  # Sort pages by score
                        }
                    )

        self.save()  # Save changes from access updates
        # Sort final results by session_relevance_score
        return sorted(
            results, key=lambda x: x["session_relevance_score"], reverse=True
        )

    def save(self):
        # Make a copy for saving to avoid modifying heap during iteration if it happens
        # Though current heap is list of tuples, so direct modification risk is low
        # sessions_to_save = {sid: data for sid, data in self.sessions.items()}
        data_to_save = {
            "sessions": self.sessions,
            "access_frequency": dict(
                self.access_frequency
            ),  # Convert defaultdict to dict for JSON
            # Heap is derived, no need to save typically, but can if desired for faster load
            # "heap_snapshot": self.heap
        }
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"Error saving MidTermMemory to {self.file_path}: {e}")

    def load(self):
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
                self.sessions = data.get("sessions", {})
                self.access_frequency = defaultdict(
                    int, data.get("access_frequency", {})
                )
                self.rebuild_heap()  # Rebuild heap from loaded sessions
            logger.info(
                f"MidTermMemory: Loaded from {self.file_path}. Sessions: {len(self.sessions)}."
            )
        except FileNotFoundError:
            logger.info(
                f"MidTermMemory: No history file found at {self.file_path}. Initializing new memory."
            )
        except json.JSONDecodeError:
            logger.info(
                f"MidTermMemory: Error decoding JSON from {self.file_path}. Initializing new memory."
            )
        except Exception as e:
            logger.error(
                f"MidTermMemory: An unexpected error occurred during load from {self.file_path}: {e}. Initializing new memory."
            )
