def get_all_projects_summary(self) -> list:
    """Returns a list of all known projects from long-term memory."""
    return self.user_long_term_memory.get_all_projects()


def get_threads_by_project(self, project_id: str) -> list:
    """Returns threads associated with a given project ID."""
    return self.user_long_term_memory.get_threads_for_project(project_id)


def get_conversations_by_thread(self, thread_id: str) -> list:
    """Returns conversations associated with a given thread ID."""
    return self.user_long_term_memory.get_conversations_for_thread(thread_id)


def get_conversation_by_id(self, conversation_id: str) -> dict:
    """Returns a specific conversation given its ID."""
    return self.user_long_term_memory.get_conversation(conversation_id)


import json
import os

import memoryos.prompts as prompts
from memoryos.long_term import LongTermMemory
from memoryos.mid_term import MidTermMemory, compute_segment_heat
from memoryos.retriever import Retriever
from memoryos.short_term import ShortTermMemory
from memoryos.updater import Updater
from memoryos.utils import (
    OpenAIClient,
    ensure_directory_exists,
    generate_id,
    get_timestamp,
    gpt_knowledge_extraction,
    gpt_update_profile,
    gpt_user_profile_analysis,
)

from guardian.codemap.generate_codemap import generate_codemap as load_codemap

# Heat threshold for triggering profile/knowledge update from mid-term memory
H_PROFILE_UPDATE_THRESHOLD = 5.0
DEFAULT_ASSISTANT_ID = "default_assistant_profile"
short_term_capacity = 100
mid_term_capacity = 50
long_term_knowledge_capacity = 1000
retrieval_queue_capacity = 50
mid_term_heat_threshold = 5.0


