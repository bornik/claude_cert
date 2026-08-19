# Module 13 — Packaging Workflows

Every other module in this repo is a Python script you `uv run`. This one
is different on purpose: most of this lesson (SKILL.md discovery, plugin
bundling, `/plugin marketplace add`, managed-settings precedence) is a
Claude Code **CLI** mechanic, not an Anthropic API concept — there's no
Messages API call that installs a plugin. So this module is a hands-on
CLI walkthrough (build a real skill → plugin → local marketplace →
install it) plus one script for the one piece that genuinely is new
API/SDK surface: the Agent SDK's `setting_sources` control.

## Requirements

The CLI walkthrough below needs the **Claude Code CLI itself**, run from
inside this repo — not just `uv run`. Everything else in this repo only
needs the Python environment.

## Files

### 🧩 `packaging-demo/` — a real, minimal plugin
```
packaging-demo/
├── .claude-plugin/plugin.json           ← manifest: {name, description}
├── skills/
│   ├── changelog-format/SKILL.md        ← auto-invoked (description match)
│   └── release-checklist/SKILL.md       ← disable-model-invocation: true
└── hooks/hooks.json                     ← PreToolUse → echo
```
**What:** `changelog-format` is the same skill from
[`09-memory/3_skills_on_demand_vs_always_on.py`](../09-memory/3_skills_on_demand_vs_always_on.py),
but this time a real `SKILL.md` file Claude Code discovers and
auto-invokes by matching your request against its `description` —
module 09 only *simulated* that matcher with a hand-rolled MATCH/NOMATCH
classifier call; here the real mechanism does the matching.
`release-checklist` sets `disable-model-invocation: true`, so it can
*never* auto-load no matter how well a request matches its description —
it only runs when you explicitly type `/packaging-demo:release-checklist`.
The `hooks/hooks.json` bundles a harmless `PreToolUse` hook so installing
the plugin has an observable, non-destructive side effect.

**Key concepts:**
- Skills are auto-discovered from `skills/<skill-name>/SKILL.md` at the
  plugin root — no explicit reference needed in `plugin.json`
- `disable-model-invocation: true` is the current way to make a skill
  explicit-invocation-only — this is what replaces the legacy
  `.claude/commands/*.md` format for a "predictable, explicit entry point"
- The plugin's name becomes the command namespace prefix:
  `packaging-demo` + `release-checklist` → `/packaging-demo:release-checklist`.
  This is why two plugins can each ship a same-named skill without
  colliding, and why renaming a plugin renames every command it exposes
- Hooks bundled in a plugin (`hooks/hooks.json`) use the exact same
  schema as `.claude/settings.json`'s `hooks` key
- A deny rule or guardrail hook you rely on locally is **not** carried
  into a plugin install unless you explicitly bundle it — the plugin only
  ships what's actually in its directory

### 🏪 `local-marketplace/` — a catalog with one local plugin
```
local-marketplace/
└── .claude-plugin/marketplace.json      ← lists packaging-demo via "../packaging-demo"
```
**What:** A marketplace is just a `.claude-plugin/marketplace.json`
catalog. This one points at `packaging-demo/` with a relative path
(`source: "../packaging-demo"`), so no git remote is needed to try the
real install flow.

### Try it — the CLI walkthrough
Run these from the repo root, in your own Claude Code session:

```bash
/plugin marketplace add ./13-packaging-workflows/local-marketplace
/plugin install packaging-demo@packaging-workflows-demo-marketplace
```
1. Ask something changelog-shaped ("write a changelog entry for fixing
   the login redirect bug") → `changelog-format` auto-invokes; compare
   the output's exact shape (bracketed component, no period,
   `(user-facing)` suffix) against a request with the plugin *not*
   installed.
2. Run `/packaging-demo:release-checklist` → the explicit-only skill
   fires. It will **not** fire on its own no matter how release-shaped
   your question is — that's the point of `disable-model-invocation`.
3. Use any tool (e.g. ask Claude to read a file) → watch for the
   `[packaging-demo hook] PreToolUse fired` line, proving the bundled
   hook installed and ran alongside your normal tool use.
4. Clean up:
   ```bash
   /plugin uninstall packaging-demo@packaging-workflows-demo-marketplace
   /plugin marketplace remove packaging-workflows-demo-marketplace
   ```

### 1️⃣ `1_agent_sdk_setting_sources.py` — Does the SDK See Your Project's Skills?
**What:** Drives the same changelog request through `claude_agent_sdk.query()`
three times against a self-contained fixture project
(`sdk_fixture/.claude/skills/changelog-format/SKILL.md`), changing only
`setting_sources`: omitted (`None`), `[]`, and `["project"]`.

**Key concepts:**
- `setting_sources=None` (the default — simply omitting it) loads every
  filesystem source, matching the interactive CLI's own defaults; this is
  **not** an opt-in, it's what happens if you say nothing
- `setting_sources=[]` is SDK isolation mode — no `.claude/` directory
  loads from anywhere, so a project's Skills, CLAUDE.md, and
  `settings.json` all become invisible regardless of how well a
  description would have matched
- `setting_sources=["project"]` is the minimum needed to load project-level
  Skills — and per the SDK's own docstring, `"project"` must be present
  for CLAUDE.md to load too
- Live result: the default and `["project"]` runs both produced the
  skill's exact format (bracketed component tag, no trailing period,
  `(user-facing)` suffix); the `[]` run fell back to a generic changelog
  entry with none of that
- This is a different failure mode than Module 09's subagent case —
  there, a Skill the *parent* loaded didn't automatically carry over to a
  delegated call. Here, nothing "loaded" in the parent sense at all; the
  SDK simply never reads the filesystem unless told to

```bash
uv run 13-packaging-workflows/1_agent_sdk_setting_sources.py
```

## What's *not* re-demonstrated here

- **Messages API's Agent Skills** (`container={"skills": [...]}` +
  code-execution + beta headers) — already covered live in
  [`09-memory/3_skills_on_demand_vs_always_on.py`](../09-memory/3_skills_on_demand_vs_always_on.py)'s
  `demo_real_agent_skills()`.
- **Managed Agents' skill attachment** — skills are attached when you
  *define* the agent resource (the same one-time `POST /v1/agents` call
  covered in [`12-managed-agents`](../12-managed-agents/)), just with a
  `skills` field added. Not re-demonstrated separately since it's the
  identical call, not a new mechanism.
- **Managed-settings precedence** (`extraKnownMarketplaces`, a marketplace
  allowlist gating which sources users may add) is enterprise-MDM-only —
  there's no local way to exercise it honestly, so it's documented here,
  not faked: managed settings sit above user and project settings in the
  configuration hierarchy, so a plugin deployed at managed scope can't be
  overridden by a user or a project file. The allowlist alone only
  restricts what a user can add; pairing it with `extraKnownMarketplaces`
  is what pushes a marketplace to everyone without requiring them to run
  the add command themselves.
