from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ._github import GitHubClient

# name -> (hex color without #, description)
CORE_LABELS: dict[str, tuple[str, str]] = {
    "agentbus":          ("0075ca", "AgentBus agent tracking"),
    "status:working":    ("2ea44f", "Agent is actively executing a task"),
    "status:idle":       ("e4e669", "Agent is registered but idle"),
    "status:blocked":    ("e99695", "Agent is waiting on a dependency"),
    "status:done":       ("7057ff", "Agent completed its last task"),
    "status:failed":     ("d73a4a", "Agent encountered an error"),
    "agentbus:conflict": ("b60205", "Resource conflict detected"),
}

STATUS_LABELS: frozenset[str] = frozenset(
    {"status:working", "status:idle", "status:blocked", "status:done", "status:failed"}
)


def ensure_labels(gh: GitHubClient, squad: Optional[str] = None) -> None:
    """Create all required AgentBus labels if they don't already exist."""
    for name, (color, description) in CORE_LABELS.items():
        gh.create_label(name, color, description)

    if squad:
        _ensure_squad_label(gh, squad)


def ensure_squad_label(gh: GitHubClient, squad: str) -> None:
    _ensure_squad_label(gh, squad)


def _ensure_squad_label(gh: GitHubClient, squad: str) -> None:
    name = f"agentbus:squad:{squad}"
    gh.create_label(name, "bfd4f2", f"AgentBus squad: {squad}")
