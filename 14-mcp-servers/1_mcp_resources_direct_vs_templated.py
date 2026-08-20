"""
EXAMPLE 1: MCP Resources — Direct vs. Templated

An MCP server can expose three kinds of things: tools (what every other
example in this repo uses), prompts, and resources. This module's README
flagged resources as "documented in the lesson text rather than faked" —
because Claude Code's own @-mention resource loading isn't something this
repo's CLI setup can reliably script. But the resource *mechanism itself*
is just MCP protocol, so we can demonstrate it directly with the `mcp`
Python SDK, no CLI or Claude Code session involved at all.

Resources are read-only data a client fetches directly by address and
drops into context — no model turn spent deciding to call a tool, no
tool_result round-trip. There are two shapes of address:

- DIRECT resource: a fixed address, no parameters. You know the whole
  path up front (e.g. `docs://list`). The server returns the same
  well-defined data every time.
- TEMPLATED resource: the address has a `{placeholder}` in it (e.g.
  `docs://file/{document_id}`). The client fills in the placeholder at
  request time to reach one of many possible items.

This script builds one tiny MCP server with one of each, connects an
in-memory client session directly to it (`mcp.shared.memory` — no
subprocess, no stdio pipe, nothing OS-specific), and shows:
1. `list_resources()` only ever returns the DIRECT resource
2. `list_resource_templates()` only ever returns the TEMPLATED one —
   they're reported through two different endpoints, not one
3. Reading the direct resource needs no argument; reading the templated
   one means substituting a real id into the placeholder

Exam-relevant point this makes concrete: whether a client actually
surfaces resources to the model (e.g. via `@server:resource://uri`
mentions) is a CLIENT capability, not something the server can force —
always check client support before designing around it.
"""

import asyncio
import logging
import warnings

from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

# The SDK logs "Processing request of type ..." at INFO for every call and
# a pydantic_settings warning fires on import — neither is relevant to the
# resource concept this example demonstrates, so both are silenced.
logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

mcp = FastMCP("resource-demo")

DOCS = {
    "readme": "Project README: run `uv run <script>.py` for any example.",
    "changelog": "v0.1.0 - initial release",
}


# A DIRECT resource: `docs://list` is a fixed address — no braces, no
# parameters. Every client that reads it gets the exact same thing back.
@mcp.resource("docs://list")
def list_docs() -> str:
    """Fixed list of available document ids. A direct resource."""
    return "\n".join(DOCS.keys())


# A TEMPLATED resource: `{document_id}` is a placeholder the client fills
# in per request. One template, many possible addresses.
@mcp.resource("docs://file/{document_id}")
def get_doc(document_id: str) -> str:
    """One document's content, addressed by id. A templated resource."""
    return DOCS.get(document_id, f"no such document: {document_id}")


async def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: MCP Resources — Direct vs. Templated")
    print("=" * 70)

    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        direct = await session.list_resources()
        print("\n📌 DIRECT resources (fixed address, no parameters):")
        for r in direct.resources:
            print(f"   {r.uri}")

        templated = await session.list_resource_templates()
        print("\n🧩 TEMPLATED resources (address has a {placeholder}):")
        for t in templated.resourceTemplates:
            print(f"   {t.uriTemplate}")

        print("\n--- Reading the direct resource: no argument needed ---")
        result = await session.read_resource("docs://list")
        print(f"📖 docs://list ->\n   {result.contents[0].text}")

        print("\n--- Reading the templated resource: substitute the placeholder ---")
        for document_id in ["readme", "changelog", "missing"]:
            result = await session.read_resource(f"docs://file/{document_id}")
            print(f"📖 docs://file/{document_id} -> {result.contents[0].text}")

    print("""
📝 Takeaway: `list_resources()` and `list_resource_templates()` are two
separate endpoints in the protocol — a resource is either direct or
templated, never listed as both. Direct resources are cheap and fast to
pull into context up front because there's nothing to decide: one fixed
address, one fixed payload. Templated resources trade that simplicity for
reach — one declared template can address an unbounded number of items,
but the caller (model or client code) has to supply the id, which is
exactly the same shape of decision a tool call requires. Whether your
client actually offers resources to the model at all (e.g. Claude Code's
@-mention attachment) is a client-side feature, not something the server
in this script can guarantee — check client support before you design an
architecture around it.
""")


if __name__ == "__main__":
    asyncio.run(main())
