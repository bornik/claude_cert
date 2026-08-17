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

IMPORTANT — this is NOT the `anthropic` REST API package. It's `claude-agent-sdk`,
which needs the `claude` CLI installed (`npm install -g @anthropic-ai/claude-code`
or equivalent) — every `query()` call spawns it as a subprocess; that's the SDK's
only transport, there's no way to talk to Claude through this SDK without it. It
also needs `ANTHROPIC_API_KEY` for the CLI to call the Claude API. By default it
registers a full set of Claude Code's own built-in tools (Bash, Read, Edit, ...)
into every call, which inflates token usage for no reason in an example like this
— so this script explicitly sets `tools=[]` (no built-ins), defines only the
custom `get_weather` tool as an in-process MCP server (`create_sdk_mcp_server`,
which runs our tool inside this same Python process instead of spawning a
separate MCP server process for it), and pins `model=` (a machine's own default
model preference otherwise applies) to keep the comparison fair and predictable.

Even with built-ins disabled, this call still costs noticeably more than
Example 1's raw API call for the same prompt — the CLI subprocess carries its
own harness/system-prompt overhead that a direct Messages API call doesn't.
That overhead, not the tool loop itself, is most of the cost difference.
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

# Enable debug logging to see what's sent to Claude
if os.getenv("DEBUG_SDK"):
    import logging
    logging.basicConfig(level=logging.DEBUG)

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


async def bare_query_cost():
    """Isolate the CLI subprocess's fixed overhead: same prompt, same model,
    but no MCP server and no tool at all — nothing left to explain a token
    difference from Example 1's raw API call except the CLI harness itself."""
    prompt = "What's the weather in Paris?"
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            model="claude-haiku-4-5",
            max_turns=1,
            setting_sources=[],
            tools=[],
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"\n💰 Bare query() usage (no tools, no MCP server): "
                  f"{message.usage['input_tokens']} in / {message.usage['output_tokens']} out "
                  f"— ~${message.total_cost_usd:.5f}")


async def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 9: Same Loop, Driven by the Agent SDK Instead of Our Code")
    print("=" * 70)

    print("\n--- Baseline: bare query(), no tools/MCP at all ---")
    await bare_query_cost()
    print("--- Compare against Example 1's raw API usage, and against the ---")
    print("--- weather-tool run below, to see where the extra tokens go.  ---\n")

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

💡 Cost breakdown — compare the three usage lines from this run:
   1. Example 1 (raw API, no CLI):        cheapest — no harness overhead
   2. Bare query() above (CLI, no tools): CLI's fixed subprocess/harness tax
   3. Weather-tool query() (CLI + MCP):   #2 plus this tool's schema cost
   The gap between #1 and #2 is what the CLI subprocess costs you just to
   exist, before a single tool is registered. The gap between #2 and #3 is
   the actual cost of the MCP tool definition and its round trip.
""")


if __name__ == "__main__":
    asyncio.run(main())
