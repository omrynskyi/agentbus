from __future__ import annotations

import random
import re
import time
from typing import Any, Optional

import requests

from .exceptions import AgentBusError

_BASE = "https://api.github.com"
_MAX_RETRIES = 5


class GitHubClient:
    def __init__(self, token: str, repo: str) -> None:
        self._repo = repo
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    # ------------------------------------------------------------------
    # Core request with retry / backoff
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{_BASE}/{path}"
        for attempt in range(_MAX_RETRIES):
            resp = self._session.request(method, url, **kwargs)
            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    wait = float(retry_after)
                else:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait)
                continue
            try:
                resp.raise_for_status()
            except requests.HTTPError as exc:
                raise AgentBusError(str(exc)) from exc
            return resp
        raise AgentBusError(
            f"GitHub API rate-limited after {_MAX_RETRIES} retries: {method} {path}"
        )

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def list_issues(
        self,
        labels: Optional[list[str]] = None,
        state: str = "open",
    ) -> list[dict]:
        params: dict[str, Any] = {"state": state, "per_page": 100}
        if labels:
            params["labels"] = ",".join(labels)

        results: list[dict] = []
        url: Optional[str] = f"{_BASE}/repos/{self._repo}/issues"
        while url:
            resp = self._session.get(url, params=params)
            try:
                resp.raise_for_status()
            except requests.HTTPError as exc:
                raise AgentBusError(str(exc)) from exc
            results.extend(resp.json())
            params = {}  # only on first request; Link header carries params
            url = _next_link(resp.headers.get("Link", ""))
        return results

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
    ) -> dict:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self._request(
            "POST", f"repos/{self._repo}/issues", json=payload
        ).json()

    def update_issue(
        self,
        number: int,
        *,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict:
        payload: dict[str, Any] = {}
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        return self._request(
            "PATCH", f"repos/{self._repo}/issues/{number}", json=payload
        ).json()

    def create_comment(self, number: int, body: str) -> dict:
        return self._request(
            "POST",
            f"repos/{self._repo}/issues/{number}/comments",
            json={"body": body},
        ).json()

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------

    def create_label(
        self, name: str, color: str, description: str = ""
    ) -> Optional[dict]:
        try:
            return self._request(
                "POST",
                f"repos/{self._repo}/labels",
                json={"name": name, "color": color, "description": description},
            ).json()
        except AgentBusError as exc:
            # 422 Unprocessable Entity means the label already exists — that's fine
            if "422" in str(exc):
                return None
            raise


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _next_link(link_header: str) -> Optional[str]:
    """Parse the 'next' URL from a GitHub Link header."""
    if not link_header:
        return None
    match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
    return match.group(1) if match else None
