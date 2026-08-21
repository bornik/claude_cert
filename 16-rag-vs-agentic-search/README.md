# Module 16 — Classical RAG vs. Agentic Search

Both approaches exist to solve the same problem: a model can't have your
whole library in context on every request without the request (and its
cost) growing as the library grows. They differ in **when** the
retrieval work happens — before the model is ever called, or live,
decided by the model itself. This module is one script that runs the
identical question through both.

## Files

```
16-rag-vs-agentic-search/
├── README.md
└── 1_classical_rag_vs_agentic_search.py
```

### 1️⃣ `1_classical_rag_vs_agentic_search.py`

```bash
uv run 16-rag-vs-agentic-search/1_classical_rag_vs_agentic_search.py
```

**What it does:** builds a small 6-document knowledge base (refund
policy, shipping policy, password reset, etc.), then answers "How long
do customers have to request a refund?" two ways:

1. **Classical RAG** — `build_vector_index()` embeds every document
   *before* the question exists; `retrieve()` embeds the query and
   ranks documents by cosine similarity; only the top-2 chunks are ever
   sent to the model.
2. **Agentic search** — the model gets `search_docs` and `read_doc`
   tools and runs the same tool-use loop shape as
   [`04-tool-use-schema-design/1_simple_loop.py`](../04-tool-use-schema-design/1_simple_loop.py),
   deciding for itself, live, what to look up. Nothing about the corpus
   is touched until the model asks.

Both then repeat the same question after padding the corpus to 26
documents with 20 irrelevant "noise" docs, to make the flat-cost claim
concrete: watch the input token count in each run's usage line barely
move despite the corpus growing 4.3x.

**A deliberate simplification, called out in the script's docstring:**
Anthropic doesn't serve an embedding model (production RAG typically
uses something like Voyage AI), so `embed()` is a small hashed-bag-of-
words vectorizer written in plain Python instead — no new dependency,
no API key. It only catches literal word overlap, not real semantic
similarity, which is why the query above shares words with the refund
doc on purpose. The **pipeline** it demonstrates — chunk, embed, store,
retrieve by similarity, only then call the model — is the real
mechanism; the vector quality is not the point of this demo.

**Key concepts:**
- Classical RAG's indexing (`build_vector_index`) happens once, up
  front, independent of whether a given document is ever queried —
  that cost is paid whether or not it pays off. Agentic search pays
  nothing upfront; the cost shows up per-query instead, as extra model
  round trips (one per tool call) while it figures out what to read.
- Both demos cap what reaches the model regardless of corpus size:
  classical RAG by taking a fixed top-`k` from the similarity ranking,
  agentic search by having `search_docs` return at most 3 snippets. The
  flat-cost property isn't unique to either strategy — it comes from
  capping what gets returned, achieved by a precomputed index in one
  case and a live search function in the other.
- Agentic search costs more *per query* here (roughly 2,400 input
  tokens across a 2-round trip loop, vs. ~160 for classical RAG's single
  call) — the tradeoff is upfront indexing effort vs. runtime round
  trips, not "one is cheaper than the other" in general. Classical RAG
  wins when the same corpus gets queried many times; agentic search
  wins when the corpus changes too often to justify re-indexing, or
  when there's no way to know what to index ahead of time.
- `_search_docs()` scores by naive keyword overlap **computed at call
  time**, on purpose — nothing about the corpus was touched before the
  question arrived, in contrast to `build_vector_index()`'s upfront
  work. The realism gap here runs the other way from `embed()`: a
  production agentic-search tool would usually be a real search engine
  or grep-like tool, not a toy keyword counter, but the "no pre-
  processing, decided live" shape is exactly the real mechanism.

## How this generalizes: Claude Code's own Tool Search

Claude Code faces the identical problem with **tool definitions**
instead of documents: loading every connected MCP server's full tool
schemas on every turn would bloat context the same way loading every
document would. Its default behavior is agentic search applied to
tools rather than text:

- **Startup:** only tool *names* and each server's general instructions
  load — the heavy, full-text schema definitions are deferred.
- **Per task:** Claude uses a built-in search step (`ToolSearch`) to
  find which tools match the current intent; only the schemas for tools
  it actually decides to invoke enter context.
- **Result:** you can connect dozens of MCP servers without paying a
  context penalty on every single turn, the same flat-cost property
  `search_docs` demonstrates above, applied to tool schemas instead of
  document chunks.

This is a Claude Code CLI mechanic, not something this repo's API
scripts can toggle — the closest **API-level** analog is the MCP
Connector's `defer_loading` and per-tool `enabled` flags, already
covered in
[`04-tool-use-schema-design/7_mcp_connector.py`](../04-tool-use-schema-design/7_mcp_connector.py):
that script's `show_context_cost_controls()` demo is doing by hand, per
tool, roughly what Claude Code's Tool Search automates across an entire
connected server.

## What's *not* re-demonstrated here

- **A real embedding model / vector database** (Voyage AI, Pinecone,
  pgvector, etc.) — out of scope for a dependency-free script; the
  pipeline shape is what's being taught, not a specific vendor's SDK.
- **The MCP Connector's context-cost controls** — already covered in
  [`04-tool-use-schema-design/7_mcp_connector.py`](../04-tool-use-schema-design/7_mcp_connector.py),
  referenced above rather than repeated.
