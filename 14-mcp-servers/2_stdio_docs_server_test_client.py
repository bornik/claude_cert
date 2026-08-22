"""
EXAMPLE 2: A Real stdio MCP Server — Docs as Resources, Conversion as a
Tool, Tested Before Any Production Client Touches It

The exam scenario: a team builds an MCP server for local engineering
documents. Claude should read the documents as context (a resource, not
a tool call), run one approved conversion operation (a tool, since it
has a real effect), and developers need to test the server before
connecting it to production clients.

Every piece of that maps directly onto what's in this module already:
  - Resources vs. tools: same distinction as
    1_mcp_resources_direct_vs_templated.py, applied to real local files
    on disk instead of an in-memory dict.
  - stdio transport: the CLI walkthrough in this module's README
    connects a remote HTTP server (DeepWiki); docs-server/server.py is
    the local counterpart — a subprocess over stdin/stdout, the right
    choice because the documents and the client are on the same machine.
  - Testing before production: this script IS that test, scripted and
    repeatable. The interactive equivalent — what the exam answer calls
    "MCP Inspector" — is the README's "Try it" section below; the
    mechanism (discover, then call, before wiring up a real client) is
    identical either way.

This script is a plain MCP client — no Claude, no Anthropic API call —
launching docs-server/server.py as a real child process and driving it
exactly like the Claude Code CLI's own MCP client would.
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = Path(__file__).resolve().parent / "docs-server" / "server.py"


async def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: stdio MCP server — docs as resources, conversion as a tool")
    print("=" * 70)

    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)])

    print(f"\nLaunching {SERVER_SCRIPT.name} as a real subprocess over stdio...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected. This is a separate OS process, not an in-memory session.")

            print("\n--- Discovery: what does this server expose, before calling anything? ---")
            resources = await session.list_resources()
            print("Direct resources:")
            for r in resources.resources:
                print(f"   {r.uri}")

            templates = await session.list_resource_templates()
            print("Templated resources:")
            for t in templates.resourceTemplates:
                print(f"   {t.uriTemplate}")

            tools = await session.list_tools()
            print("Tools:")
            for t in tools.tools:
                print(f"   {t.name}: {t.description}")

            print("\n--- Reading a document as a RESOURCE (context, not a tool call) ---")
            listing = await session.read_resource("docs://list")
            print(f"docs://list ->\n  {listing.contents[0].text}")

            doc = await session.read_resource("docs://file/architecture.md")
            print(f"\ndocs://file/architecture.md (first 120 chars) ->\n  {doc.contents[0].text[:120]}...")

            print("\n--- Running the approved conversion operation as a TOOL call ---")
            result = await session.call_tool(
                "convert_markdown_to_text", {"filename": "architecture.md"}
            )
            converted = result.content[0].text
            print(f"convert_markdown_to_text('architecture.md') ->\n{converted}")

            print("\n--- Calling it on a file that doesn't exist, to see the failure mode ---")
            missing = await session.call_tool(
                "convert_markdown_to_text", {"filename": "does-not-exist.md"}
            )
            print(f"convert_markdown_to_text('does-not-exist.md') -> {missing.content[0].text!r}")

    print("""
📝 Takeaway: everything above ran against the SAME server.py a
production client would eventually connect to — nothing here is mocked.
This is exactly the kind of pass a team should run (scripted, or
interactively via MCP Inspector — see the README) before pointing a real
client at a new MCP server: confirm the resource/tool split is right,
confirm discovery lists what you expect, and confirm at least one
failure mode (a missing file) doesn't crash the server.
""")


if __name__ == "__main__":
    asyncio.run(main())
