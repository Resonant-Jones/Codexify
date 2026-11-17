"""Native cancellable transport for the four ADR-112 reads only.

No route/admission registration, caller URL, ambient token, proxy or redirect.
The Command Bus owns policy, run persistence and audit. This adapter owns only
bounded provider translation and current authority checks around each request.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import time
from typing import Any
from uuid import UUID

import httpx

from guardian.command_bus.accepted_knowledge_read import (
    AcceptedKnowledgeRead,
    AcceptedKnowledgeReadUnavailable,
)
from guardian.connections.github import service as github
from guardian.core.chat_account_custody import ChatAccountAcceptancePending
from guardian.connections.notion import service as notion
from guardian.utils.log_safety import install_safe_logging
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    accepted_chat_deadline_for_task,
)

install_safe_logging()
MAX_RESPONSE_BYTES = 1_048_576
REQUEST_SECONDS = 15.0
RECHECK_SECONDS = 0.1
AUTHORITY_CHECK_SECONDS = 2.0
ORIGINS = {"github": github.API_BASE, "notion": notion.NOTION_API_BASE}


def _unavailable() -> None:
    raise AcceptedKnowledgeReadUnavailable(
        "accepted_knowledge_read_unavailable"
    ) from None


async def _authority(method, *, seconds: float = AUTHORITY_CHECK_SECONDS):
    """Do not block the event loop/watchdog on synchronous canonical reads.

    A timed-out read cannot start provider I/O. Its database transaction has
    local statement/lock timeouts in the private invocation DB wrapper.
    """
    if seconds <= 0:
        _unavailable()
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(method), min(seconds, AUTHORITY_CHECK_SECONDS)
        )
    except asyncio.CancelledError:
        raise
    except ChatAccountAcceptancePending:
        raise
    except Exception:
        _unavailable()


def _object_id(value: Any) -> str:
    if not isinstance(value, str):
        _unavailable()
    try:
        return str(UUID(value))
    except ValueError:
        _unavailable()


class _Reader:
    def __init__(self, fence, payload, command, client, work_limit):
        self.fence, self.payload, self.command, self.client = (
            fence,
            payload,
            command,
            client,
        )
        self.work_limit = work_limit
        self.provider = fence._grant.provider
        self.requests = 0
        self.did_request = False

    def policy(self):
        from guardian.command_bus.invoke import _accepted_policy_denial

        if _accepted_policy_denial(
            self.payload, self.command, self.fence._binding.account_id
        ):
            _unavailable()

    async def check(self):
        self.policy()
        await _authority(
            self.fence.revalidate, seconds=self.work_limit - time.monotonic()
        )

    async def request(self, method, path, *, params=None, body=None):
        # Only internally constructed paths reach here; no public generic URL API.
        self.requests += 1
        if self.requests > notion.MAX_BLOCK_REQUESTS + 1:
            _unavailable()
        limit = min(REQUEST_SECONDS, self.work_limit - time.monotonic())
        if limit <= 0:
            _unavailable()

        async def monitored():
            await self.check()
            credential = await _authority(
                self.fence.credential_for_io, seconds=self.work_limit - time.monotonic()
            )
            headers = {"Authorization": f"Bearer {credential.access_token}"}
            if self.provider == "github":
                headers.update(
                    {
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": github.API_VERSION,
                    }
                )
            else:
                headers.update(
                    {
                        "Notion-Version": notion.NOTION_API_VERSION,
                        "Content-Type": "application/json",
                    }
                )

            async def exchange():
                self.did_request = True
                async with self.client.stream(
                    method,
                    ORIGINS[self.provider] + path,
                    params=params,
                    json=body,
                    headers=headers,
                    timeout=limit,
                ) as response:
                    if not 200 <= response.status_code < 300:
                        _unavailable()
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(data) + len(chunk) > MAX_RESPONSE_BYTES:
                            _unavailable()
                        data.extend(chunk)
                    parsed = json.loads(data)
                    if not isinstance(parsed, dict):
                        _unavailable()
                    return parsed

            pending = asyncio.create_task(exchange())
            try:
                while True:
                    done, _ = await asyncio.wait({pending}, timeout=RECHECK_SECONDS)
                    # Recheck even if the response won the race with revocation.
                    await self.check()
                    if done:
                        return await pending
            finally:
                if not pending.done():
                    pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)

        try:
            return await asyncio.wait_for(monitored(), limit)
        except asyncio.CancelledError:
            raise
        except Exception:
            _unavailable()

    async def github(self, arguments):
        query, path = arguments.query, arguments.path_params
        repository = github.normalize_repository(
            query.get("repository") or f"{path.get('owner')}/{path.get('repo')}"
        )

        def now():
            return datetime.now(timezone.utc).isoformat()

        if self.command.command_id.endswith("_search"):
            payload = await self.request(
                "GET",
                "/search/issues",
                params={
                    "q": f'repo:{repository} "{query["query"].strip()}"',
                    "page": 1,
                    "per_page": 25,
                },
            )
            rows, total = payload.get("items"), payload.get("total_count")
            if not isinstance(rows, list) or type(total) is not int or total < 0:
                _unavailable()
            retrieved = now()
            results = []
            for row in rows[:25]:
                if not isinstance(row, dict):
                    _unavailable()
                results.append(
                    {
                        **github.GitHubClient._object(row, repository, retrieved),
                        "preview": str(row.get("body") or "")[:512],
                    }
                )
            return {
                "connection_id": "github_knowledge",
                "capability": "content_search",
                "results": results,
                "retrieved_at": retrieved,
                "next_page": 2 if total > 25 else None,
                "results_incomplete": bool(payload.get("incomplete_results"))
                or total > 1000,
            }
        number = path["number"]
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            _unavailable()
        payload = await self.request("GET", f"/repos/{repository}/issues/{number}")
        retrieved = now()
        obj = github.GitHubClient._object(payload, repository, retrieved)
        if obj["number"] != number or (
            payload.get("body") is not None and not isinstance(payload["body"], str)
        ):
            _unavailable()
        content = payload.get("body") or ""
        return {
            "connection_id": "github_knowledge",
            "capability": "content_read",
            "object": obj,
            "content": content[: github.MAX_CONTENT_CHARS],
            "content_truncated": len(content) > github.MAX_CONTENT_CHARS,
            "content_scope": "issue_or_pull_request_body_only",
            "retrieved_at": retrieved,
        }

    async def notion(self, arguments):
        if self.command.command_id.endswith("_search"):
            payload = await self.request(
                "POST",
                "/search",
                body={
                    "query": arguments.query["query"].strip(),
                    "page_size": 25,
                    "filter": {"property": "object", "value": "page"},
                },
            )
            rows = payload.get("results")
            if not isinstance(rows, list):
                _unavailable()
            retrieved = notion._retrieved_at()
            return {
                "connection_id": "notion",
                "capability": "content_search",
                "results": [
                    notion._normalize_search_page(row, retrieved)
                    for row in rows
                    if isinstance(row, dict) and row.get("object") == "page"
                ][:25],
                "next_cursor": (
                    str(payload["next_cursor"])[:1024]
                    if payload.get("has_more") and payload.get("next_cursor")
                    else None
                ),
                "retrieved_at": retrieved,
            }
        root = _object_id(arguments.path_params["object_id"])
        page = await self.request("GET", f"/pages/{root}")
        if page.get("object") != "page" or _object_id(page.get("id")) != root:
            _unavailable()
        blocks, budget = [], [notion.MAX_BLOCK_REQUESTS]

        async def children(block_id, depth):
            truncated, cursor, seen = False, None, set()
            while len(blocks) < notion.MAX_BLOCKS:
                if budget[0] <= 0:
                    return True
                budget[0] -= 1
                params = {"page_size": min(100, notion.MAX_BLOCKS - len(blocks))}
                if cursor:
                    params["start_cursor"] = cursor
                payload = await self.request(
                    "GET", f"/blocks/{block_id}/children", params=params
                )
                rows = payload.get("results")
                if not isinstance(rows, list):
                    _unavailable()
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if len(blocks) >= notion.MAX_BLOCKS:
                        return True
                    blocks.append(row)
                    if row.get("has_children"):
                        if depth >= notion.MAX_BLOCK_DEPTH:
                            truncated = True
                        else:
                            truncated = (
                                await children(_object_id(row.get("id")), depth + 1)
                                or truncated
                            )
                if not payload.get("has_more"):
                    return truncated
                cursor = payload.get("next_cursor")
                if (
                    not isinstance(cursor, str)
                    or not 1 <= len(cursor) <= 1024
                    or cursor in seen
                ):
                    _unavailable()
                seen.add(cursor)
            return True

        truncated = await children(root, 0)
        full = "\n".join(text for row in blocks if (text := notion._block_text(row)))
        retrieved = notion._retrieved_at()
        return {
            "connection_id": "notion",
            "capability": "content_read",
            "object": {
                **notion._provenance(page, retrieved),
                "parent": notion._parent_metadata(page),
                "created_at": page.get("created_time"),
                "last_edited_at": page.get("last_edited_time"),
            },
            "content": full[: notion.MAX_CONTENT_CHARS],
            "content_truncated": truncated or len(full) > notion.MAX_CONTENT_CHARS,
            "block_count": len(blocks),
            "retrieved_at": retrieved,
        }


async def execute_accepted_provider_read(
    *, fence: AcceptedKnowledgeRead, payload, command
) -> dict[str, Any]:
    reader = None
    try:
        remaining = await _authority(fence.remaining_seconds)
        limit = min(fence._monotonic_deadline, time.monotonic() + remaining)
        arguments = await _authority(fence.arguments, seconds=limit - time.monotonic())
        async with httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
        ) as client:
            reader = _Reader(fence, payload, command, client, limit)
            result = await (
                reader.github(arguments)
                if reader.provider == "github"
                else reader.notion(arguments)
            )
            await reader.check()
        return {"status_code": 200, "headers": {}, "body": result}
    except asyncio.CancelledError:
        raise
    except Exception:
        deadline = accepted_chat_deadline_for_task(fence._task)
        if time.monotonic() >= fence._monotonic_deadline or (
            deadline is not None
            and datetime.now(timezone.utc) >= deadline.work_deadline_at
        ):
            raise AcceptedChatTaskDeadlineExceeded(
                attempted=bool(reader and reader.did_request)
            ) from None
        _unavailable()
