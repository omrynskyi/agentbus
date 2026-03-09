"""AgentBus — GitHub-native agent state coordination layer."""

from .agent import Agent
from .bus import AgentBus
from .exceptions import AgentBusError, ConflictError
from .models import AgentState

__version__ = "0.1.0"
__all__ = ["AgentBus", "Agent", "AgentState", "AgentBusError", "ConflictError"]