class Memoryos:
    def __init__(
        self,
        user_id: str,
        data_storage_path: str,
        embedder,  # required argument
        llm_api_key: str = None,
        llm_base_url: str = None,
        assistant_id: str = DEFAULT_ASSISTANT_ID,
        llm_model: str = "gpt-4",
    ):
        self.user_id = user_id
        self.data_storage_path = data_storage_path
        self.embedder = embedder  # 🔑 PLUGGABLE!
        self.assistant_id = assistant_id
        self.llm_model = llm_model

        # Load codemap once during initialization
        self.codemap = load_codemap()
        print(f"Memoryos: Loaded codemap with {len(self.codemap)} top-level entries.")
        self.client = OpenAIClient(api_key=llm_api_key, base_url=llm_base_url)

        # Define file paths for user-specific data
        self.user_data_dir = os.path.join(self.data_storage_path, "users", self.user_id)
        user_short_term_path = os.path.join(self.user_data_dir, "short_term.json")
        user_mid_term_path = os.path.join(self.user_data_dir, "mid_term.json")
        user_long_term_path = os.path.join(
            self.user_data_dir, "long_term_user.json"
        )  # User profile and their knowledge

        # Define file paths for assistant-specific data (knowledge)
        self.assistant_data_dir = os.path.join(
            self.data_storage_path, "assistants", self.assistant_id
        )
        assistant_long_term_path = os.path.join(
            self.assistant_data_dir, "long_term_assistant.json"
        )

        # Ensure directories exist
        ensure_directory_exists(
            user_short_term_path
        )  # ensure_directory_exists operates on the file path, creating parent dirs
        ensure_directory_exists(user_mid_term_path)
        ensure_directory_exists(user_long_term_path)
        ensure_directory_exists(assistant_long_term_path)

        # Initialize Memory Modules for User
        self.short_term_memory = ShortTermMemory(
            file_path=user_short_term_path, max_capacity=short_term_capacity
        )
        self.mid_term_memory = MidTermMemory(
            file_path=user_mid_term_path,
            client=self.client,
            max_capacity=mid_term_capacity,
        )
        self.user_long_term_memory = LongTermMemory(
            file_path=user_long_term_path,
            knowledge_capacity=long_term_knowledge_capacity,
        )

        # Initialize Memory Module for Assistant Knowledge
        self.assistant_long_term_memory = LongTermMemory(
            file_path=assistant_long_term_path,
            knowledge_capacity=long_term_knowledge_capacity,
        )

        # Initialize Orchestration Modules
        self.updater = Updater(
            short_term_memory=self.short_term_memory,
            mid_term_memory=self.mid_term_memory,
            long_term_memory=self.user_long_term_memory,
            client=self.client,
            llm_model=self.llm_model,
            codemap=self.codemap,
        )
        self.retriever = Retriever()

        self.mid_term_heat_threshold = mid_term_heat_threshold

        # Load codemap once during initialization
        self.codemap = load_codemap()
        print(f"Memoryos: Loaded codemap with {len(self.codemap)} top-level entries.")

    def _trigger_profile_and_knowledge_update_if_needed(self):
        """
        Checks mid-term memory for hot segments and triggers profile/knowledge update if threshold is met.
        Adapted from main_memoybank.py's update_user_profile_from_top_segment.
        """
        if not self.mid_term_memory.heap:
            return

        # Peek at the top of the heap (hottest segment)
        # MidTermMemory heap stores (-H_segment, sid)
        neg_heat, sid = self.mid_term_memory.heap[0]
        current_heat = -neg_heat

        if current_heat >= self.mid_term_heat_threshold:
            session = self.mid_term_memory.sessions.get(sid)
            if not session:
                self.mid_term_memory.rebuild_heap()  # Clean up if session is gone
                return

            # Get unanalyzed pages from this hot session
            # A page is a dict: {"user_input": ..., "agent_response": ..., "timestamp": ..., "analyzed": False, ...}
            unanalyzed_pages = [
                p for p in session.get("details", []) if not p.get("analyzed", False)
            ]

            if unanalyzed_pages:
                print(
                    f"Memoryos: Mid-term session {sid} heat ({current_heat:.2f}) exceeded threshold. Analyzing {len(unanalyzed_pages)} pages for profile/knowledge update."
                )

                # Perform user profile analysis and knowledge extraction separately
                # First call: User profile analysis
                new_user_profile_text = gpt_user_profile_analysis(
                    unanalyzed_pages, self.client, model=self.llm_model
                )

                # Second call: Knowledge extraction (user private data and assistant knowledge)
                knowledge_result = gpt_knowledge_extraction(
                    unanalyzed_pages, self.client, model=self.llm_model
                )
                new_user_private_knowledge = knowledge_result.get("private")
                new_assistant_knowledge = knowledge_result.get("assistant_knowledge")

                # Update User Profile in user's LTM
                if new_user_profile_text and new_user_profile_text.lower() != "none":
                    old_profile = self.user_long_term_memory.get_raw_user_profile(
                        self.user_id
                    )
                    if old_profile and old_profile.lower() != "none":
                        updated_profile = gpt_update_profile(
                            old_profile,
                            new_user_profile_text,
                            self.client,
                            model=self.llm_model,
                        )
                    else:
                        updated_profile = new_user_profile_text
                    self.user_long_term_memory.update_user_profile(
                        self.user_id, updated_profile, merge=False
                    )  # Don't merge, replace with latest

                # Add User Private Knowledge to user's LTM
                if (
                    new_user_private_knowledge
                    and new_user_private_knowledge.lower() != "none"
                ):
                    for line in new_user_private_knowledge.split("\n"):
                        if line.strip() and line.strip().lower() not in [
                            "none",
                            "- none",
                            "- none.",
                        ]:
                            self.user_long_term_memory.add_user_knowledge(line.strip())

                # Add Assistant Knowledge to assistant's LTM
                if (
                    new_assistant_knowledge
                    and new_assistant_knowledge.lower() != "none"
                ):
                    for line in new_assistant_knowledge.split("\n"):
                        if line.strip() and line.strip().lower() not in [
                            "none",
                            "- none",
                            "- none.",
                        ]:
                            self.assistant_long_term_memory.add_assistant_knowledge(
                                line.strip()
                            )  # Save to dedicated assistant LTM

                # Mark pages as analyzed and reset session heat contributors
                for p in session["details"]:
                    p["analyzed"] = (
                        True  # Mark all pages in session, or just unanalyzed_pages?
                    )
                    # Original code marked all pages in session

                session["N_visit"] = 0  # Reset visits after analysis
                session["L_interaction"] = 0  # Reset interaction length contribution
                # session["R_recency"] = 1.0 # Recency will re-calculate naturally
                session["H_segment"] = compute_segment_heat(
                    session
                )  # Recompute heat with reset factors
                session["last_visit_time"] = get_timestamp()  # Update last visit time

                self.mid_term_memory.rebuild_heap()  # Heap needs rebuild due to H_segment change
                self.mid_term_memory.save()
                print(
                    f"Memoryos: Profile/Knowledge update for session {sid} complete. Heat reset."
                )
            else:
                print(
                    f"Memoryos: Hot session {sid} has no unanalyzed pages. Skipping profile update."
                )
        else:
            # print(f"Memoryos: Top session {sid} heat ({current_heat:.2f}) below threshold. No profile update.")
            pass  # No action if below threshold

    def add_memory(
        self,
        user_input: str,
        agent_response: str,
        timestamp: str = None,
        meta_data: dict = None,
    ):
        """
        Adds a new QA pair (memory) to the system, supporting project and thread metadata.
        meta_data can include project_id, thread_id, and other conversation metadata.
        """
        if not timestamp:
            timestamp = get_timestamp()
        # Compose the memory object with project/thread info if provided
        qa_pair = {
            "user_input": user_input,
            "agent_response": agent_response,
            "timestamp": timestamp,
        }
        # Attach meta_data fields (including project/thread) to the memory object
        if meta_data:
            for key, value in meta_data.items():
                # Avoid overwriting main fields
                if key not in qa_pair:
                    qa_pair[key] = value
        self.short_term_memory.add_qa_pair(qa_pair)
        print(f"Memoryos: Added QA to short-term. User: {user_input[:30]}...")

        if self.short_term_memory.is_full():
            print("Memoryos: Short-term memory full. Processing to mid-term.")
            self.updater.process_short_term_to_mid_term()

        # --- Auto-branching logic based on conversation token count ---
        if meta_data and "thread_id" in meta_data:
            thread_id = meta_data["thread_id"]
            # Find all conversations in this thread
            all_conversations = self.user_long_term_memory.get_conversations_for_thread(
                thread_id
            )
            for convo in all_conversations:
                messages = convo.get("messages", [])
                token_count = 0
                for msg in messages:
                    token_count += len(self.client.tokenize(msg.get("user_input", "")))
                    token_count += len(
                        self.client.tokenize(msg.get("agent_response", ""))
                    )
                if token_count > 80000:  # 100k total context - 20k reserved
                    print(
                        f"Memoryos: Conversation {convo['conversation_id']} exceeded 80,000 tokens. Auto-branching..."
                    )
                    self.summarize_and_branch_conversation(convo["conversation_id"])

        # After any memory addition that might impact mid-term, check for profile updates
        self._trigger_profile_and_knowledge_update_if_needed()

        # Update rolling summary for the thread, if applicable
        meta_data_for_memory = meta_data if meta_data else {}
        if "thread_id" in meta_data_for_memory:
            thread_id = meta_data_for_memory["thread_id"]
            self.update_rolling_summary(thread_id)

    def update_rolling_summary(self, thread_id: str):
        """
        Generates or updates a rolling summary for the given thread by summarizing recent messages.
        This summary is overwritten each time it's updated (rolling state, not permanent memory).
        """
        print(f"Memoryos: Updating rolling summary for thread '{thread_id}'")

        # Retrieve all conversations in the thread
        conversations = self.user_long_term_memory.get_conversations_for_thread(
            thread_id
        )
        recent_messages = []
        for convo in conversations:
            recent_messages.extend(convo.get("messages", []))

        if not recent_messages:
            print("Memoryos: No messages found for thread. Skipping rolling summary.")
            return

        # Cap the number of messages to avoid overload
        recent_messages = recent_messages[-40:]  # Only consider the last 40 exchanges

        convo_text = "\n".join(
            [
                f"User: {m['user_input']}\nAssistant: {m['agent_response']}"
                for m in recent_messages
            ]
        )

        system_prompt = (
            "You are a rolling summarizer. Provide a short, updated summary of the recent conversation. "
            "Summarize key points and overall direction. Keep it concise and overwrite previous versions."
        )

        summary = self.client.chat_completion(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": convo_text},
            ],
            temperature=0.4,
            max_tokens=300,
        )

        self.user_long_term_memory.attach_rolling_summary_to_thread(
            thread_id, summary.strip()
        )

    def get_response(
        self,
        query: str,
        relationship_with_user="friend",
        style_hint="",
        user_conversation_meta_data: dict = None,
    ) -> str:
        """
        Generates a response to the user's query, incorporating memory and context.
        Attaches project and thread metadata to the conversation object if provided.
        """
        print(f"Memoryos: Generating response for query: '{query[:50]}...'")

        # 1. Retrieve context
        retrieval_results = self.retriever.retrieve_context(
            user_query=query,
            user_id=self.user_id,
            # Using default thresholds from Retriever class for now
        )
        retrieved_pages = retrieval_results["retrieved_pages"]
        retrieved_user_knowledge = retrieval_results["retrieved_user_knowledge"]
        retrieved_assistant_knowledge = retrieval_results[
            "retrieved_assistant_knowledge"
        ]

        # 2. Get short-term history
        short_term_history = self.short_term_memory.get_all()
        history_text = "\n".join(
            [
                f"User: {qa.get('user_input', '')}\nAssistant: {qa.get('agent_response', '')} (Time: {qa.get('timestamp', '')})"
                for qa in short_term_history
            ]
        )

        # 3. Format retrieved mid-term pages (retrieval_queue equivalent)
        retrieval_text = "\n".join(
            [
                f"【Historical Memory】\nUser: {page.get('user_input', '')}\nAssistant: {page.get('agent_response', '')}\nTime: {page.get('timestamp', '')}\nConversation chain overview: {page.get('meta_info','N/A')}"
                for page in retrieved_pages
            ]
        )

        # 4. Get user profile
        user_profile_text = self.user_long_term_memory.get_raw_user_profile(
            self.user_id
        )
        if not user_profile_text or user_profile_text.lower() == "none":
            user_profile_text = "No detailed profile available yet."

        # 5. Format retrieved user knowledge for background
        user_knowledge_background = ""
        if retrieved_user_knowledge:
            user_knowledge_background = "\n【Relevant User Knowledge Entries】\n"
            for kn_entry in retrieved_user_knowledge:
                user_knowledge_background += (
                    f"- {kn_entry['knowledge']} (Recorded: {kn_entry['timestamp']})\n"
                )

        background_context = (
            f"【User Profile】\n{user_profile_text}\n{user_knowledge_background}"
        )

        # 6. Format retrieved Assistant Knowledge (from assistant's LTM)
        assistant_knowledge_text_for_prompt = "【Assistant Knowledge Base】\n"
        if retrieved_assistant_knowledge:
            for ak_entry in retrieved_assistant_knowledge:
                assistant_knowledge_text_for_prompt += (
                    f"- {ak_entry['knowledge']} (Recorded: {ak_entry['timestamp']})\n"
                )
        else:
            assistant_knowledge_text_for_prompt += (
                "- No relevant assistant knowledge found for this query.\n"
            )

        # 7. Format user_conversation_meta_data (if provided), and extract project/thread info
        meta_data_text_for_prompt = "【Current Conversation Metadata】\n"
        meta_data_for_memory = {}
        if user_conversation_meta_data:
            try:
                meta_data_text_for_prompt += json.dumps(
                    user_conversation_meta_data, ensure_ascii=False, indent=2
                )
            except TypeError:
                meta_data_text_for_prompt += str(user_conversation_meta_data)
            # Extract project_id, thread_id, etc. for tagging the memory object
            for key in ["project_id", "thread_id", "project_name", "thread_title"]:
                if key in user_conversation_meta_data:
                    meta_data_for_memory[key] = user_conversation_meta_data[key]
            # Optionally, store the whole metadata for future use
            meta_data_for_memory["conversation_meta"] = user_conversation_meta_data
        else:
            meta_data_text_for_prompt += "None provided for this turn."

        # 8. Construct Prompts
        system_prompt_text = prompts.GENERATE_SYSTEM_RESPONSE_SYSTEM_PROMPT.format(
            relationship=relationship_with_user,
            assistant_knowledge_text=assistant_knowledge_text_for_prompt,
            meta_data_text=meta_data_text_for_prompt,
        )

        user_prompt_text = prompts.GENERATE_SYSTEM_RESPONSE_USER_PROMPT.format(
            history_text=history_text,
            retrieval_text=retrieval_text,
            background=background_context,
            relationship=relationship_with_user,
            query=query,
        )

        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt_text},
        ]

        # 9. Call LLM for response
        print("Memoryos: Calling LLM for final response generation...")
        response_content = self.client.chat_completion(
            model=self.llm_model, messages=messages, temperature=0.7, max_tokens=1500
        )

        # Codemap fallback if LLM response is vague or empty
        fallback_triggers = [
            "i don't know",
            "i'm not sure",
            "no idea",
            "unknown",
            "not sure",
        ]
        if any(trigger in response_content.lower() for trigger in fallback_triggers):
            print(
                "Memoryos: Primary LLM response was vague. Attempting codemap introspection as fallback."
            )
            codemap_fallback = self.query_codemap(query)
            response_content += f"\n\n[Codemap Insight]\n{codemap_fallback}"

        # 10. Add this interaction to memory, tagging with project/thread metadata if available
        self.add_memory(
            user_input=query,
            agent_response=response_content,
            timestamp=get_timestamp(),
            meta_data=meta_data_for_memory if meta_data_for_memory else None,
        )

        return response_content

    def save(self, title: str, content: str, tags: list = None, **kwargs):
        """A convenience method to save a memory entry, aliasing add_memory."""
        meta_data = {"tags": tags or []}
        self.add_memory(user_input=title, agent_response=content, meta_data=meta_data)

    def query(self, query: str, limit: int = 10, **kwargs):
        """
        A convenience method to query memories, aliasing the retriever.
        kwargs accepts unused params like 'timeframe' for agent compatibility.
        """
        results = self.retriever.retrieve_context(user_query=query, limit=limit)
        # Return a list of pages for consistency with what agents might expect
        return results.get("retrieved_pages", [])

    def fetch_memory(self, query: str, limit: int = 10, **kwargs):
        """An alias for the query method for agent compatibility."""
        return self.query(query, limit=limit, **kwargs)

    # --- Helper/Maintenance methods (optional additions) ---
    def get_user_profile_summary(self) -> str:
        return self.user_long_term_memory.get_raw_user_profile(self.user_id)

    def get_assistant_knowledge_summary(self) -> list:
        return self.assistant_long_term_memory.get_assistant_knowledge()

    def force_mid_term_analysis(self):
        """Forces analysis of all unanalyzed pages in the hottest mid-term segment if heat is above 0.
        Useful for testing or manual triggering.
        """
        original_threshold = self.mid_term_heat_threshold
        self.mid_term_heat_threshold = 0.0  # Temporarily lower threshold
        print("Memoryos: Force-triggering mid-term analysis...")
        self._trigger_profile_and_knowledge_update_if_needed()
        self.mid_term_heat_threshold = original_threshold  # Restore original threshold

    def __repr__(self):
        return f"<Memoryos user_id='{self.user_id}' assistant_id='{self.assistant_id}' data_path='{self.data_storage_path}'>"

    def query_codemap(self, query: str) -> str:
        """
        Uses LLM to answer natural language questions about the codebase using codemap context.
        """
        if not self.codemap:
            return "Codemap is not loaded or is empty."

        codemap_context = "\n".join(
            [f"- {filename}: {desc}" for filename, desc in self.codemap.items()]
        )

        system_prompt = (
            "You are an expert code navigator. Given a user's question and a summary of the project's code files, "
            "return a helpful and specific answer. Mention relevant files and what they do. Be brief but informative."
        )

        user_prompt = f"QUESTION: {query}\n\nCODEMAP:\n{codemap_context}"

        response = self.client.chat_completion(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=800,
        )

        return response.strip()

    def get_codemap_summary(self) -> dict:
        """
        Returns a brief summary of codemap keys for inspection or debugging.
        """
        return list(self.codemap.keys())

    def cli_codemap_query(self):
        """
        Exposes a CLI interface for querying the codemap.
        """
        import argparse

        parser = argparse.ArgumentParser(
            description="Ask a question about the project's codebase using the codemap."
        )
        parser.add_argument(
            "question",
            type=str,
            help="Your natural language question about the codebase.",
        )

        args = parser.parse_args()
        result = self.query_codemap(args.question)
        print("\n--- CODEMAP ANSWER ---\n")
        print(result)


