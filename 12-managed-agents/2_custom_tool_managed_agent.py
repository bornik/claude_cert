"""
EXAMPLE 2: Managed Agents — Custom Tools via Events (a Third Way to Run
"What's the Weather in Paris?")

This is the SAME task as 04-tool-use-schema-design/1_simple_loop.py (you
poll `response.stop_reason == "tool_use"` in a while loop) and
9_agent_sdk_builtin_loop.py (the Agent SDK's query() drives the loop as a
local subprocess). Here, Managed Agents drives the loop server-side, and
your custom tool call arrives as an `agent.custom_tool_use` EVENT on the
session stream instead of a `tool_use` content BLOCK in a Messages API
response.

Custom tools are the one tool type Managed Agents does NOT execute for you
-- your application still owns the implementation, same as every other
paradigm. What changes is the transport: no `tool_result` content block, no
query() callback -- an `agent.custom_tool_use` event, which you answer with
a `user.custom_tool_result` event.
"""

import sys
from pathlib import Path

from anthropic import Anthropic, APIStatusError
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _setup import get_or_create_agent, get_or_create_environment

load_dotenv()
client = Anthropic()

WORKSPACE = "default"

# Same tool, same fake weather, as 1_simple_loop.py and
# 9_agent_sdk_builtin_loop.py -- only the transport differs below.
WEATHER_TOOL = {
    "type": "custom",
    "name": "get_weather",
    "description": (
        "Get current weather for a location. Use this when the user asks "
        "about weather. Do not use for forecasts."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name, e.g., 'London' or 'Paris'"}
        },
        "required": ["location"],
    },
}


def execute_weather_tool(location: str) -> str:
    return f"{location}: 18°C, partly cloudy"


def build_agent_and_environment():
    environment_id = get_or_create_environment(
        client,
        key="weather",
        name="managed-agents-practice-weather-env",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    agent_id, version = get_or_create_agent(
        client,
        key="weather",
        name="Managed Agents Practice — Weather",
        model="claude-haiku-4-5",
        system="You are a weather assistant. Use get_weather for current-weather questions.",
        tools=[WEATHER_TOOL],
    )
    return environment_id, agent_id, version


def run_session(environment_id, agent_id, version):
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent_id, "version": version},
        environment_id=environment_id,
        title="Managed Agents — custom tool round trip",
    )
    print(f"Session: {session.id}")
    print(f"Trace:   https://platform.claude.com/workspaces/{WORKSPACE}/sessions/{session.id}")

    prompt = "What's the weather in Paris?"
    print(f"\n📨 User: {prompt}")

    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        client.beta.sessions.events.send(
            session_id=session.id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": prompt}]}],
        )

        for event in stream:
            if event.type == "agent.custom_tool_use":
                print(f"\n🔧 Claude called (via EVENT, not a content block): {event.name}({event.input})")
                result = execute_weather_tool(event.input["location"])
                print(f"   Result: {result}")
                client.beta.sessions.events.send(
                    session_id=session.id,
                    events=[
                        {
                            "type": "user.custom_tool_result",
                            "custom_tool_use_id": event.id,
                            "content": [{"type": "text", "text": result}],
                        }
                    ],
                )
            elif event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(f"\n🤖 Claude: {block.text}")
            elif event.type == "session.status_idle":
                if event.stop_reason.type != "requires_action":
                    break
            elif event.type == "session.status_terminated":
                break

    try:
        client.beta.sessions.archive(session_id=session.id)
        print(f"\nArchived session {session.id}.")
    except Exception as e:
        print(f"\n(Couldn't archive session yet, harmless: {e})")


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Managed Agents — Custom Tool Round Trip (same weather task)")
    print("=" * 70)

    try:
        environment_id, agent_id, version = build_agent_and_environment()
        run_session(environment_id, agent_id, version)
    except APIStatusError as e:
        if e.status_code in (403, 404):
            print(
                f"\n⚠️  Managed Agents beta doesn't appear to be enabled for this "
                f"workspace yet ({e.status_code}: {e.message})."
            )
            return
        raise

    print("""
📝 Takeaway: compare the three transports for the exact same tool call:
- 1_simple_loop.py:            a `tool_use` CONTENT BLOCK in an API
  response, polled with `while response.stop_reason == "tool_use"`.
- 9_agent_sdk_builtin_loop.py:  an `AssistantMessage` block yielded from
  query(), handled by a local subprocess running the Agent SDK's own loop.
- this script:                 an `agent.custom_tool_use` EVENT on an SSE
  stream, answered with `user.custom_tool_result` -- no local loop code at
  all; the loop itself lives on Anthropic's servers, not your process.
Your tool's implementation (execute_weather_tool) is identical in all
three -- Managed Agents changes who drives the loop and how results travel
back, never who's responsible for actually running your custom tool code.
""")


if __name__ == "__main__":
    main()
