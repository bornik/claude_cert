"""
docs-server/server.py — a real stdio MCP server for local engineering docs.

This is the server half of module 14's example 2. Run it standalone and
it does nothing visible — it just sits waiting for JSON-RPC messages on
stdin. That's what "local stdio transport" actually means: a subprocess
your client launches and talks to over stdin/stdout, not a network
listener you'd curl. It's the right transport here because these
documents live on the same machine as whoever's running Claude — there's
no remote service to reach.

Exposes exactly the split the exam scenario calls for:
  - Documents as RESOURCES (docs://list, docs://file/{filename}) — read-
    only data a client pulls into context directly. Claude should be
    reading these, not deciding whether to "fetch" them via a tool call.
  - One TOOL (convert_markdown_to_text) for the approved conversion
    operation — an action with a real effect (producing a new
    representation of the doc), which is what tools are for. It never
    writes back to disk; it returns the converted text.

Test this server two ways before any production client ever touches it:
  1. Scripted:    uv run 14-mcp-servers/2_stdio_docs_server_test_client.py
  2. Interactive: npx @modelcontextprotocol/inspector uv run 14-mcp-servers/docs-server/server.py
     (see the module README for the full MCP Inspector walkthrough)
"""

import logging
import re
import warnings
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Same reasoning as 1_mcp_resources_direct_vs_templated.py: the SDK logs
# "Processing request of type ..." at INFO for every call, and a
# pydantic_settings warning fires on import. This runs as its OWN process
# (launched over stdio), so it needs its own suppression — the parent
# script's logging config doesn't reach a child process.
logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

DOCS_DIR = Path(__file__).resolve().parent / "docs"

mcp = FastMCP("docs-server")


@mcp.resource("docs://list")
def list_docs() -> str:
    """Every local engineering document available, by filename. A direct
    resource — fixed address, no parameters."""
    return "\n".join(p.name for p in sorted(DOCS_DIR.glob("*.md")))


@mcp.resource("docs://file/{filename}")
def read_doc(filename: str) -> str:
    """One document's raw Markdown, addressed by filename. A templated
    resource — the caller supplies which file."""
    path = DOCS_DIR / filename
    if not path.is_file():
        return f"no such document: {filename}"
    return path.read_text()


_MD_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_MD_HEADER = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_MD_BOLD_ITALIC = re.compile(r"(\*\*|__|\*|_)(.+?)\1")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_INLINE_CODE = re.compile(r"`([^`]+)`")


@mcp.tool()
def convert_markdown_to_text(filename: str) -> str:
    """Convert one local document from Markdown to plain text. This is
    the approved conversion operation this server exposes: it strips
    headers, bold/italic markers, code fences, and inline code, and
    turns links into their link text. Read-only — it never modifies the
    source file on disk, only returns the converted string."""
    path = DOCS_DIR / filename
    if not path.is_file():
        return f"no such document: {filename}"
    text = path.read_text()
    text = _MD_CODE_FENCE.sub("", text)
    text = _MD_HEADER.sub("", text)
    text = _MD_BOLD_ITALIC.sub(r"\2", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_INLINE_CODE.sub(r"\1", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


if __name__ == "__main__":
    mcp.run()  # defaults to stdio transport
