# guardian/core/chat_db.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class ChatDB(ABC):
    """Common interface that both SQLite and Postgres adapters must implement."""

    # ---- chat threads (chat_threads) -------------------------------------
    @abstractmethod
    def create_chat_thread(
        self,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    def ensure_chat_thread(
        self,
        thread_id: int,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_recent_thread(self, user_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_chat_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def list_chat_threads(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def update_thread(
        self,
        thread_id: int,
        *,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> bool:
        ...

    @abstractmethod
    def delete_thread(self, thread_id: int) -> None:
        ...

    @abstractmethod
    def count_chat_threads(self) -> int:
        ...

    @abstractmethod
    def count_all_messages(self) -> int:
        ...

    # ---- chat messages ----------------------------------------------------
    @abstractmethod
    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        created_at: Optional[str] = None,
    ) -> int:
        ...

    @abstractmethod
    def list_messages(
        self,
        thread_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def count_messages(self, thread_id: int) -> int:
        ...

    @abstractmethod
    def delete_message(self, thread_id: int, message_id: int) -> None:
        ...

    # ---- legacy thread lineage (threads table) ---------------------------
    @abstractmethod
    def create_thread(
        self,
        parent_thread_id: Optional[int],
        session_id: str,
        summary: str,
        user_id: str,
        project_id: Optional[str] = None,
    ) -> int:
        ...

    @abstractmethod
    def get_thread(self, thread_id: int) -> Optional[Tuple[Any, ...]]:
        ...

    @abstractmethod
    def list_threads(
        self,
        *,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_child_threads(self, parent_thread_id: int) -> List[Tuple[Any, ...]]:
        ...

    @abstractmethod
    def get_thread_summary(self, thread_id: int) -> Optional[str]:
        ...

    # ---- chat history -----------------------------------------------------
    @abstractmethod
    def get_chat_history(
        self,
        *,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        ...

    # ---- memory -----------------------------------------------------------
    @abstractmethod
    def add_memory(
        self,
        user_id: str,
        silo: str,
        content: str,
        *,
        tags: str = "",
        pinned: bool = False,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> int:
        ...

    @abstractmethod
    def list_memories(
        self,
        silo: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def count_memories(self, silo: str) -> int:
        ...

    @abstractmethod
    def update_memory(
        self,
        entry_id: int,
        *,
        content: Optional[str] = None,
        tags: Optional[str] = None,
        pinned: Optional[bool] = None,
    ) -> None:
        ...

    @abstractmethod
    def delete_memory(self, entry_id: int) -> None:
        ...

    @abstractmethod
    def insert_memory_event(
        self,
        *,
        content: str,
        tag: Optional[str],
        agent: str,
        type_: str,
        parent_id: Optional[int] = None,
    ) -> int:
        ...

    @abstractmethod
    def prune_midterm(self, older_than_iso: str) -> int:
        ...

    @abstractmethod
    def search_memory(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def history_entries(
        self,
        *,
        limit: int = 50,
        tag: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def write_audit_log(
        self,
        event: str,
        entity: str,
        entity_id: str,
        user_id: str,
    ) -> None:
        ...

    # ---- projects ---------------------------------------------------------
    @abstractmethod
    def create_project(self, name: str, description: str = "") -> int:
        ...

    @abstractmethod
    def ensure_project(self, name: str, description: str = "") -> int:
        ...

    @abstractmethod
    def list_projects(self) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def delete_project(self, project_id: int) -> bool:
        ...

    @abstractmethod
    def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        ...

    @abstractmethod
    def eject_threads_from_project(self, project_id: int) -> None:
        ...

    # ---- agent profiles ---------------------------------------------------
    @abstractmethod
    def get_agent_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def upsert_agent_profile(self, agent_id: str, **updates: Any) -> None:
        ...

    @abstractmethod
    def check_summarization_allowed(
        self,
        agent_id: str,
        requested_by: str,
    ) -> Tuple[bool, Optional[str]]:
        ...

    # ---- diagnostics ------------------------------------------------------
    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        ...
