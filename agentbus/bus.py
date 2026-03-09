from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from ._github import GitHubClient
from ._labels import ensure_labels, ensure_squad_label
from .agent import Agent
from .exceptions import AgentBusError
from .models import AgentState

_ISSUE_PREFIX = "[AgentBus] "


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentBus:
    """Entry point for AgentBus. Scoped to a single GitHub repo."""

    def __init__(self, repo: str, token: str) -> None:
        self._repo = repo
        self._gh = GitHubClient(token=token, repo=repo)
        self._labels_ready = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        agent_id: str,
        agent_type: str = "coding",
        squad: Optional[str] = None,
    ) -> Agent:
        """Create or reopen the agent Issue. Returns an Agent ready to use."""
        self._ensure_labels(squad)

        now = _now_iso()
        state = AgentState(
            agent_id=agent_id,
            agent_type=agent_type,
            squad=squad,
            status="idle",
            started_at=now,
            updated_at=now,
        )
        labels = _compute_labels(state)
        body = state.to_yaml()
        title = f"{_ISSUE_PREFIX}{agent_id}"

        existing = self._find_issue(agent_id, state="all")
        if existing:
            state.issue_number = existing["number"]
            # Preserve original started_at if we can parse it
            prior = AgentState.from_yaml(existing.get("body") or "")
            if prior and prior.started_at:
                state.started_at = prior.started_at

            self._gh.update_issue(
                existing["number"],
                body=state.to_yaml(),
                state="open",
                labels=labels,
            )
            self._gh.create_comment(existing["number"], "**registered** (session started)")
        else:
            issue = self._gh.create_issue(title=title, body=body, labels=labels)
            state.issue_number = issue["number"]

        return Agent(state=state, gh=self._gh, bus=self)

    def query(
        self,
        status: Optional[str] = None,
        squad: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> list[AgentState]:
        """List agents matching the given filters."""
        labels = ["agentbus"]
        if status:
            labels.append(f"status:{status}")
        if squad:
            labels.append(f"agentbus:squad:{squad}")

        issues = self._gh.list_issues(labels=labels, state="open")
        agents: list[AgentState] = []
        for issue in issues:
            if not issue.get("title", "").startswith(_ISSUE_PREFIX):
                continue
            state = AgentState.from_yaml(issue.get("body") or "")
            if state is None:
                continue
            if agent_type and state.agent_type != agent_type:
                continue
            state.issue_number = issue["number"]
            agents.append(state)
        return agents

    def get(self, agent_id: str) -> Optional[AgentState]:
        """Get the current state of a specific agent."""
        issue = self._find_issue(agent_id, state="all")
        if not issue:
            return None
        state = AgentState.from_yaml(issue.get("body") or "")
        if state:
            state.issue_number = issue["number"]
        return state

    def wait_for(
        self,
        agent_id: str,
        status: str,
        timeout: int = 600,
        poll_interval: int = 10,
    ) -> AgentState:
        """Block until the agent reaches the given status or timeout expires."""
        deadline = time.monotonic() + timeout
        while True:
            state = self.get(agent_id)
            if state and state.status == status:
                return state
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AgentBusError(
                    f"Timeout waiting for agent '{agent_id}' to reach status '{status}'"
                )
            time.sleep(min(poll_interval, remaining))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_labels(self, squad: Optional[str] = None) -> None:
        if not self._labels_ready:
            ensure_labels(self._gh)
            self._labels_ready = True
        if squad:
            ensure_squad_label(self._gh, squad)

    def _find_issue(self, agent_id: str, state: str = "open") -> Optional[dict]:
        title = f"{_ISSUE_PREFIX}{agent_id}"
        issues = self._gh.list_issues(labels=["agentbus"], state=state)
        return next((i for i in issues if i.get("title") == title), None)


def _compute_labels(state: AgentState) -> list[str]:
    labels = ["agentbus", f"status:{state.status}"]
    if state.squad:
        labels.append(f"agentbus:squad:{state.squad}")
    return labels
