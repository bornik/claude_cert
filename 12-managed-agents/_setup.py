"""
Shared setup helper for the Managed Agents examples in this module.

Managed Agents draws a hard line the raw Messages API and Agent SDK don't
need to: the Agent (model/system/tools) is a PERSISTED, VERSIONED resource
you create ONCE and reuse -- never inside your hot path. Calling
agents.create() at the top of every script run accumulates orphaned agents
and pays create latency for nothing.

This helper enforces that by caching created agent/environment IDs to a
local JSON file (.managed_agents_state.json, gitignored) and reusing them
on every subsequent run. Delete that file if you want fresh resources --
e.g. after editing an agent's system prompt or tools below.
"""

import json
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent / ".managed_agents_state.json"


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_or_create_environment(client, key: str, **create_kwargs) -> str:
    """Return a cached environment_id, or create one once and cache it."""
    state = _load_state()
    cache_key = f"environment:{key}"
    if cache_key in state:
        print(f"♻️  Reusing environment {state[cache_key]!r} (created on a previous run)")
        return state[cache_key]

    print(f"🏗️  Creating environment {key!r} (one-time setup)...")
    environment = client.beta.environments.create(**create_kwargs)
    state[cache_key] = environment.id
    _save_state(state)
    print(f"   Created: {environment.id}")
    return environment.id


def get_or_create_agent(client, key: str, **create_kwargs) -> tuple[str, int]:
    """Return a cached (agent_id, version), or create one once and cache it."""
    state = _load_state()
    cache_key = f"agent:{key}"
    if cache_key in state:
        cached = state[cache_key]
        print(f"♻️  Reusing agent {cached['id']!r} v{cached['version']} (created on a previous run)")
        return cached["id"], cached["version"]

    print(f"🏗️  Creating agent {key!r} (one-time setup)...")
    agent = client.beta.agents.create(**create_kwargs)
    state[cache_key] = {"id": agent.id, "version": agent.version}
    _save_state(state)
    print(f"   Created: {agent.id} (version {agent.version})")
    return agent.id, agent.version
