# Module 14 — MCP Servers & Access Auditing

Like [module 13](../13-packaging-workflows/), most of this lesson is a
Claude Code **CLI** mechanic, not an Anthropic API concept — connecting an
MCP server, choosing its scope, and writing permission rules all happen in
CLI config, not in a `messages.create()` call. The one piece that *is* API
surface (the API's MCP Connector: `mcp_toolset`, `defer_loading`, per-tool
`enabled`) is already covered live in
[`04-tool-use-schema-design/7_mcp_connector.py`](../04-tool-use-schema-design/7_mcp_connector.py)
and isn't re-demonstrated here. This module is a hands-on CLI walkthrough
in two parts: connecting a real MCP server (transport + scope), and a
`PostToolUse` hook that deterministically audits every tool call —
including calls the server from part 1 makes.

## Requirements

The Claude Code CLI itself, run from inside this repo. Part 1 uses
DeepWiki, the same public, no-auth remote MCP server used in module 04's
script — no account needed. The optional GitHub MCP step needs a GitHub
account and a Personal Access Token; skip it if you don't want to set one
up, the config pattern is the point, not the live call.

## Files

```
14-mcp-servers/
├── README.md
├── access-audit-demo/                   ← a real, minimal plugin
│   ├── .claude-plugin/plugin.json
│   └── hooks/
│       ├── hooks.json                   ← PostToolUse, matcher "*"
│       └── log_tool_call.py             ← appends one JSON line per tool call
└── local-marketplace/
    └── .claude-plugin/marketplace.json  ← lists access-audit-demo via "../access-audit-demo"
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
- **Resources and prompts** — the other two things an MCP server can
  expose besides tools. Resource-injection support varies by client and
  isn't something this repo's CLI setup can reliably demo, so it's
  documented in the lesson text rather than faked here.
