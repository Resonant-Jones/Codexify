from typing import Dict, Optional

from memoryos.long_term import LongTermMemory
from memoryos.mid_term import MidTermMemory
from memoryos.short_term import ShortTermMemory
from memoryos.utils import (
    OpenAIClient,
    check_conversation_continuity,
    generate_id,
    generate_page_meta_info,
    get_timestamp,
    gpt_generate_multi_summary,
    llm_extract_keywords,
)


class Updater:
    def __init__(
        self,
        short_term_memory: ShortTermMemory,
        mid_term_memory: MidTermMemory,
        long_term_memory: LongTermMemory,
        client: OpenAIClient,
        topic_similarity_threshold=0.5,
        llm_model="gpt-4o-mini",
        codemap: Optional[Dict] = None,
    ):
        self.short_term_memory = short_term_memory
        self.mid_term_memory = mid_term_memory
        self.long_term_memory = long_term_memory
        self.client = client
        self.topic_similarity_threshold = topic_similarity_threshold
        self.last_evicted_page_for_continuity = (
            None  # Tracks the actual last page object for continuity checks
        )
        self.llm_model = llm_model
        self.codemap = codemap
        # Codemap is used for agent introspection and contextual awareness

    def _update_linked_pages_meta_info(self, start_page_id, new_meta_info):
        """
        Updates meta_info for a chain of connected pages starting from start_page_id.
        This is a simplified version. Assumes that once a chain is broken (no pre_page),
        we don't need to go further back. Updates forward as well.
        """
        # Go backward
        q = [start_page_id]
        visited = {start_page_id}

        head = 0
        while head < len(q):
            current_page_id = q[head]
            head += 1
            page = self.mid_term_memory.get_page_by_id(current_page_id)
            if page:
                page["meta_info"] = new_meta_info
                # Check previous page
                prev_id = page.get("pre_page")
                if prev_id and prev_id not in visited:
                    q.append(prev_id)
                    visited.add(prev_id)
                # Check next page
                next_id = page.get("next_page")
                if next_id and next_id not in visited:
                    q.append(next_id)
                    visited.add(next_id)
        if q:  # If any pages were updated
            self.mid_term_memory.save()  # Save mid-term memory after updates

    def process_short_term_to_mid_term(self):
        evicted_qas = []
        while self.short_term_memory.is_full():
            qa = self.short_term_memory.pop_oldest()
            if qa and qa.get("user_input") and qa.get("agent_response"):
                evicted_qas.append(qa)

        if not evicted_qas:
            print("Updater: No QAs evicted from short-term memory.")
            return

        print(
            f"Updater: Processing {len(evicted_qas)} QAs from short-term to mid-term."
        )

        # 1. Create page structures and handle continuity within the evicted batch
        current_batch_pages = []
        temp_last_page_in_batch = (
            self.last_evicted_page_for_continuity
        )  # Carry over from previous batch if any

        for qa_pair in evicted_qas:
            current_page_obj = {
                "page_id": generate_id("page"),
                "user_input": qa_pair.get("user_input", ""),
                "agent_response": qa_pair.get("agent_response", ""),
                "timestamp": qa_pair.get("timestamp", get_timestamp()),
                "preloaded": False,  # Default for new pages from short-term
                "analyzed": False,  # Default for new pages from short-term
                "pre_page": None,
                "next_page": None,
                "meta_info": None,
            }

            is_continuous = check_conversation_continuity(
                temp_last_page_in_batch,
                current_page_obj,
                self.client,
                model=self.llm_model,
            )

            if is_continuous and temp_last_page_in_batch:
                current_page_obj["pre_page"] = temp_last_page_in_batch["page_id"]
                # The actual next_page for temp_last_page_in_batch will be set when it's stored in mid-term
                # or if it's already there, it needs an update. This linking is tricky.
                # For now, we establish the link from current to previous.
                # MidTermMemory's update_page_connections can fix the other side if pages are already there.

                # Meta info generation based on continuity
                last_meta = temp_last_page_in_batch.get("meta_info")
                new_meta = generate_page_meta_info(
                    last_meta, current_page_obj, self.client, model=self.llm_model
                )
                current_page_obj["meta_info"] = new_meta
                # If temp_last_page_in_batch was part of a chain, its meta_info and subsequent ones should update.
                # This implies that meta_info should perhaps be updated more globally or propagated.
                # For now, new_meta applies to current_page_obj and potentially its chain.
                # We can call _update_linked_pages_meta_info if temp_last_page_in_batch is in mid-term already.
                if temp_last_page_in_batch.get(
                    "page_id"
                ) and self.mid_term_memory.get_page_by_id(
                    temp_last_page_in_batch["page_id"]
                ):
                    self._update_linked_pages_meta_info(
                        temp_last_page_in_batch["page_id"], new_meta
                    )
            else:
                # Start of a new chain or no previous page
                current_page_obj["meta_info"] = generate_page_meta_info(
                    None, current_page_obj, self.client, model=self.llm_model
                )

            current_batch_pages.append(current_page_obj)
            temp_last_page_in_batch = (
                current_page_obj  # Update for the next iteration in this batch
            )

        # Update the global last evicted page for the next run of this method
        if current_batch_pages:
            self.last_evicted_page_for_continuity = current_batch_pages[-1]

        # 2. Consolidate text from current_batch_pages for multi-summary
        if not current_batch_pages:
            return

        input_text_for_summary = "\n".join(
            [
                f"User: {p.get('user_input','')}\nAssistant: {p.get('agent_response','')}"
                for p in current_batch_pages
            ]
        )

        print("Updater: Generating multi-topic summary for the evicted batch...")
        multi_summary_result = gpt_generate_multi_summary(
            input_text_for_summary, self.client, model=self.llm_model
        )

        # 3. Insert pages into MidTermMemory based on summaries
        if multi_summary_result and multi_summary_result.get("summaries"):
            for summary_item in multi_summary_result["summaries"]:
                theme_summary = summary_item.get(
                    "content", "General summary of recent interactions."
                )
                theme_keywords = summary_item.get("keywords", [])
                print(
                    f"Updater: Processing theme '{summary_item.get('theme')}' for mid-term insertion."
                )

                # Pass the already processed pages (with IDs, embeddings to be added by MidTermMemory if not present)
                self.mid_term_memory.insert_pages_into_session(
                    summary_for_new_pages=theme_summary,
                    keywords_for_new_pages=theme_keywords,
                    pages_to_insert=current_batch_pages,  # These pages now have pre_page, next_page, meta_info set up
                    similarity_threshold=self.topic_similarity_threshold,
                )
        else:
            # Fallback: if no summaries, add as one session or handle as a single block
            print(
                "Updater: No specific themes from multi-summary. Adding batch as a general session."
            )
            fallback_summary = "General conversation segment from short-term memory."
            fallback_keywords = (
                llm_extract_keywords(
                    input_text_for_summary, self.client, model=self.llm_model
                )
                if input_text_for_summary
                else []
            )
            self.mid_term_memory.insert_pages_into_session(
                summary_for_new_pages=fallback_summary,
                keywords_for_new_pages=list(fallback_keywords),
                pages_to_insert=current_batch_pages,
                similarity_threshold=self.topic_similarity_threshold,
            )

        # After pages are in mid-term, ensure their connections are doubly linked if needed.
        # MidTermMemory.insert_pages_into_session should ideally handle this internally
        # or we might need a separate pass to solidify connections after all insertions.
        for page in current_batch_pages:
            if page.get("pre_page"):
                self.mid_term_memory.update_page_connections(
                    page["pre_page"], page["page_id"]
                )
            if page.get("next_page"):
                self.mid_term_memory.update_page_connections(
                    page["page_id"], page["next_page"]
                )  # This seems redundant if next is set by prior
        if current_batch_pages:  # Save if any pages were processed
            self.mid_term_memory.save()

    def update_long_term_from_analysis(self, user_id, profile_analysis_result):
        """
        Updates long-term memory based on the results of a personality/knowledge analysis.
        profile_analysis_result is expected to be a dict with keys like "profile", "private", "assistant_knowledge".
        """
        if not profile_analysis_result:
            print("Updater: No analysis result provided for long-term update.")
            return

        new_profile_text = profile_analysis_result.get("profile")
        if new_profile_text and new_profile_text.lower() != "none":
            print(f"Updater: Updating user profile for {user_id} in LongTermMemory.")
            current_profile = self.long_term_memory.get_raw_user_profile(user_id)
            if current_profile and current_profile.lower() != "none":
                updated_profile = gpt_update_profile(
                    current_profile, new_profile_text, self.client
                )
            else:
                updated_profile = new_profile_text  # First profile
            self.long_term_memory.update_user_profile(user_id, updated_profile)

        user_private_knowledge = profile_analysis_result.get("private")
        if user_private_knowledge and user_private_knowledge.lower() != "none":
            print(
                f"Updater: Adding user private knowledge for {user_id} to LongTermMemory."
            )
            # Split if multiple lines, assuming each line is a distinct piece of knowledge
            for line in user_private_knowledge.split("\n"):
                if line.strip() and line.strip().lower() not in [
                    "none",
                    "- none",
                    "- none.",
                ]:
                    self.long_term_memory.add_user_knowledge(line.strip())

        assistant_knowledge_text = profile_analysis_result.get("assistant_knowledge")
        if assistant_knowledge_text and assistant_knowledge_text.lower() != "none":
            print("Updater: Adding assistant knowledge to LongTermMemory.")
            for line in assistant_knowledge_text.split("\n"):
                if line.strip() and line.strip().lower() not in [
                    "none",
                    "- none",
                    "- none.",
                ]:
                    self.long_term_memory.add_assistant_knowledge(line.strip())

        # LongTermMemory.save() is called by its add/update methods