import os

# --- CLI command for codemap:query ---
import click


@click.group()
def cli():
    pass


@cli.command("codemap:query")
@click.argument("question", type=str)
def codemap_query(question):
    """Ask a question about the codebase using codemap.json."""
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    # Setup dummy user credentials and data path
    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")  # Replace as needed
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    answer = memory.query_codemap(question)
    print("\n--- CODEMAP ANSWER ---\n")
    print(answer)


# --- CLI command for memory:show-user-profile ---
@cli.command("memory:show-user-profile")
def show_user_profile():
    """Display the current user's profile from long-term memory."""
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    profile = memory.get_user_profile_summary()
    print("\n--- USER PROFILE ---\n")
    print(profile)


# --- CLI command for memory:show-assistant-knowledge ---
@cli.command("memory:show-assistant-knowledge")
def show_assistant_knowledge():
    """Display current assistant knowledge from long-term memory."""
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    knowledge = memory.get_assistant_knowledge_summary()
    print("\n--- ASSISTANT KNOWLEDGE ---\n")
    for entry in knowledge:
        print(f"- {entry['knowledge']} (Recorded: {entry['timestamp']})")


# --- CLI command for memory:show-projects ---
@cli.command("memory:show-projects")
def show_projects():
    """Display all known projects from long-term memory."""
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    projects = memory.get_all_projects_summary()
    print("\n--- PROJECTS ---\n")
    for project in projects:
        print(f"- {project.get('project_id')} | {project.get('project_name')}")


