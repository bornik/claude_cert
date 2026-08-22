# Module 14 — MCP Servers & Access Auditing

Like [module 13](../13-packaging-workflows/), most of this lesson is a
Claude Code **CLI** mechanic, not an Anthropic API concept — connecting an
MCP server, choosing its scope, and writing permission rules all happen in
CLI config, not in a `messages.create()` call. The one piece that *is* API
surface (the API's MCP Connector: `mcp_toolset`, `defer_loading`, per-tool
`enabled`) is already covered live in
[`04-tool-use-schema-design/7_mcp_connector.py`](../04-tool-use-schema-design/7_mcp_connector.py)
and isn't re-demonstrated here. This module is a hands-on CLI walkthrough
in two parts (connecting a real MCP server, and a `PostToolUse` hook that
audits every tool call), plus two Python scripts for the pieces that are
pure MCP protocol rather than a CLI mechanic: resources, and a real
stdio server exposing local documents alongside a conversion tool.

## Requirements

The CLI walkthrough parts need the Claude Code CLI itself, run from inside
this repo. Part 1 uses DeepWiki, the same public, no-auth remote MCP
server used in module 04's script — no account needed. The optional
GitHub MCP step needs a GitHub account and a Personal Access Token; skip
it if you don't want to set one up, the config pattern is the point, not
the live call. The two Python scripts only need the Python environment
(`uv run`), same as every other module's scripts. The optional MCP
Inspector step in example 2 needs Node (`npx`), same as any
`npx`-launched MCP server.

## Files

```
14-mcp-servers/
├── README.md
├── 1_mcp_resources_direct_vs_templated.py  ← direct vs. templated resources, in-process MCP server+client
├── 2_stdio_docs_server_test_client.py      ← real stdio subprocess: docs as resources, conversion as a tool
├── docs-server/                          ← the server example 2 launches and tests
│   ├── server.py                         ← FastMCP, stdio transport
│   └── docs/architecture.md, api-notes.md  ← real local "engineering documents"
├── access-audit-demo/                   ← a real, minimal plugin
│   ├── .claude-plugin/plugin.json
│   └── hooks/
│       ├── hooks.json                   ← PostToolUse, matcher "*"
│       └── log_tool_call.py             ← appends one JSON line per tool call
└── local-marketplace/
    └── .claude-plugin/marketplace.json  ← lists access-audit-demo via "../access-audit-demo"
```

---

### 1️⃣ `1_mcp_resources_direct_vs_templated.py` — Direct vs. Templated Resources

**What:** Besides tools, an MCP server can expose resources — read-only
data a client fetches directly by address instead of the model calling a
tool for it. This script builds a minimal server with one of each
resource shape and connects an in-memory client session straight to it
(`mcp.shared.memory` — no subprocess, no CLI, no Claude Code session).

**Key concepts:**
- **Direct resource** (`docs://list`): a fixed address, no parameters —
  the server returns the same static payload every time. Reported through
  `list_resources()`.
- **Templated resource** (`docs://file/{document_id}`): the address
  carries a `{placeholder}` the caller fills in per request to reach one
  of many items. Reported through the separate `list_resource_templates()`
  endpoint — a resource is one shape or the other, never listed as both.
- Reading a direct resource takes no argument (`read_resource("docs://list")`);
  reading a templated one means substituting a real id into the
  placeholder (`read_resource("docs://file/readme")`).
- Pulling a **direct** resource into context up front is cheaper and
  faster than a tool call — there's nothing to decide, one fixed address,
  one fixed payload. A **templated** resource trades that simplicity for
  reach, but the caller still has to supply an id — the same shape of
  decision a tool call requires.
