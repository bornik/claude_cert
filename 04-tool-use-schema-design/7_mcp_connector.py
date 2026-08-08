"""
EXAMPLE 7: MCP as an Alternative to Manual Schema Authoring

Everything in examples 1-6 assumes YOU write the tool schema: name,
description, input_schema, and the function that runs when Claude issues
a tool_use block. The Model Context Protocol (MCP) moves that work out of
your application and into a dedicated server. If a well-maintained MCP
server exists for the service you need, you connect to it instead of
hand-writing an integration.

This example uses the API's MCP Connector (server-side, beta) to connect
to a public remote MCP server directly in a messages.create() call — no
tool schemas, no execution loop written by us. Compare this to
1_simple_loop.py, where every one of those pieces was ours to write.

Two context-cost controls matter once you connect a server with many
tools, both set via the mcp_toolset entry in the `tools` array:
  - defer_loading: delay loading a tool's definition until the model
    actually needs it (cuts upfront context cost for large tool lists).
  - enabled / configs: allowlist which of the server's tools are exposed
    at all, per tool.

Requirements:
  - The MCP Connector needs the `mcp-client-2025-11-20` beta header.
  - It only supports remote (Streamable HTTP) servers — a local stdio
    server can't be reached through the API connector, only through
    Claude Code / Claude Desktop as the client.

Cost note: the DeepWiki tool result below dumps a full wiki page into
context (~165k input tokens, well over a cent per run on Haiku). This is
exactly the context-cost problem the last section of this script talks
about — don't loop this one.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

# A public remote MCP server (DeepWiki: ask questions about GitHub repos'
# indexed documentation) — no auth required, good for a runnable demo.
MCP_SERVER_URL = "https://mcp.deepwiki.com/mcp"


def demo_manual_vs_mcp():
    print("\n" + "=" * 70)
    print("Manual schema authoring vs. connecting to an MCP server")
    print("=" * 70)
    print("""
Manual (examples 1-6 in this module):
  1. You write input_schema for every operation.
  2. You write the Python function that actually executes each tool.
  3. You maintain both as the underlying service's API evolves.

MCP (this example):
  1. Your MCP client sends a ListToolsRequest to the server.
  2. The server returns its tool definitions — you didn't write them.
  3. Claude picks among them exactly like any tool you'd have authored
     yourself; the tool_use / tool_result loop is unchanged.
  4. The server also EXECUTES the tool call — no Python function of ours
     runs. That's the actual shift: who owns the schema AND the runtime.
""")


def call_via_mcp_connector():
    """Ask a question answerable only via the MCP server's tools, with
    no locally-defined tools at all — everything comes from the server."""
    print("\n" + "=" * 70)
    print("🔴 LIVE CHECK: Calling a tool we never defined, via MCP Connector")
    print("=" * 70)

    query = (
        "Using the available tools, look up the anthropics/anthropic-sdk-python "
        "GitHub repo and tell me in one sentence what the repo is for."
    )
    print(f"\nQuery: {query!r}")
    print(f"MCP server: {MCP_SERVER_URL}")
    print("Local tools defined by us: NONE — all tool defs come from the server.")

    response = client.beta.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        betas=["mcp-client-2025-11-20"],
        mcp_servers=[
            {
                "type": "url",
                "url": MCP_SERVER_URL,
                "name": "deepwiki",
            }
        ],
        tools=[{"type": "mcp_toolset", "mcp_server_name": "deepwiki"}],
        messages=[{"role": "user", "content": query}],
    )
    print_usage(response, model="claude-haiku-4-5")

    print("\nContent blocks returned:")
    for block in response.content:
        if block.type == "mcp_tool_use":
            print(f"  • mcp_tool_use: {block.name}({block.input}) on server '{block.server_name}'")
        elif block.type == "mcp_tool_result":
            preview = str(block.content)[:200]
            print(f"  • mcp_tool_result: {preview}...")
        elif block.type == "text":
            print(f"  • text: {block.text}")

    print("""
📝 Note: we never wrote a schema, an input_schema, or an execution
function for anything DeepWiki exposes. The server told Claude what
tools exist (via ListToolsRequest under the hood) and ran them when
called. The tool_use/tool_result contract you built by hand in
1_simple_loop.py is identical here — mcp_tool_use / mcp_tool_result
are just the MCP-flavored versions of the same blocks.
""")


def show_context_cost_controls():
    print("\n" + "=" * 70)
    print("Controlling context cost: defer_loading and per-tool enabled")
    print("=" * 70)
    print("""
Connecting a server with a large tool list adds every tool's definition
to the context window up front, even for tools you don't use this turn.
Two knobs go on the mcp_toolset entry in `tools` (the one that points at
the server by name), via a default_config plus optional per-tool configs:

    {
        "type": "mcp_toolset",
        "mcp_server_name": "big-server",
        "default_config": {"enabled": True, "defer_loading": True},
        "configs": {
            "search": {"enabled": True, "defer_loading": False},
        },
    }

- defer_loading skips loading a tool's full definition until Claude
  actually needs it — cuts upfront context cost when a server exposes
  many tools.
- enabled (per-tool, inside configs) allowlists/denylists specific tools
  on a server you're otherwise connected to for breadth.
- allowed_tools narrows exposure the same way the "required fields"
  discipline from 3_schema_design.py narrows what Claude has to reason
  about — fewer, sharper choices.
- Manual schema authoring still wins when you need description-level
  control (exclusion clauses, boundary cases like 6_boundary_case_failure.py)
  that a general-purpose server's descriptions won't have tuned for you.
- Realistic combo: connect to an MCP server for breadth (coverage of an
  entire API surface), then allowlist down to the specific tools you
  route to, and — if the server's own descriptions are too vague near a
  boundary — wrap or pre-filter with the same tuning discipline as
  examples 3 and 6.
""")


def main():
    demo_manual_vs_mcp()
    call_via_mcp_connector()
    show_context_cost_controls()


if __name__ == "__main__":
    main()
