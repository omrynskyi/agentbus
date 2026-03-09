from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import AgentState


class AgentBusError(Exception):
    """Raised on GitHub API failures or AgentBus-level errors."""


class ConflictError(AgentBusError):
    """Raised when one or more resource conflicts are detected."""

    def __init__(self, conflicts: list[AgentState]) -> None:
        self.conflicts = conflicts
        ids = [c.agent_id for c in conflicts]
        super().__init__(
            f"Resource conflict with {len(conflicts)} agent(s): {ids}"
        )
