# AgentBus

GitHub-native agent state coordination layer. Uses GitHub Issues as a real-time bus — agents register, claim resources, detect conflicts, and signal completion with no external infrastructure.

## Installation

```bash
pip install agentbus
```

Requires a GitHub token with `repo` scope (Issues read/write).

## Quickstart

```python
from agentbus import AgentBus, ConflictError
import os

bus = AgentBus(repo="org/my-repo", token=os.environ["GITHUB_TOKEN"])

# Register (idempotent — creates or reopens the agent Issue)
agent = bus.register(
    agent_id="auth-refactor-03",
    agent_type="coding",
    squad="security",
)

# Declare intent and claim resources
target_files = ["auth/tokens.py", "auth/session.py", "tests/test_auth.py"]
agent.checkin(task="Migrating JWT tokens to RS256 algorithm", resources=target_files)

# Check for conflicts before doing any work
conflicts = agent.check_conflicts(target_files)
if conflicts:
    agent.block(blocked_by=conflicts[0].agent_id)
    agent.log(f"Waiting for {conflicts[0].agent_id} to release auth/ files")
    bus.wait_for(conflicts[0].agent_id, status="done", timeout=300)
    agent.unblock()

# Do the work
try:
    # ... task logic ...
    agent.log("Completed tokens.py — starting session.py")
    # ... more work ...
    agent.done(summary="JWT migration complete. All tests passing.")
except Exception as e:
    agent.fail(reason=f"Unexpected error: {e}")
    raise
```

## API Reference

### `AgentBus`

| Method | Description |
|---|---|
| `AgentBus(repo, token)` | Initialize for a specific repo |
| `bus.register(agent_id, agent_type, squad?)` | Create or reopen agent Issue; returns `Agent` |
| `bus.query(status?, squad?, agent_type?)` | List agents matching filters |
| `bus.get(agent_id)` | Get a specific agent's current state |
| `bus.wait_for(agent_id, status, timeout?, poll_interval?)` | Block until agent reaches status |

### `Agent`

| Method | Description |
|---|---|
| `agent.checkin(task, resources?)` | Update task and claimed resources; sets status `working` |
| `agent.check_conflicts(resources)` | Returns list of agents holding any of the given resources |
| `agent.block(blocked_by)` | Set status to `blocked`, record dependency |
| `agent.unblock()` | Clear blocked status, resume `working` |
| `agent.done(summary?)` | Mark complete, release all resources |
| `agent.fail(reason?)` | Mark failed, release resources |
| `agent.log(message)` | Append informational comment to Issue |

## Label Reference

| Label | Description |
|---|---|
| `agentbus` | All AgentBus issues |
| `status:working` | Agent is actively executing a task |
| `status:idle` | Agent is registered but not working |
| `status:blocked` | Agent is waiting on a dependency |
| `status:done` | Agent completed its last task |
| `status:failed` | Agent encountered an error |
| `agentbus:conflict` | Resource conflict (applied externally) |
| `agentbus:squad:{name}` | Squad scoping for large teams |

Labels are created automatically on first `register()`.

## Human Visibility

All state is visible in the GitHub Issues tab:

- `label:agentbus` — all registered agents
- `label:agentbus label:status:working` — currently active agents
- `label:agentbus:conflict` — conflicts needing human review
- Click any Issue for the full timeline of state transitions

## Resource Naming Conventions

```python
# Files — use repo-relative paths
"src/components/Login.tsx"
"api/payments.py"

# Database tables
"database:users"

# External services
"service:stripe-api"

# Logical features
"feature:auth-flow"
```

## Error Handling

```python
from agentbus import AgentBusError

try:
    agent.checkin(task="...", resources=["path/to/file.py"])
except AgentBusError as e:
    # GitHub API unavailable — proceed without coordination
    print(f"AgentBus unavailable: {e}")
```

AgentBus is designed to degrade gracefully. If GitHub is unavailable, catch `AgentBusError` and proceed — coordination is a best-effort safety layer.

## Tips for Large Teams

- Always set `squad` in `register()` to scope queries and speed up conflict detection
- Keep `resources` lists tight — only claim files you will actually write to
- Call `agent.done()` promptly — it releases resource claims for other agents
- Use `agent.log()` generously for human and agent visibility
- If spawning sub-agents, pass your `agent_id` as metadata so the dependency chain is visible
