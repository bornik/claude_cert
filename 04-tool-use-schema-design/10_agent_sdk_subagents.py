"""
EXAMPLE 10: Real Subagent Delegation (Agent SDK)

Two earlier examples touched "subagent" without actually spawning one:
- `09-memory/3_skills_on_demand_vs_always_on.py` *simulated* a subagent with
  a second, bare `client.messages.create()` call (fresh `messages[]`, no
  system prompt) just to show it doesn't inherit the parent's loaded Skill.
- `9_agent_sdk_builtin_loop.py` (this module) ran the Agent SDK's tool-use
  loop, but with a single agent doing all the work itself.

This example spawns a REAL subagent: a separate, independently-scoped
Claude turn that the orchestrator delegates to and gets a report back
from — the same mechanism behind Claude Code's own Task tool (the thing
driving "Agent" calls in an interactive session).

The pieces:
- `AgentDefinition` — describes a named subagent type: its own system
  prompt, its own restricted tool list, its own model
- `ClaudeAgentOptions(agents={...})` — registers one or more
  `AgentDefinition`s so the orchestrator can delegate to them by name
- The orchestrator gets this ability through the `Task` tool (it shows up
  in the message stream as a tool_use block named `Agent`, with
  `subagent_type` in its input) — without `tools=["Task"]`, there's no way
  to delegate at all, real or otherwise

Below, only the `weather-checker` subagent is given the custom
`get_weather` tool. The orchestrator itself never gets direct access to
it — it can only reach the weather data by delegating to the subagent
that has it.

NOTE on timing: subagents launch in the background by default (the exact
behavior described in this repo's own Claude Code session for its Agent
tool: "Agents run in the background... you will be notified when it
completes"). That's why the stream below shows the orchestrator's FIRST
reply as a placeholder ("I've launched the agent... running in the
background") with its own `ResultMessage`, and only THEN — once the
subagent's `TaskNotificationMessage` arrives — does the orchestrator take
another turn to report the real answer, with a second `ResultMessage`.
Nothing is broken; that's two turns of one `query()` call, not two calls.
"""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TaskNotificationMessage,
    TaskStartedMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)
from claude_agent_sdk.types import AgentDefinition


# Step 1 (same tool as Example 9): a plain async function, registered as an
# in-process MCP server — nothing subagent-specific about the tool itself.
@tool("get_weather", "Get current weather for a location. Use this when the user asks about weather.", {"location": str})
async def get_weather(args):
    location = args["location"]
    return {"content": [{"type": "text", "text": f"{location}: 18°C, partly cloudy"}]}


weather_server = create_sdk_mcp_server(name="weather", version="1.0.0", tools=[get_weather])

# Step 2: the subagent itself — its own description (how the orchestrator
# decides when to delegate to it), its own system prompt, its own scoped-down
# tool list. It has NO access to anything the orchestrator has beyond what's
# listed here.
weather_checker = AgentDefinition(
    description="Checks current weather for any location. Use for ANY weather-related question.",
    prompt="You are a weather specialist. Use the get_weather tool to answer, then report the result concisely.",
    tools=["mcp__weather__get_weather"],
)


async def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 10: Real Subagent Delegation via the Agent SDK")
    print("=" * 70)

    prompt = "What's the weather in Paris? Delegate this to the weather-checker subagent."
    print(f"\n📨 User: {prompt}")

    # Step 3: ONE query() call — the orchestrator only has the `Task` tool,
    # so its only path to an answer is delegating to `weather-checker`.
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            model="claude-haiku-4-5",
            max_turns=5,
            setting_sources=[],
            tools=["Task"],  # orchestrator can delegate — nothing else built in
            allowed_tools=["Task", "mcp__weather__get_weather"],
            mcp_servers={"weather": weather_server},
            agents={"weather-checker": weather_checker},
        ),
    ):
        if isinstance(message, TaskStartedMessage):
            print(f"\n🚀 Subagent spawned: type={message.data.get('subagent_type')!r}")
        elif isinstance(message, TaskNotificationMessage):
            print(f"📋 Subagent reported back: {message.summary}")
            print(f"   (subagent-only usage — isolated from the orchestrator's own: {message.usage})")
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    if block.input.get("subagent_type"):
                        print(f"\n🔧 Orchestrator delegates: {block.name} -> {block.input['subagent_type']} ({block.input.get('description')})")
                    else:
                        print(f"\n🔧 Subagent's own tool call: {block.name} {block.input}")
                elif isinstance(block, TextBlock):
                    print(f"\n🤖 {block.text}")
        elif isinstance(message, ResultMessage):
            print(f"\n✅ Turn result: {message.result}")
            print(f"💰 Usage: {message.usage['input_tokens']} in / {message.usage['output_tokens']} out — ~${message.total_cost_usd:.5f}")

    print("""
📝 Takeaway: `agents={...}` + `AgentDefinition` is the real mechanism behind
delegation — a genuinely separate Claude turn with its own prompt, its own
restricted tools, and its own token usage, reported back to the orchestrator
through a Task/Agent tool_result. Compare that to Module 09's "subagent":
that was one plain API call standing in for two, used only to show a Skill
doesn't carry over. This is what actually happens when Claude Code (or your
own Agent SDK code) hands work to a subagent — scoping tools per-agent like
this is also how you'd stop an orchestrator from touching a capability
(e.g. Bash, or a sensitive MCP tool) that only one specialized subagent
should have.
""")


if __name__ == "__main__":
    asyncio.run(main())
