from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from .models import AgentState

if TYPE_CHECKING:
    from ._github import GitHubClient
    from .bus import AgentBus


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Agent:
    """Represents a registered agent. All state mutations go through this object."""

    def __init__(
        self,
        state: AgentState,
        gh: GitHubClient,
        bus: AgentBus,
    ) -> None:
        self._state = state
        self._gh = gh
        self._bus = bus

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def agent_id(self) -> str:
        return self._state.agent_id

    @property
    def status(self) -> str:
        return self._state.status

    @property
    def current_task(self) -> Optional[str]:
        return self._state.current_task

    @property
    def claimed_resources(self) -> list[str]:
        return list(self._state.claimed_resources)

    @property
    def issue_number(self) -> Optional[int]:
        return self._state.issue_number

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def checkin(self, task: str, resources: Optional[list[str]] = None) -> None:
        """Declare the current task and claim resources. Sets status to working."""
        self._state.current_task = task
        self._state.claimed_resources = list(resources or [])
        self._state.status = "working"
        self._state.updated_at = _now_iso()
        self._update_issue()
        self._gh.create_comment(
            self._state.issue_number,
            f"**check-in**: {task}",
        )

    def check_conflicts(self, resources: list[str]) -> list[AgentState]:
        """Return agents currently claiming any of the given resources."""
        target = set(resources)
        conflicts: list[AgentState] = []
        for peer in self._bus.query(status="working"):
            if peer.agent_id == self._state.agent_id:
                continue
            if target & set(peer.claimed_resources):
                conflicts.append(peer)
        return conflicts

    def block(self, blocked_by: str) -> None:
        """Mark this agent as blocked, waiting on another agent."""
        self._state.status = "blocked"
        self._state.blocked_by = blocked_by
        self._state.updated_at = _now_iso()
        self._update_issue()
        self._gh.create_comment(
            self._state.issue_number,
            f"**blocked** by `{blocked_by}`",
        )

    def unblock(self) -> None:
        """Clear blocked status and resume working."""
        self._state.status = "working"
        self._state.blocked_by = None
        self._state.updated_at = _now_iso()
        self._update_issue()
        self._gh.create_comment(
            self._state.issue_number,
            "**unblocked** — resuming work",
        )

    def done(self, summary: Optional[str] = None) -> None:
        """Mark task complete and release all claimed resources."""
        self._state.status = "done"
        self._state.claimed_resources = []
        self._state.blocked_by = None
        self._state.updated_at = _now_iso()
        self._update_issue()
        msg = "**done**" + (f": {summary}" if summary else "")
        self._gh.create_comment(self._state.issue_number, msg)

    def fail(self, reason: Optional[str] = None) -> None:
        """Mark agent failed and release all claimed resources."""
        self._state.status = "failed"
        self._state.claimed_resources = []
        self._state.blocked_by = None
        self._state.updated_at = _now_iso()
        self._update_issue()
        msg = "**failed**" + (f": {reason}" if reason else "")
        self._gh.create_comment(self._state.issue_number, msg)

    def log(self, message: str) -> None:
        """Append an informational comment without changing status."""
        self._gh.create_comment(
            self._state.issue_number,
            f"**log**: {message}",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_issue(self) -> None:
        body = self._state.to_yaml()
        labels = _compute_labels(self._state)
        self._gh.update_issue(self._state.issue_number, body=body, labels=labels)


def _compute_labels(state: AgentState) -> list[str]:
    labels = ["agentbus", f"status:{state.status}"]
    if state.squad:
        labels.append(f"agentbus:squad:{state.squad}")
    return labels
