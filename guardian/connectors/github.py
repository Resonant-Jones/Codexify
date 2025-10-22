"""GitHub connector helpers."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

API_ROOT = "https://api.github.com"
LOGGER = logging.getLogger(__name__)


def _headers(token: Optional[str]) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "guardian-backend",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_json(url: str, token: Optional[str]) -> List[Dict[str, Any]]:
    resp = requests.get(url, headers=_headers(token), timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return []


def _format_doc(kind: str, record: Dict[str, Any], fetched_at: str) -> Optional[Dict[str, Any]]:
    external_id = record.get("id")
    if external_id is None:
        return None
    return {
        "external_id": f"{kind}:{external_id}",
        "payload": {
            "kind": kind,
            "source_url": record.get("html_url"),
            "data": record,
        },
        "fetched_at": fetched_at,
    }


def sync_repo(owner: str, repo: str, token: Optional[str]) -> List[Dict[str, Any]]:
    """Return a list of JSON documents (issues + pull requests)."""
    base = f"{API_ROOT}/repos/{owner}/{repo}"
    results: List[Dict[str, Any]] = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    issues = _fetch_json(f"{base}/issues?state=all&per_page=50", token)
    for issue in issues:
        if issue.get("pull_request"):
            continue
        formatted = _format_doc("issue", issue, fetched_at)
        if formatted:
            results.append(formatted)

    pulls = _fetch_json(f"{base}/pulls?state=all&per_page=50", token)
    for pr in pulls:
        formatted = _format_doc("pull_request", pr, fetched_at)
        if formatted:
            results.append(formatted)

    if not results:
        LOGGER.info("[github] No items fetched for %s/%s", owner, repo)

    return results
