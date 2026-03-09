# AgentBus

GitHub-native coordination layer for AI agent teams. Uses GitHub Issues as a real-time state bus — no extra infrastructure required.

## Install

```bash
pip install git+https://github.com/omrynskyi/agentbus.git
```

Requires a GitHub token with `repo` scope.

## How it works

Every agent in a repo gets one GitHub Issue. That Issue is the agent's identity, status board, and audit log. Before touching any shared resource, an agent registers itself, declares what it intends to modify, and checks whether another agent has already claimed those resources. When done, it signals completion so waiting agents can proceed.

No database. No broker. Just GitHub Issues.

## Agent workflow

**Before starting any task that touches shared files or resources:**

1. Register with the bus (idempotent — safe to call every session)
2. Check in with your task description and the resources you intend to modify
3. Check for conflicts — if another agent has claimed a resource, wait or abort
4. Do your work, logging progress as you go
5. Signal done or failed when finished — this releases your resource claims

**Before writing to any file, always check whether another agent owns it.** If there's a conflict, either wait for the owning agent to finish or fail gracefully and surface the conflict to humans.

## Human visibility

Open the Issues tab in your repo:

- `label:agentbus` — all registered agents
- `label:agentbus label:status:working` — currently active
- `label:agentbus:conflict` — conflicts needing human attention

## Claude Code skill

The `/agentbus` skill is in `.claude/skills/agentbus.md`. When working in a repo that uses AgentBus, Claude will automatically follow the coordination protocol — registering, claiming resources, detecting conflicts, and signaling completion.

For full protocol details, see [`agentbus-skill.md`](./agentbus-skill.md).
