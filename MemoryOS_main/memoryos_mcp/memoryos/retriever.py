import heapq
from collections import deque

from long_term import LongTermMemory
from mid_term import MidTermMemory
from short_term import ShortTermMemory
from utils import (  # OpenAIClient might not be directly used here but good for consistency
    OpenAIClient, get_timestamp)

# from .updater import Updater # Updater is not directly used by Retriever


class Retriever:
    def __init__(
        self,
        mid_term_memory: MidTermMemory,
        long_term_memory: LongTermMemory,
        assistant_long_term_memory: LongTermMemory = None,  # Add assistant LTM
        # client: OpenAIClient, # Not strictly needed if all LLM calls are within memory modules
        queue_capacity=7,
    ):  # Default from main_memoybank was 7 for retrieval_queue
        # Short term memory is usually for direct context, not primary retrieval source here
        # self.short_term_memory = short_term_memory
        self.mid_term_memory = mid_term_memory
        self.long_term_memory = long_term_memory
        self.assistant_long_term_memory = (
            assistant_long_term_memory  # Store assistant LTM reference
        )
        # self.client = client
        self.retrieval_queue_capacity = queue_capacity
        # self.retrieval_queue = deque(maxlen=queue_capacity) # This was instance level, but retrieve returns it, so maybe not needed as instance var

    def retrieve_context(
        self,
        user_query: str,
        user_id: str,  # Needed for profile, can be used for context filtering if desired
        segment_similarity_threshold=0.1,  # From main_memoybank example
        page_similarity_threshold=0.1,  # From main_memoybank example
        knowledge_threshold=0.01,  # From main_memoybank example
        top_k_sessions=5,  # From MidTermMemory search default
        top_k_knowledge=20,  # Default for knowledge search
    ):
        print(f"Retriever: Starting retrieval for query: '{user_query[:50]}...'")

        # 1. Retrieve from Mid-Term Memory
        # MidTermMemory.search_sessions now takes client for its internal keyword extraction
        # It also returns a more structured result including scores.
        matched_sessions = self.mid_term_memory.search_sessions(
            query_text=user_query,
            segment_similarity_threshold=segment_similarity_threshold,
            page_similarity_threshold=page_similarity_threshold,
            top_k_sessions=top_k_sessions,
        )

        # Use a heap to get top N pages across all relevant sessions based on their scores
        top_pages_heap = []
        page_counter = 0  # Add counter to ensure unique comparison
        for session_match in matched_sessions:
            for page_match in session_match.get("matched_pages", []):
                page_data = page_match["page_data"]
                page_score = page_match["score"]  # Using the page score directly

                # Add session relevance score to page score or combine them?
                # For now, using page_score. Could be: page_score * session_match["session_relevance_score"]
                combined_score = (
                    page_score  # Potentially adjust with session_relevance_score
                )

                if len(top_pages_heap) < self.retrieval_queue_capacity:
                    heapq.heappush(
                        top_pages_heap, (combined_score, page_counter, page_data)
                    )
                    page_counter += 1
                elif (
                    combined_score > top_pages_heap[0][0]
                ):  # If current page is better than the worst in heap
                    heapq.heappop(top_pages_heap)
                    heapq.heappush(
                        top_pages_heap, (combined_score, page_counter, page_data)
                    )
                    page_counter += 1

        # Extract pages from heap, already sorted by heapq property (smallest first)
        # We want highest scores, so either use a max-heap or sort after popping from min-heap.
        retrieved_mid_term_pages = [
            item[2] for item in sorted(top_pages_heap, key=lambda x: x[0], reverse=True)
        ]
        print(
            f"Retriever: Mid-term memory recalled {len(retrieved_mid_term_pages)} pages."
        )

        # 2. Retrieve from Long-Term User Knowledge (specific to the user)
        # Assuming LongTermMemory for a user stores their specific knowledge/private data.
        # The main LongTermMemory class in `long_term.py` has `search_user_knowledge` which doesn't need user_id as it's implicit in the instance
        # However, if a single LTM instance handles multiple users, it would need user_id.
        # For the Memoryos class, LTM will be user-specific or assistant-specific.
        retrieved_user_knowledge = self.long_term_memory.search_user_knowledge(
            user_query, threshold=knowledge_threshold, top_k=top_k_knowledge
        )
        print(
            f"Retriever: Long-term user knowledge recalled {len(retrieved_user_knowledge)} items."
        )

        # 3. Retrieve from Long-Term Assistant Knowledge (general for the assistant)
        # This requires a separate LTM instance or a method in LTM that queries a different knowledge base.
        # In our Memoryos structure, there will be a separate LTM for assistant.
        # For now, assuming self.long_term_memory is the USER's LTM.
        # The Memoryos class will handle passing the correct LTM instance for assistant knowledge.
        # This function will just return what it can from the provided LTM.
        # If assistant_ltm is passed, it can be used: self.assistant_long_term_memory.search_assistant_knowledge(...)
        retrieved_assistant_knowledge = []
        if self.assistant_long_term_memory:
            retrieved_assistant_knowledge = (
                self.assistant_long_term_memory.search_assistant_knowledge(
                    user_query, threshold=knowledge_threshold, top_k=top_k_knowledge
                )
            )
            print(
                f"Retriever: Long-term assistant knowledge recalled {len(retrieved_assistant_knowledge)} items."
            )
        else:
            print(
                "Retriever: No assistant long-term memory provided, skipping assistant knowledge retrieval."
            )

        return {
            "retrieved_pages": retrieved_mid_term_pages,  # List of page dicts
            "retrieved_user_knowledge": retrieved_user_knowledge,  # List of knowledge entry dicts
            "retrieved_assistant_knowledge": retrieved_assistant_knowledge,  # List of assistant knowledge entry dicts
            "retrieved_at": get_timestamp(),
        }
