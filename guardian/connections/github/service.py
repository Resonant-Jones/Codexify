"""Bounded GitHub issue/PR evidence; no sync, persistence, or mutation.

Repository grants are supplied by the account-owned credential boundary, never
inferred from token permissions. Callers must re-resolve that boundary per read.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable

import requests

API_BASE = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_RESULTS = 50
MAX_CONTENT_CHARS = 50_000
REQUEST_TIMEOUT_SECONDS = 15
_REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}\Z")


class GitHubError(RuntimeError):
    error_code = "github_provider_error"


class GitHubNotConfiguredError(GitHubError):
    error_code = "github_not_configured"


class GitHubAuthorizationError(GitHubError):
    error_code = "github_authorization_failed"


class GitHubScopeError(GitHubError):
    error_code = "github_scope_denied"


class GitHubTransportError(GitHubError):
    error_code = "github_transport_error"


class GitHubProviderError(GitHubError):
    error_code = "github_provider_error"


class GitHubObjectNotFoundError(GitHubError):
    error_code = "github_object_not_found"


def normalize_repository(value: str) -> str:
    if not isinstance(value, str) or not _REPOSITORY.fullmatch(value):
        raise GitHubScopeError("Invalid repository selection")
    if value.split("/", 1)[1] in {".", ".."}:
        raise GitHubScopeError("Invalid repository selection")
    return value.lower()


class GitHubClient:
    def __init__(self, token: str, allowed_repositories: Iterable[str]) -> None:
        if not isinstance(token, str) or not token.strip():
            raise GitHubNotConfiguredError("No GitHub credential configured")
        if isinstance(allowed_repositories, (str, bytes)):
            raise GitHubScopeError("Repository grants must be explicit")
        self._repositories = frozenset(
            normalize_repository(v) for v in allowed_repositories
        )
        if not self._repositories or len(self._repositories) > 20:
            raise GitHubScopeError("One to twenty repository grants are required")
        self._token = token

    def _scope(self, repository: str) -> str:
        repository = normalize_repository(repository)
        if repository not in self._repositories:
            raise GitHubScopeError("Repository is outside the connection grant")
        return repository

    def _request_json(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{API_BASE}{path}",
                params=params,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": API_VERSION,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise GitHubTransportError(
                "GitHub request could not be completed"
            ) from None
        if response.status_code in {401, 403}:
            raise GitHubAuthorizationError("GitHub rejected the configured access")
        if response.status_code == 404:
            raise GitHubObjectNotFoundError("GitHub object was not found")
        if response.status_code >= 300:
            raise GitHubProviderError("GitHub returned an unsuccessful response")
        try:
            payload = response.json()
        except ValueError:
            raise GitHubProviderError("GitHub returned an invalid response") from None
        if not isinstance(payload, dict):
            raise GitHubProviderError("GitHub returned an invalid response")
        return payload

    def validate(self) -> None:
        for repository in sorted(self._repositories):
            payload = self._request_json(f"/repos/{repository}")
            if str(payload.get("full_name") or "").lower() != repository:
                raise GitHubProviderError(
                    "GitHub returned unexpected repository identity"
                )

    def _object(
        self, row: dict[str, Any], repository: str, retrieved_at: str
    ) -> dict[str, Any]:
        number = row.get("number")
        if type(number) is not int or number <= 0:
            raise GitHubProviderError("GitHub returned invalid object identity")
        expected_api_url = f"{API_BASE}/repos/{repository}/issues/{number}"
        if str(row.get("url") or "").lower() != expected_api_url:
            raise GitHubProviderError("GitHub returned an out-of-scope object")
        kind = "pull_request" if isinstance(row.get("pull_request"), dict) else "issue"
        return {
            "provider": "github",
            "source_system": "github",
            "repository": repository,
            "number": number,
            "object_type": kind,
            "external_object_id": f"{repository}#{number}",
            "external_url": f"https://github.com/{repository}/{'pull' if kind == 'pull_request' else 'issues'}/{number}",
            "title": str(row.get("title") or "")[:1024],
            "state": str(row.get("state") or "")[:32],
            "created_at": row.get("created_at"),
            "last_edited_at": row.get("updated_at"),
            "retrieved_at": retrieved_at,
        }

    def search(
        self, *, repository: str, query: str, page: int = 1, limit: int = 25
    ) -> dict[str, Any]:
        repository = self._scope(repository)
        # A phrase, not arbitrary GitHub search syntax. The host supplies scope.
        if (
            not isinstance(query, str)
            or not 1 <= len(query.strip()) <= 500
            or any(c in query for c in ':"\\\n\r')
        ):
            raise GitHubScopeError("Search requires a bounded plain-text phrase")
        if (
            type(page) is not int
            or type(limit) is not int
            or not 1 <= limit <= MAX_RESULTS
            or not 1 <= page
            or page * limit > 1000
        ):
            raise GitHubScopeError("Invalid search page or limit")
        payload = self._request_json(
            "/search/issues",
            params={
                "q": f'repo:{repository} "{query.strip()}"',
                "page": page,
                "per_page": limit,
            },
        )
        rows = payload.get("items")
        total = payload.get("total_count")
        if not isinstance(rows, list) or type(total) is not int or total < 0:
            raise GitHubProviderError("GitHub returned invalid search results")
        retrieved_at = datetime.now(timezone.utc).isoformat()
        results = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                raise GitHubProviderError("GitHub returned invalid search results")
            results.append(
                {
                    **self._object(row, repository, retrieved_at),
                    "preview": str(row.get("body") or "")[:512],
                }
            )
        return {
            "connection_id": "github_knowledge",
            "capability": "content_search",
            "results": results,
            "retrieved_at": retrieved_at,
            "next_page": page + 1 if page * limit < min(total, 1000) else None,
            "results_incomplete": bool(payload.get("incomplete_results"))
            or total > 1000,
        }

    def read_issue(self, *, repository: str, number: int) -> dict[str, Any]:
        repository = self._scope(repository)
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise GitHubScopeError("Invalid issue number")
        payload = self._request_json(f"/repos/{repository}/issues/{number}")
        retrieved_at = datetime.now(timezone.utc).isoformat()
        obj = self._object(payload, repository, retrieved_at)
        if obj["number"] != number:
            raise GitHubProviderError("GitHub returned unexpected object identity")
        body = payload.get("body")
        if body is not None and not isinstance(body, str):
            raise GitHubProviderError("GitHub returned invalid object content")
        body = body or ""
        return {
            "connection_id": "github_knowledge",
            "capability": "content_read",
            "object": obj,
            "content": body[:MAX_CONTENT_CHARS],
            "content_truncated": len(body) > MAX_CONTENT_CHARS,
            "content_scope": "issue_or_pull_request_body_only",
            "retrieved_at": retrieved_at,
        }
