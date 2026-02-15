"""Abstract chat database interface shared by SQL backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


## ChatDB Abstract Base Class
class ChatDB(ABC):
    """Common interface that both SQLite and Postgres adapters must implement."""

    ## ---- chat threads (chat_threads) -------------------------------------
    @abstractmethod
    def create_chat_thread(
        self,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a new chat thread.

        Args:
            user_id (str): The ID of the user creating the thread.
            title (str): The title of the chat thread.
            summary (str, optional): A brief summary of the thread. Defaults to "".
            project_id (Optional[int], optional): The ID of the project. Defaults to None.
            parent_id (Optional[int], optional): Optional parent thread identifier. Defaults to None.

        Returns:
            Dict[str, Any]: The newly created chat thread.
        """
        ...

    @abstractmethod
    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        """Ensure a chat thread exists, creating it if necessary.

        Args:
            thread_id (int): The ID of the thread.
            user_id (str): The ID of the user.
            title (str): The title of the chat thread.
            summary (str, optional): A brief summary of the thread. Defaults to "".
            project_id (Optional[int], optional): The ID of the project. Defaults to None.
            parent_id (Optional[int], optional): Optional parent thread identifier. Defaults to None.

        Returns:
            Dict[str, Any]: The chat thread.
        """
        ...

    @abstractmethod
    def get_recent_thread(self, user_id: str) -> dict[str, Any] | None:
        """Get the most recent chat thread for a user.

        Args:
            user_id (str): The ID of the user.

        Returns:
            Optional[Dict[str, Any]]: The most recent chat thread, or None if none exist.
        """
        ...

    @abstractmethod
    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        """Get a chat thread by ID.

        Args:
            thread_id (int): The ID of the thread.

        Returns:
            Optional[Dict[str, Any]]: The chat thread, or None if not found.
        """
        ...

    @abstractmethod
    def list_chat_threads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        user_id: str | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """List chat threads.

        Args:
            limit (int, optional): The maximum number of threads to return. Defaults to 50.
            offset (int, optional): The offset from which to start. Defaults to 0.
            user_id (Optional[str], optional): The ID of the user. Defaults to None.
            project_id (Optional[int], optional): The ID of the project. Defaults to None.

        Returns:
            List[Dict[str, Any]]: A list of chat threads.
        """
        ...

    @abstractmethod
    def update_thread(
        self,
        thread_id: int,
        *,
        title: str | None = None,
        summary: str | None = None,
        project_id: int | None = None,
        project_id_set: bool = False,
        active_profile_id: str | None = None,
        active_profile_id_set: bool = False,
    ) -> bool:
        """Update a chat thread.

        Args:
            thread_id (int): The ID of the thread.
            title (Optional[str], optional): The new title. Defaults to None.
            summary (Optional[str], optional): The new summary. Defaults to None.
            project_id (Optional[int], optional): The new project ID. Defaults to None.
            project_id_set (bool, optional): True to set project_id even when None.
            active_profile_id (Optional[str], optional): The active system profile id.
            active_profile_id_set (bool, optional): True to set active_profile_id even when None.

        Returns:
            None
        """
        ...

    @abstractmethod
    def set_thread_active_profile_id(
        self, thread_id: int, profile_id: str | None
    ) -> bool:
        """Set active profile id for a thread.

        Args:
            thread_id (int): The target thread.
            profile_id (Optional[str]): Profile id to set, or None to clear.

        Returns:
            bool: True when a row was updated.
        """
        ...

    @abstractmethod
    def update_thread_metadata(
        self, thread_id: int, metadata: dict[str, Any]
    ) -> bool:
        """Replace thread metadata payload.

        Args:
            thread_id (int): The target thread.
            metadata (dict[str, Any]): New metadata payload.

        Returns:
            bool: True when a row was updated.
        """
        ...

    @abstractmethod
    def set_thread_profile_overrides(
        self, thread_id: int, overrides: dict[str, Any]
    ) -> bool:
        """Upsert profile overrides in thread metadata.

        Args:
            thread_id (int): The target thread.
            overrides (dict[str, Any]): Mapping profile_id -> payload.

        Returns:
            bool: True when a row was updated.
        """
        ...

    @abstractmethod
    def delete_thread(self, thread_id: int) -> None:
        """Delete a chat thread.

        Args:
            thread_id (int): The ID of the thread.

        Returns:
            None
        """
        ...

    @abstractmethod
    def count_chat_threads(self) -> int:
        """Count the total number of chat threads.

        Returns:
            int: The total number of chat threads.
        """
        ...

    @abstractmethod
    def count_all_messages(self) -> int:
        """Count all messages across all threads.

        Returns:
            int: The total number of messages.
        """
        ...

    @abstractmethod
    def archive_thread(self, thread_id: int) -> dict[str, Any] | None:
        """Set ``archived_at`` for the given thread and return the updated record."""
        ...

    ## ---- chat messages ----------------------------------------------------
    @abstractmethod
    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        """Create a new message in a thread.

        Args:
            thread_id (int): The ID of the thread.
            role (str): The role of the message sender.
            content (str): The content of the message.
            created_at (Optional[str], optional): The timestamp. Defaults to None.

        Returns:
            int: The ID of the newly created message.
        """
        ...

    @abstractmethod
    def list_messages(
        self,
        thread_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        exclude_kinds: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List messages in a thread.

        Args:
            thread_id (int): The ID of the thread.
            limit (int, optional): The maximum number of messages. Defaults to 50.
            offset (int, optional): The offset. Defaults to 0.
            exclude_kinds (list[str] | None, optional): Message kinds to omit.

        Returns:
            List[Dict[str, Any]]: A list of messages in the thread.
        """
        ...

    @abstractmethod
    def count_messages(self, thread_id: int) -> int:
        """Count messages in a thread.

        Args:
            thread_id (int): The ID of the thread.

        Returns:
            int: The number of messages in the thread.
        """
        ...

    @abstractmethod
    def delete_message(self, thread_id: int, message_id: int) -> None:
        """Delete a message from a thread.

        Args:
            thread_id (int): The ID of the thread.
            message_id (int): The ID of the message.

        Returns:
            None
        """
        ...

    ## ---- legacy thread lineage (threads table) ---------------------------
    @abstractmethod
    def create_thread(
        self,
        parent_thread_id: int | None,
        session_id: str,
        summary: str,
        user_id: str,
        project_id: str | None = None,
    ) -> int:
        """Create a new thread.

        Args:
            parent_thread_id (Optional[int], optional): The ID of the parent thread. Defaults to None.
            session_id (str): The session ID.
            summary (str): A brief summary of the thread.
            user_id (str): The ID of the user.
            project_id (Optional[str], optional): The ID of the project. Defaults to None.

        Returns:
            int: The ID of the newly created thread.
        """
        ...

    @abstractmethod
    def get_thread(self, thread_id: int) -> tuple[Any, ...] | None:
        """Get a thread.

        Args:
            thread_id (int): The ID of the thread.

        Returns:
            Optional[Tuple[Any, ...]]: The thread data.
        """
        ...

    @abstractmethod
    def list_threads(
        self,
        *,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List threads.

        Args:
            user_id (Optional[str], optional): The ID of the user. Defaults to None.
            project_id (Optional[str], optional): The ID of the project. Defaults to None.

        Returns:
            List[Dict[str, Any]]: A list of threads.
        """
        ...

    @abstractmethod
    def get_child_threads(self, parent_thread_id: int) -> list[tuple[Any, ...]]:
        """Get child threads of a parent thread.

        Args:
            parent_thread_id (int): The ID of the parent thread.

        Returns:
            List[Tuple[Any, ...]]: A list of child threads.
        """
        ...

    @abstractmethod
    def get_thread_summary(self, thread_id: int) -> str | None:
        """Get the summary of a thread.

        Args:
            thread_id (int): The ID of the thread.

        Returns:
            Optional[str]: The summary of the thread.
        """
        ...

    ## ---- chat history -----------------------------------------------------
    @abstractmethod
    def get_chat_history(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get chat history.

        Args:
            session_id (Optional[str], optional): The session ID. Defaults to None.
            user_id (Optional[str], optional): The ID of the user. Defaults to None.
            limit (int, optional): The maximum number of history entries. Defaults to 50.

        Returns:
            List[Dict[str, Any]]: A list of chat history entries.
        """
        ...

    ## ---- memory -----------------------------------------------------------
    @abstractmethod
    def add_memory(
        self,
        user_id: str,
        silo: str,
        content: str,
        *,
        tags: str = "",
        pinned: bool = False,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> int:
        """Add a memory entry.

        Args:
            user_id (str): The ID of the user.
            silo (str): The silo.
            content (str): The content of the memory entry.
            tags (str, optional): Tags for the memory entry. Defaults to "".
            pinned (bool, optional): Whether the entry is pinned. Defaults to False.
            created_at (Optional[str], optional): The creation timestamp. Defaults to None.
            updated_at (Optional[str], optional): The update timestamp. Defaults to None.

        Returns:
            int: The ID of the memory entry.
        """
        ...

    @abstractmethod
    def list_memories(
        self,
        silo: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List memory entries.

        Args:
            silo (str): The silo.
            limit (int, optional): The maximum number of entries. Defaults to 50.
            offset (int, optional): The offset. Defaults to 0.

        Returns:
            List[Dict[str, Any]]: A list of memory entries.
        """
        ...

    @abstractmethod
    def count_memories(self, silo: str) -> int:
        """Count memory entries in a silo.

        Args:
            silo (str): The silo.

        Returns:
            int: The number of memory entries.
        """
        ...

    @abstractmethod
    def update_memory(
        self,
        entry_id: int,
        *,
        content: str | None = None,
        tags: str | None = None,
        pinned: bool | None = None,
    ) -> None:
        """Update a memory entry.

        Args:
            entry_id (int): The ID of the memory entry.
            content (Optional[str], optional): The new content. Defaults to None.
            tags (Optional[str], optional): The new tags. Defaults to None.
            pinned (Optional[bool], optional): Whether the entry is pinned. Defaults to None.

        Returns:
            None
        """
        ...

    @abstractmethod
    def delete_memory(self, entry_id: int) -> None:
        """Delete a memory entry.

        Args:
            entry_id (int): The ID of the memory entry.

        Returns:
            None
        """
        ...

    @abstractmethod
    def insert_memory_event(
        self,
        *,
        content: str,
        tag: str | None,
        agent: str,
        type_: str,
        parent_id: int | None = None,
    ) -> int:
        """Insert a memory event.

        Args:
            content (str): The content of the event.
            tag (Optional[str], optional): The tag. Defaults to None.
            agent (str): The agent.
            type_ (str): The type of event.
            parent_id (Optional[int], optional): The ID of the parent event. Defaults to None.

        Returns:
            int: The ID of the event.
        """
        ...

    @abstractmethod
    def prune_midterm(self, older_than_iso: str) -> int:
        """Prune midterm memories.

        Args:
            older_than_iso (str): The timestamp.

        Returns:
            int: The number of pruned memories.
        """
        ...

    @abstractmethod
    def search_memory(
        self, query: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Search memories.

        Args:
            query (str): The search query.
            limit (int, optional): The maximum number of results. Defaults to 20.

        Returns:
            List[Dict[str, Any]]: A list of memory entries matching the query.
        """
        ...

    @abstractmethod
    def history_entries(
        self,
        *,
        limit: int = 50,
        tag: str | None = None,
        agent: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get history entries.

        Args:
            limit (int, optional): The maximum number of entries. Defaults to 50.
            tag (Optional[str], optional): The tag. Defaults to None.
            agent (Optional[str], optional): The agent. Defaults to None.

        Returns:
            List[Dict[str, Any]]: A list of history entries.
        """
        ...

    @abstractmethod
    def write_audit_log(
        self,
        event: str,
        entity: str,
        entity_id: str,
        user_id: str,
    ) -> None:
        """Write an audit log.

        Args:
            event (str): The event.
            entity (str): The entity.
            entity_id (str): The ID of the entity.
            user_id (str): The ID of the user.

        Returns:
            None
        """
        ...

    ## ---- projects ---------------------------------------------------------
    @abstractmethod
    def create_project(self, name: str, description: str = "") -> int:
        """Create a project.

        Args:
            name (str): The name of the project.
            description (str, optional): The description. Defaults to "".

        Returns:
            int: The ID of the project.
        """
        ...

    @abstractmethod
    def ensure_project(self, name: str, description: str = "") -> int:
        """Ensure a project exists.

        Args:
            name (str): The name of the project.
            description (str, optional): The description. Defaults to "".

        Returns:
            int: The ID of the project.
        """
        ...

    @abstractmethod
    def list_projects(self) -> list[dict[str, Any]]:
        """List projects.

        Returns:
            List[Dict[str, Any]]: A list of projects.
        """
        ...

    @abstractmethod
    def delete_project(self, project_id: int) -> bool:
        """Delete a project.

        Args:
            project_id (int): The ID of the project.

        Returns:
            bool: Whether the project was deleted.
        """
        ...

    @abstractmethod
    def update_project(
        self,
        project_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Update a project.

        Args:
            project_id (int): The ID of the project.
            name (Optional[str], optional): The new name. Defaults to None.
            description (Optional[str], optional): The new description. Defaults to None.

        Returns:
            None
        """
        ...

    @abstractmethod
    def eject_threads_from_project(self, project_id: int) -> None:
        """Eject threads from a project.

        Args:
            project_id (int): The ID of the project.

        Returns:
            None
        """
        ...

    ## ---- agent profiles ---------------------------------------------------
    @abstractmethod
    def get_agent_profile(self, agent_id: str) -> dict[str, Any] | None:
        """Get an agent profile.

        Args:
            agent_id (str): The ID of the agent.

        Returns:
            Optional[Dict[str, Any]]: The agent profile.
        """
        ...

    @abstractmethod
    def upsert_agent_profile(self, agent_id: str, **updates: Any) -> None:
        """Upsert an agent profile.

        Args:
            agent_id (str): The ID of the agent.
            **updates (Any): The updates.

        Returns:
            None
        """
        ...

    @abstractmethod
    def check_summarization_allowed(
        self,
        agent_id: str,
        requested_by: str,
    ) -> tuple[bool, str | None]:
        """Check if summarization is allowed.

        Args:
            agent_id (str): The ID of the agent.
            requested_by (str): The ID of the requester.

        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a boolean indicating
                whether summarization is allowed and an optional reason.
        """
        ...

    ## ---- connector sync jobs ---------------------------------------------
    @abstractmethod
    def ensure_sync_job_support(self) -> None:
        """Ensure the backing store for connector sync jobs exists."""
        ...

    @abstractmethod
    def create_sync_job(
        self,
        connector_id: str,
        *,
        status: str = "queued",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a new connector sync job and return the stored row."""
        ...

    @abstractmethod
    def update_sync_job(
        self,
        job_id: int,
        *,
        status: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        attempts: int | None = None,
        last_error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update fields on a sync job and return the latest representation."""
        ...

    @abstractmethod
    def list_recent_sync_jobs(
        self,
        *,
        connector_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return recent sync jobs, optionally filtered by connector."""
        ...

    ## ---- connector configs & runs ----------------------------------------
    @abstractmethod
    def create_connector_config(
        self,
        name: str,
        type_: str,
        config: dict[str, Any],
        schedule: str | None = None,
    ) -> dict[str, Any]:
        """Persist a connector configuration and return the stored row."""

    @abstractmethod
    def update_connector_config(
        self,
        name: str,
        *,
        config: dict[str, Any] | None = None,
        schedule: str | None = None,
    ) -> dict[str, Any]:
        """Update connector configuration and/or schedule."""

    @abstractmethod
    def list_connector_configs(
        self, type_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """List connector configurations, optionally filtered by type."""

    @abstractmethod
    def list_connector_configs_with_last_run(self) -> list[dict[str, Any]]:
        """Return connector configs annotated with their most recent run."""

    @abstractmethod
    def get_connector_config(self, name: str) -> dict[str, Any] | None:
        """Return a connector config identified by name (slug)."""

    @abstractmethod
    def create_connector_run(
        self,
        config_id: int,
        *,
        status: str,
        started_at: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Insert a connector run row."""

    @abstractmethod
    def complete_connector_run(
        self,
        run_id: int,
        *,
        status: str,
        finished_at: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Update a connector run with completion data."""

    @abstractmethod
    def get_last_connector_run(self, config_id: int) -> dict[str, Any] | None:
        """Return the most recent run for a connector."""

    @abstractmethod
    def upsert_raw_documents(
        self,
        config_id: int,
        docs: list[dict[str, Any]],
    ) -> None:
        """Insert or update raw documents for a connector."""

    @abstractmethod
    def list_raw_documents_for_config(
        self, config_id: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return raw documents stored for a connector configuration."""

    ## ---- events outbox ---------------------------------------------------
    @abstractmethod
    def ensure_event_outbox(self) -> None:
        """Ensure the durable events_outbox storage exists."""
        ...

    @abstractmethod
    def append_event(
        self, topic: str, payload: dict[str, Any], tenant_id: str = "default"
    ) -> None:
        """Persist a new event for later streaming."""
        ...

    @abstractmethod
    def list_events_after(
        self, last_id: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch events with IDs greater than ``last_id`` ordered ascending."""
        ...

    @abstractmethod
    def delete_events_through(
        self, last_id: int, tenant_id: str | None = None
    ) -> None:
        """Delete events with IDs less than or equal to ``last_id``."""
        ...

    ## ---- diagnostics ------------------------------------------------------
    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.

        Args:
            table_name (str): The name of the table.

        Returns:
            bool: Whether the table exists.
        """
        ...
