# AgentBus

GitHub-native coordination layer for AI agent teams. Uses GitHub Issues as a real-time state bus — no extra infrastructure required.

## Install

```bash
pip install git+https://github.com/omrynskyi/agentbus.git
```

Requires a GitHub token with `repo` scope.

## Usage

```python
from agentbus import AgentBus
import os

bus = AgentBus(repo="your-org/your-repo", token=os.environ["GITHUB_TOKEN"])

# Register your agent (idempotent)
agent = bus.register(agent_id="my-agent-01", agent_type="coding", squad="platform")

# Check in and claim files you'll modify
agent.checkin(
    task="Refactoring auth module",
    resources=["auth/tokens.py", "auth/session.py"]
)

# Check for conflicts before doing any work
conflicts = agent.check_conflicts(["auth/tokens.py", "auth/session.py"])
if conflicts:
    agent.block(blocked_by=conflicts[0].agent_id)
    bus.wait_for(conflicts[0].agent_id, status="done", timeout=300)
    agent.unblock()

# Do your work, log progress
agent.log("Completed tokens.py — moving to session.py")

# Signal completion
agent.done(summary="Auth refactor complete, all tests passing")

# Or signal failure
# agent.fail(reason="Merge conflict — needs human review")
```

## See what other agents are doing

```python
# All active agents
for a in bus.query(status="working"):
    print(f"{a.agent_id}: {a.current_task} → {a.claimed_resources}")

# Scoped to your squad
bus.query(status="working", squad="platform")

# Check a specific agent
peer = bus.get("schema-migration-agent-01")
print(peer.status, peer.current_task)
```

## Human visibility

Open the Issues tab in your repo:

- `label:agentbus` — all registered agents
- `label:agentbus label:status:working` — currently active
- `label:agentbus:conflict` — conflicts needing attention

## Claude Code skill

See [`agentbus-skill.md`](./agentbus-skill.md) for the Claude-compatible skill file. Add it to your Claude session so Claude automatically uses AgentBus when working in a shared repo.
