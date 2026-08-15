"""
EXAMPLE 1: Managed Agents — Agent (once) -> Session (every run)

Compare this to 04-tool-use-schema-design/1_simple_loop.py (you write the
tool-use loop yourself) and 9_agent_sdk_builtin_loop.py (the Agent SDK
writes the loop, but it still runs as a local subprocess on your machine).
Managed Agents is the third option: Anthropic's servers run the agent loop
AND host the sandbox where tools execute. There's no local while-loop here
and no local process running "bash" -- that happens in a container on
Anthropic's side. Your code only ever sends/receives JSON events over an
SSE stream.

Mandatory flow (see _setup.py for why steps 1-2 are guarded):
1. POST /v1/environments  — a reusable sandbox template          (ONCE)
2. POST /v1/agents        — model + system + tools, versioned    (ONCE)
3. POST /v1/sessions      — a single run, references the agent   (EVERY RUN)
4. Stream events in/out until the session goes idle/terminated

Note: step 3 provisions a real cloud sandbox container, so this script
takes noticeably longer to run than the Messages-API examples elsewhere in
this repo (tens of seconds), and incurs a small real compute + token cost.

Requires Managed Agents beta access on your API key's workspace. If you get
a 403/404 below, the beta likely isn't enabled yet for this workspace.
"""

import sys
from pathlib import Path

from anthropic import Anthropic, APIStatusError
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _setup import get_or_create_agent, get_or_create_environment

load_dotenv()
client = Anthropic()

# Swap for your actual workspace slug if the API key isn't in the org's
# Default workspace -- the session response doesn't carry it.
WORKSPACE = "default"


def build_agent_and_environment():
    environment_id = get_or_create_environment(
        client,
        key="basics",
        name="managed-agents-practice-env",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )

    agent_id, version = get_or_create_agent(
        client,
        key="basics",
        name="Managed Agents Practice — Basics",
        model="claude-haiku-4-5",
        system=(
            "You are a sandboxed shell assistant. When asked to inspect the "
            "environment, use the bash tool and report exactly what it returns."
        ),
        tools=[{"type": "agent_toolset_20260401"}],
    )
    return environment_id, agent_id, version


def run_session(environment_id, agent_id, version):
    print("\n" + "=" * 70)
    print("Creating a session (this provisions a real sandbox container)")
    print("=" * 70)
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent_id, "version": version},
        environment_id=environment_id,
        title="Managed Agents basics — sandbox proof",
    )
    print(f"Session: {session.id} (status={session.status})")
    print(f"Trace:   https://platform.claude.com/workspaces/{WORKSPACE}/sessions/{session.id}")

    task = "Run `pwd && whoami && ls /workspace` and tell me exactly what each command printed."
    print(f"\n📨 User: {task}")

    # Stream-first: open the stream BEFORE sending, or early events can be missed.
    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        client.beta.sessions.events.send(
            session_id=session.id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": task}]}],
        )

        for event in stream:
            if event.type == "agent.tool_use":
                print(f"\n🔧 Sandbox executed (server-side, NOT on your machine): {event.name}({event.input})")
            elif event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(f"\n🤖 Claude: {block.text}")
            elif event.type == "session.status_idle":
                # Don't break on idle alone -- it also fires transiently
                # between tool calls. Only stop when nothing is pending.
                if event.stop_reason.type != "requires_action":
                    break
            elif event.type == "session.status_terminated":
                break

    try:
        session = client.beta.sessions.retrieve(session_id=session.id)
        print(f"\n💰 Session usage: {session.usage.input_tokens} in / {session.usage.output_tokens} out")
    except Exception:
        pass

    # Sessions are cheap, per-run, disposable -- archiving one is routine
    # cleanup. Contrast with the agent/environment above: those are
    # persistent, reusable resources, and archiving them is PERMANENT with
    # no unarchive -- never do that as routine cleanup.
    try:
        client.beta.sessions.archive(session_id=session.id)
        print(f"Archived session {session.id}.")
    except Exception as e:
        print(f"(Couldn't archive session yet, harmless: {e})")


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Managed Agents — Agent (once) -> Session (every run)")
    print("=" * 70)

    try:
        environment_id, agent_id, version = build_agent_and_environment()
        run_session(environment_id, agent_id, version)
    except APIStatusError as e:
        if e.status_code in (403, 404):
            print(
                f"\n⚠️  Managed Agents beta doesn't appear to be enabled for this "
                f"workspace yet ({e.status_code}: {e.message}). Ask your Anthropic "
                f"contact to enable it, then re-run this script."
            )
            return
        raise

    print("""
📝 Takeaway: nothing above is a while-loop you wrote (contrast with
1_simple_loop.py), and nothing spawned a subprocess on your machine
(contrast with 9_agent_sdk_builtin_loop.py). `bash` genuinely ran inside
Anthropic's sandbox container -- your process only ever sent/received JSON
events over the session stream. The agent config (model/system/tools) is
also a separate, versioned, reusable resource: re-run this script and watch
it print "Reusing agent..." / "Reusing environment..." instead of creating
new ones each time.
""")


if __name__ == "__main__":
    main()
