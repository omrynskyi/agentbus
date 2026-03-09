---
name: agentbus
description: Coordinate with other agents using AgentBus — register, claim resources, check for conflicts, log progress, and signal completion via GitHub Issues.
---

# AgentBus Skill for Claude

## What is AgentBus?

AgentBus is a GitHub-native coordination layer for AI agent teams. It uses GitHub Issues as a real-time state bus — agents register themselves, broadcast what they are working on, claim resources, detect conflicts, and signal completion. No external database or infrastructure is required.

**Key principle:** Every agent in a repo has one GitHub Issue. That Issue is its identity, status board, and audit log.

---

## When to Use AgentBus

Use AgentBus whenever you are:
- About to start a task that modifies files in a shared codebase
- Working in a repo where other agents (or humans) may be doing related work simultaneously
- About to write to a file, table, API, or other resource that another agent might also be targeting
- Completing or failing a task that other agents may be waiting on

Do not use AgentBus for:
- Reading files (no need to claim read-only access)
- Ephemeral scratch work that does not touch shared resources
- Tasks in isolated environments with no other concurrent agents

---

## Setup

```python
from agentbus import AgentBus
import os

bus = AgentBus(
    repo="org/repo-name",           # The GitHub repo you are working in
    token=os.environ["GITHUB_TOKEN"] # GitHub token with repo scope
)
```

---

## Standard Task Workflow

Follow this pattern for every task:

### Step 1: Register

Call `register` once at the start of your session. It is idempotent — safe to call every time.

```python
agent = bus.register(
    agent_id="my-agent-01",     # Unique, stable identifier for this agent
    agent_type="coding",        # coding | review | test | deploy | analysis
    squad="platform"            # Optional: your team/squad name
)
```

### Step 2: Check In and Claim Resources

Before touching any file or resource, check in and declare what you intend to modify.

```python
agent.checkin(
    task="Adding rate limiting to the payments API",
    resources=[
        "api/payments.py",
        "api/middleware/rate_limit.py",
        "tests/test_payments.py"
    ]
)
```

### Step 3: Check for Conflicts

Always check for conflicts immediately after checking in, before doing any work.

```python
conflicts = agent.check_conflicts(resources=[
    "api/payments.py",
    "api/middleware/rate_limit.py",
    "tests/test_payments.py"
])

if conflicts:
    # Another agent has claimed one of these resources
    for conflict in conflicts:
        print(f"Conflict: {conflict.agent_id} is working on {conflict.claimed_resources}")
    
    # Option A: Block and wait
    agent.block(blocked_by=conflicts[0].agent_id)
    bus.wait_for(agent_id=conflicts[0].agent_id, status="done", timeout=600)
    agent.unblock()
    
    # Option B: Abort and report
    agent.fail(reason=f"Resource conflict with {conflicts[0].agent_id} — needs human resolution")
    raise SystemExit(1)
```

### Step 4: Do the Work

Proceed with your task normally.

### Step 5: Complete or Fail

```python
# On success
agent.done(summary="Added rate limiting — 100 req/min per API key, tests passing")

# On failure
agent.fail(reason="Circular import introduced by rate_limit.py — needs human review")
```

---

## Querying Peer State

Before starting work, you can survey what other agents in the repo are doing:

```python
# See all currently active agents
active = bus.query(status="working")
for a in active:
    print(f"{a.agent_id}: {a.current_task} — claiming {a.claimed_resources}")

# See if anyone is working on a specific file
all_agents = bus.query(status="working")
file_owners = [a for a in all_agents if "api/payments.py" in a.claimed_resources]

# Scope to your squad only (faster on large teams)
squad_agents = bus.query(status="working", squad="platform")

# Check a specific agent
peer = bus.get("schema-migration-agent-01")
print(peer.status, peer.current_task)
```

---

## Waiting on Dependencies

If your task cannot begin until another agent finishes:

```python
# Wait up to 10 minutes for the migration agent to complete
bus.wait_for(
    agent_id="schema-migration-agent-01",
    status="done",
    timeout=600  # seconds
)

# Then proceed
agent.checkin(task="Running post-migration data validation", resources=["db/validate.py"])
```

---

## Logging Mid-Task

Append progress notes to your Issue without changing status:

```python
agent.log("Completed payments.py refactor — moving to middleware")
agent.log("Found unexpected dependency on legacy auth module — investigating")
```

---

## Example: Full Task Lifecycle

```python
from agentbus import AgentBus, ConflictError
import os

bus = AgentBus(repo="acme/backend", token=os.environ["GITHUB_TOKEN"])

# Register this agent
agent = bus.register(agent_id="auth-refactor-03", agent_type="coding", squad="security")

# Declare intent
target_files = ["auth/tokens.py", "auth/session.py", "tests/test_auth.py"]
agent.checkin(task="Migrating JWT tokens to RS256 algorithm", resources=target_files)

# Check for conflicts
conflicts = agent.check_conflicts(target_files)
if conflicts:
    agent.block(blocked_by=conflicts[0].agent_id)
    agent.log(f"Waiting for {conflicts[0].agent_id} to release auth/ files")
    bus.wait_for(conflicts[0].agent_id, status="done", timeout=300)
    agent.unblock()

# Do the actual work
try:
    # ... your task logic here ...
    agent.log("Completed tokens.py — starting session.py")
    # ... more work ...
    agent.done(summary="JWT migration complete. All tests passing. PR #482 opened.")

except Exception as e:
    agent.fail(reason=f"Unexpected error: {str(e)}")
    raise
```

---

## Status Reference

| Status | Meaning |
|---|---|
| `idle` | Registered but not currently working |
| `working` | Actively executing a task |
| `blocked` | Waiting on another agent |
| `done` | Last task completed successfully |
| `failed` | Last task failed; resources released |

---

## Resource Naming Conventions

Use consistent, unambiguous resource names so conflict detection works correctly across agents:

```python
# Files — use repo-relative paths
"src/components/Login.tsx"
"api/payments.py"

# Database tables
"database:users"
"database:transactions"

# External APIs or services
"service:stripe-api"
"service:sendgrid"

# Logical features or domains
"feature:auth-flow"
"feature:checkout"
```

---

## Human Visibility

All agent state is visible to humans in the GitHub Issues tab:

- Filter `label:agentbus` to see all registered agents
- Filter `label:agentbus + label:status:working` to see active agents
- Filter `label:agentbus:conflict` to see active conflicts needing human review
- Click any agent Issue to see its full history of state transitions

---

## Error Handling

```python
from agentbus import AgentBus, ConflictError, AgentBusError

try:
    agent.checkin(task="...", resources=["path/to/file.py"])
except AgentBusError as e:
    # GitHub API failure — safe to retry
    print(f"AgentBus unavailable: {e} — proceeding without coordination")
```

AgentBus is designed to degrade gracefully. If GitHub is unavailable or rate-limited, catch `AgentBusError` and proceed — coordination is a best-effort safety layer, not a hard blocker.

---

## Tips for Large Teams

- Always set the `squad` parameter in `register()` — it scopes queries and speeds up conflict detection
- Keep `resources` lists tight — only claim files you will actually write to
- Call `agent.done()` promptly when finished — it releases your resource claims for other agents
- Use `agent.log()` generously — it helps humans and other agents understand your progress
- If you are spawning sub-agents, pass your `agent_id` as metadata so the dependency chain is visible