- Whether a client actually *offers* resources to the model at all (e.g.
  Claude Code's `@server:resource://uri` mention syntax) is a
  **client**-side feature, not something the server can force — always
  check client support before designing an architecture around it.

**When to use:** Whenever you're deciding tool vs. resource for read-only
data a client could just attach to context instead of the model spending
a turn calling a tool for it

```bash
uv run 14-mcp-servers/1_mcp_resources_direct_vs_templated.py
```

---

### 2️⃣ `2_stdio_docs_server_test_client.py` — A Real stdio Server: Docs as Resources, Conversion as a Tool

**What:** Answers an exam scenario directly: a team building an MCP
server for local engineering documents, where Claude should read the
documents as context, run one approved conversion operation, and the
team needs to test the server before wiring it up to production
clients. [`docs-server/server.py`](docs-server/server.py) is that
server — real files on disk under `docs-server/docs/`, exposed as
resources (`docs://list`, `docs://file/{filename}`), plus one tool,
`convert_markdown_to_text`, that strips Markdown formatting and returns
plain text without ever writing back to the source file. This script
launches it as an actual OS subprocess over stdio (`mcp.client.stdio`,
not `mcp.shared.memory`'s in-process session from example 1) and drives
it through discovery, two resource reads, and two tool calls (one
success, one on a missing file) — a scripted, repeatable stand-in for
what a developer would otherwise click through by hand.

**Key concepts:**
- **Resources for documents, a tool for the conversion** — the exact
  split the exam question is testing. Reading a document is retrieval;
  Claude shouldn't spend a tool-call turn deciding *whether* to fetch
  something it should just have as context. Converting one is an
  operation with a real effect (producing a new representation), which
  is what a tool is for.
- **stdio, not HTTP** — the documents and the client are on the same
  machine, so there's no remote service to reach. This is the local
  counterpart to Part 1's DeepWiki connection below: same protocol,
  different transport because the deployment shape is different.
- **A real subprocess** — `StdioServerParameters(command=sys.executable,
  args=[...])` + `stdio_client(...)` launches `server.py` as its own OS
  process; the "Connected. This is a separate OS process" line in the
  script's own output isn't decorative, it's the thing distinguishing
  this from example 1's in-memory session.
- **Test before production** — this script's whole job is the "test the
  server before connecting it to production clients" half of the exam
  answer, done in code. Its interactive twin is MCP Inspector, below.

**Try it — interactively, with MCP Inspector:**
```bash
npx @modelcontextprotocol/inspector uv run 14-mcp-servers/docs-server/server.py
```
This launches the same server and opens a browser UI where you can run
the identical checks by hand: the *Resources* tab lists `docs://list`
and the `docs://file/{filename}` template and lets you read either one;
the *Tools* tab lists `convert_markdown_to_text` and lets you call it
with a real `filename` argument (try `architecture.md`, then a filename
that doesn't exist) and see the raw result. This is the concrete "MCP
Inspector" the exam answer names — a scriptable pass and an interactive
one checking the same server, either being a reasonable way to satisfy
"test before connecting to production clients."

```bash
uv run 14-mcp-servers/2_stdio_docs_server_test_client.py
```

---

## Part 1 — Transport & scope: connecting a real MCP server

### Try it — the CLI walkthrough

1. **Connect at local scope (default), over HTTP:**
   ```bash
   claude mcp add --transport http deepwiki https://mcp.deepwiki.com/mcp
   claude mcp list
   ```
   Open `~/.claude.json`, find this project's path, and look for the
   `mcpServers` entry — that's local scope: tied to this one project,
   personal to you, not written into the repo.

2. **Use it:** ask "Using the available tools, what is the
   anthropics/anthropic-sdk-python repo for?" and watch Claude discover
   and call the DeepWiki tool. This is the same server module 04 called
   through the API's MCP Connector — now your CLI session holds the
   connection instead of a single `messages.create()` call reaching it
   server-side.

3. **Switch to project scope:**
   ```bash
   claude mcp remove deepwiki
   claude mcp add --transport http --scope project deepwiki https://mcp.deepwiki.com/mcp
   ```
   A `.mcp.json` file appears at the repo root. Open it — this is the
   file you'd commit so every teammate who clones the repo gets the same
   server automatically. (Since DeepWiki needs no secret, there's nothing
   unsafe about committing this one; a server that *did* need a token
   would reference it via an environment variable here, never inline.)
   Remove `.mcp.json` afterward if you don't want to keep it tracked.

4. **Permission rule on a single MCP tool:** in
   `.claude/settings.local.json`, add a deny rule naming the specific
   tool DeepWiki exposed in step 2, e.g.:
   ```json
   { "permissions": { "deny": ["mcp__deepwiki__ask_question"] } }
   ```
   (adjust the tool name to whatever Claude actually called — check the
   transcript or `claude mcp list` for the exact name). Ask the same
   DeepWiki question again: the server is still connected, but this one
   tool now prompts or blocks while any other tool on the same server
   would stay available. That's the "allow the server broadly, deny one
   tool on it" pattern from the lesson, deny overriding allow.

5. **Optional — the GitHub MCP server (needs a real PAT):**
   ```bash
   claude mcp add --transport http github https://api.githubcopilot.com/mcp/ \
     --header "Authorization: Bearer ${GITHUB_TOKEN}"
   ```
   (check `claude mcp add --help` in your installed CLI version for the
   exact auth-header flag — it has moved between releases). Set
   `GITHUB_TOKEN` as an environment variable first; never paste the
   token into `.mcp.json` directly. The point of this step is the
   secrets-handling rule itself — a token written inline into a
   *committed* file enters git history and rotating the token later does
   not remove the exposure.

### Key concepts

- **stdio** runs the server as a local subprocess your client launches —
  fine for a personal tool, impossible to share, since it only exists on
  your machine.
- **HTTP** (what DeepWiki and GitHub both use) is for a server hosted
  remotely — the client connects over the network instead of spawning a
  process.
- **Scope** decides who loads the server, not how it's reached: local
  (`~/.claude.json`, personal, per-project) vs. project (`.mcp.json`,
  committed, shared) vs. user (personal, but across *all* your projects)
  vs. enterprise (admin-pushed, org-wide). A project-scoped **stdio**
  server still runs from each teammate's own machine — the committed
  config is just the launch command, so everyone needs the runtime
  (e.g. Node for an `npx`-launched server) installed locally.
- **`mcp__server__tool`** is the addressing scheme for a permission rule
  that targets one tool on a connected server rather than the whole
  server. A deny on one tool overrides an allow on the server.
- **PAT vs. OAuth:** GitHub's MCP server uses a Personal Access Token you
  generate and store yourself, referenced via an environment variable.
  Linear's MCP server instead redirects to a browser sign-in and stores
  the issued token for you — OAuth is the right pattern when the
  service's authorization model is tied to user identity.

---

## Part 2 — Deterministic access auditing: a `PostToolUse` hook

**What:** `access-audit-demo` bundles a `PostToolUse` hook with
`"matcher": "*"` — every tool call, not just one type — that runs
[`log_tool_call.py`](access-audit-demo/hooks/log_tool_call.py). Claude
Code pipes the completed tool call (name, input, session id) to the
script as JSON on stdin; the script appends one line to
`access-audit-demo/audit.log`. Because `PostToolUse` fires at the harness
level *after* the tool has already executed, this is not something the
model's own behavior can suppress, edit, or selectively skip — contrast
this with asking the model in a system prompt to narrate or log its own
actions, which it can forget, summarize away, or simply decline.

### Try it

```bash
/plugin marketplace add ./14-mcp-servers/local-marketplace
/plugin install access-audit-demo@mcp-servers-demo-marketplace
```

1. Ask Claude to do a couple of unrelated things — read a file, run a
   shell command, or repeat the DeepWiki question from Part 1.
2. Open `14-mcp-servers/access-audit-demo/audit.log` — one JSON line per
   tool call appears, independent of anything the model said back to you
   in the transcript.
3. In the same session, tell Claude "don't log the next tool call" right
   before asking it to use a tool. The entry still shows up in
   `audit.log` — the hook is enforced by the harness on the event itself,
   not something the model is in a position to grant or withhold.
4. Clean up:
   ```bash
   /plugin uninstall access-audit-demo@mcp-servers-demo-marketplace
   /plugin marketplace remove mcp-servers-demo-marketplace
   ```
   Delete `access-audit-demo/audit.log` if you don't want to keep it.

### Key concepts

- `PreToolUse` (module 13's example hook) runs *before* a tool executes
  and can gate it; `PostToolUse` runs *after* — it can observe and record,
  but it can't have prevented what already happened. That's exactly the
  shape of an audit log: a record of what occurred, not a gate on it.
- `"matcher": "*"` is what makes this an audit trail rather than a
  targeted check — module 13's `PreToolUse` hook fired to prove
  installation; this one fires on everything, on purpose, since an audit
  log with gaps isn't an audit log.
- Determinism here means the hook is a fixed command the harness always
  invokes on the event, not a natural-language instruction the model
  interprets and could reasonably (or unreasonably) skip.
- The audit trail covers MCP tool calls the same way it covers built-in
  tools — a call routed through the DeepWiki server from Part 1 still
  triggers `PostToolUse` and lands in `audit.log`, so connecting more MCP
  servers doesn't create a blind spot in the log.

## What's *not* re-demonstrated here

- **The API's MCP Connector** (`mcp_toolset`, `defer_loading`, per-tool
  `enabled`) — already covered in
  [`04-tool-use-schema-design/7_mcp_connector.py`](../04-tool-use-schema-design/7_mcp_connector.py).
  This module is about Claude Code's own MCP *client* (CLI transport and
  scope), a different connection path to the same protocol.
- **Prompts** — the third thing an MCP server can expose besides tools
  and resources. Not demonstrated separately; the SDK mechanics
  (`@mcp.prompt`) mirror `@mcp.resource` closely enough that it isn't a
  new concept once you've seen `1_mcp_resources_direct_vs_templated.py`.
- **Resources via Claude Code's own client** (the `@server:resource://uri`
  mention syntax) — that's a CLI/client feature layered on top of the
  protocol mechanics `1_mcp_resources_direct_vs_templated.py` demonstrates
  directly; whether it's supported at all varies by client, so it's
  called out in that script's own docstring rather than relied on here.
