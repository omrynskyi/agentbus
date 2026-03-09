from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import yaml


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class AgentState:
    agent_id: str
    agent_type: str = "coding"
    squad: Optional[str] = None
    current_task: Optional[str] = None
    claimed_resources: list[str] = field(default_factory=list)
    status: str = "idle"
    blocked_by: Optional[str] = None
    started_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Runtime only — not serialized to YAML
    issue_number: Optional[int] = None

    def to_yaml(self) -> str:
        data: dict[str, Any] = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "squad": self.squad,
            "current_task": self.current_task,
            "claimed_resources": self.claimed_resources,
            "status": self.status,
            "blocked_by": self.blocked_by,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, body: str) -> Optional[AgentState]:
        if not body:
            return None
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError:
            return None
        if not isinstance(data, dict) or "agent_id" not in data:
            return None
        return cls(
            agent_id=data.get("agent_id", ""),
            agent_type=data.get("agent_type", "coding"),
            squad=data.get("squad"),
            current_task=data.get("current_task"),
            claimed_resources=data.get("claimed_resources") or [],
            status=data.get("status", "idle"),
            blocked_by=data.get("blocked_by"),
            started_at=data.get("started_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
            metadata=data.get("metadata") or {},
        )
