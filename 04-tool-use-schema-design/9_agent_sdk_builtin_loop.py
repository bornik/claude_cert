"""
EXAMPLE 9: The Same Loop, Built Into the Agent SDK

Example 1 (`1_simple_loop.py`) hand-rolled the tool-use loop against the raw
Messages API: send a message, check `stop_reason == "tool_use"`, execute the
tool ourselves, append a `tool_result`, call again, repeat until Claude
stops asking for tools. That loop — call, execute, feed back, repeat — is
something you write and maintain yourself.

The Claude Agent SDK (`claude-agent-sdk`, a separate package from `anthropic`)
runs that same loop FOR you. You register a tool as a plain async Python
function via `@tool` + `create_sdk_mcp_server`, call `query()` once, and
consume an async stream of messages — the SDK calls the tool, feeds the
result back, and keeps going until Claude is done. Same weather/Paris
scenario as Example 1, same tool, same outcome — the difference is who
drives the loop.

IMPORTANT — this is NOT the `anthropic` package. It's a different SDK that
spawns the `claude` CLI as a subprocess, so it needs the CLI installed
(`npm install -g @anthropic-ai/claude-code` or equivalent) in addition to
`ANTHROPIC_API_KEY`. Left at its defaults it also registers a full set of
Claude Code's own built-in tools (Bash, Read, Edit, ...) into every call,
which inflates token usage for no reason in an example like this — so this
script explicitly sets `tools=[]` (no built-ins) and pins `model=` (a
machine's own default model preference otherwise applies here, not just
the tool used) to keep the comparison fair and the cost predictable.
"""

import asyncio

from dotenv import load_dotenv

load_dotenv()

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

# Step 1 (same as Example 1): define the tool — but as a real async function,
# not a JSON schema + a manual if/elif dispatching on tool_use_block.name.
@tool("get_weather", "Get current weather for a location. Use this when the user asks about weather. Do not use for forecasts.", {"location": str})
async def get_weather(args):
    location = args["location"]
    result = f"18°C, partly cloudy"
    return {"content": [{"type": "text", "text": f"{location}: {result}"}]}


# Step 2: register it as an in-process MCP server the SDK can call directly —
# no separate process, no network hop, just our Python function.
weather_server = create_sdk_mcp_server(name="weather", version="1.0.0", tools=[get_weather])


async def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 9: Same Loop, Driven by the Agent SDK Instead of Our Code")
    print("=" * 70)

    prompt = "What's the weather in Paris?"
    print(f"\n📨 User: {prompt}")

    # Step 3-5 (the whole loop from Example 1): ONE query() call. The SDK
    # calls get_weather, feeds the result back to Claude, and keeps going
    # until Claude stops asking for tools — we just consume the stream.
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            model="claude-haiku-4-5",
            max_turns=3,
            setting_sources=[],  # don't pull in this machine's CLAUDE.md/settings
            tools=[],  # no Claude Code built-in tools (Bash, Read, Edit, ...) — only ours
            allowed_tools=["mcp__weather__get_weather"],
            mcp_servers={"weather": weather_server},
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"\n🔧 SDK-driven call: {block.name}")
                    print(f"   Arguments: {block.input}")
                elif isinstance(block, TextBlock):
                    print(f"\n🤖 Claude: {block.text}")
        elif isinstance(message, ResultMessage):
            print(f"\n✅ Claude's final answer:\n   {message.result}")
            print(f"\n💰 Usage: {message.usage['input_tokens']} in / {message.usage['output_tokens']} out — ~${message.total_cost_usd:.5f}")

    print("""
📝 Takeaway: the tool call, the tool_result round-trip, and the "keep going
until done" check all happened inside query() — we never wrote a while loop
or an if/elif on block.type. That's the actual tradeoff: Example 1 gives you
full visibility and control over every turn (useful for approval gates,
custom retry logic, or logging every step); the Agent SDK trades that
control for not having to write or maintain the loop yourself. Neither is
strictly better — it's the same "workflow vs. agent" tradeoff from Module 07,
just at the level of who drives tool-use turns instead of who decides
overall task steps.
""")


if __name__ == "__main__":
    asyncio.run(main())