# --- CLI command for memory:show-threads ---
@cli.command("memory:show-threads")
@click.argument("project_id", type=str)
def show_threads_by_project(project_id):
    """Display threads associated with a specific project."""
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    threads = memory.get_threads_by_project(project_id)
    print(f"\n--- THREADS in PROJECT {project_id} ---\n")
    for thread in threads:
        print(f"- {thread.get('thread_id')} | {thread.get('thread_title')}")


# --- CLI command for memory:show-conversations ---
@cli.command("memory:show-conversations")
@click.argument("thread_id", type=str)
def show_conversations_by_thread(thread_id):
    """Display conversations associated with a specific thread."""
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    conversations = memory.get_conversations_by_thread(thread_id)
    print(f"\n--- CONVERSATIONS in THREAD {thread_id} ---\n")
    for convo in conversations:
        print(f"- {convo.get('conversation_id')} | {convo.get('title', 'Untitled')}")


# --- CLI command for memory:get-conversation ---
@cli.command("memory:get-conversation")
@click.argument("conversation_id", type=str)
def get_conversation_by_id(conversation_id):
    """Retrieve a specific conversation by its ID."""
    import json
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    convo = memory.get_conversation_by_id(conversation_id)
    print(f"\n--- CONVERSATION {conversation_id} ---\n")
    print(json.dumps(convo, indent=2))

    def summarize_and_branch_conversation(self, conversation_id: str):
        """
        Summarizes the specified conversation and creates a child conversation linked to it.
        Stores summary inside the original conversation object.
        """
        print(f"Memoryos: Summarizing and branching conversation '{conversation_id}'")

        # Retrieve the full conversation
        conversation = self.user_long_term_memory.get_conversation(conversation_id)
        if not conversation:
            print(f"Memoryos: Conversation '{conversation_id}' not found.")
            return None

        # Compose content for summarization
        messages = conversation.get("messages", [])
        convo_text = "\n".join(
            [
                f"User: {m['user_input']}\nAssistant: {m['agent_response']}"
                for m in messages
            ]
        )

        system_prompt = (
            "You are an archival summarizer. Create a succinct summary of the following conversation. "
            "Highlight key decisions, emotional tone, turning points, and intended next steps. Output 1 short paragraph."
        )

        summary_result = self.client.chat_completion(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": convo_text},
            ],
            temperature=0.5,
            max_tokens=400,
        )

        # Generate new child conversation ID
        new_convo_id = generate_id()
        child_convo = {
            "conversation_id": new_convo_id,
            "title": f"Child of {conversation_id}",
            "messages": [],
            "parent_id": conversation_id,
            "created_at": get_timestamp(),
        }

        # Store child conversation and update parent with summary
        self.user_long_term_memory.store_conversation(child_convo)

        summary_blob = {
            "summary_text": summary_result,
            "created_at": get_timestamp(),
            "child_conversation_id": new_convo_id,
        }

        self.user_long_term_memory.attach_summary_to_conversation(
            conversation_id, summary_blob
        )

        print(
            f"Memoryos: Summary complete. Child conversation '{new_convo_id}' created."
        )
        return summary_blob


# --- CLI command for memory:summarize-and-branch ---
@cli.command("memory:summarize-and-branch")
@click.argument("conversation_id", type=str)
def summarize_and_branch(conversation_id):
    """Summarize a conversation and create a child branch."""
    import os
    from memoryos.memoryos import Memoryos
    from memoryos.embedders.local_embedder import LocalEmbedder

    user_id = "default"
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")
    data_storage_path = "./data"
    embedder = LocalEmbedder()
    memory = Memoryos(
        user_id=user_id,
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        embedder=embedder,
        llm_model=llm_model,
    )
    result = memory.summarize_and_branch_conversation(conversation_id)
    print("\n--- SUMMARY RESULT ---\n")
    print(result if result else "No summary was generated.")
