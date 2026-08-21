"""
EXAMPLE 1: Classical RAG vs. Agentic Search — same question, two retrieval
strategies, both built to keep the model's context flat as the corpus grows.

Both approaches solve the same problem: a model can't read your whole
library on every request without the request growing (and costing more)
as the library grows. They differ in WHEN they do the retrieval work:

  CLASSICAL RAG — retrieval happens BEFORE the model is ever called.
    1. Every doc is split into chunks and converted to an embedding
       (a vector of numbers capturing its meaning) ahead of time, and
       stored in a vector "database".
    2. At query time, the query itself is embedded the same way, matched
       by similarity against the stored vectors, and only the best-
       matching chunk(s) are handed to the model.
    This script stands in for a real embedding model (Anthropic doesn't
    serve one; production RAG typically uses something like Voyage AI)
    with a small hashed-bag-of-words vectorizer, implemented in plain
    Python below. The MECHANISM — chunk, embed, store, retrieve by
    similarity — is the real thing; the vector math is a simplification
    to keep this script dependency-free.

  AGENTIC SEARCH — retrieval happens AT query time, decided by the model.
    No index exists ahead of time. The model gets a `search_docs` tool
    and a `read_doc` tool and decides for itself, per question, what to
    look up — potentially several tool calls deep. This is exactly what
    Claude Code's own Tool Search does with MCP tool definitions instead
    of documents: tool names and server instructions load at startup,
    full schemas are deferred, and a search step loads only what a given
    task actually needs. See the README for how the two map onto each
    other.

Both demos run the SAME query against the SAME six-document knowledge
base, then again after padding the corpus with 20 irrelevant "noise"
documents, to make the flat-cost claim concrete rather than theoretical.
"""

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5"

KNOWLEDGE_BASE = [
    {
        "id": "refunds",
        "title": "Refund Policy",
        "text": (
            "Customers may request a full refund within 30 days of "
            "purchase, provided the item is unused and in its original "
            "packaging. Refunds are issued to the original payment "
            "method within 5-7 business days of approval. Digital "
            "goods are non-refundable once downloaded."
        ),
    },
    {
        "id": "shipping",
        "title": "Shipping Policy",
        "text": (
            "Standard shipping takes 5-8 business days within the "
            "continental US. Expedited shipping (2-3 business days) is "
            "available at checkout for an additional fee. We do not "
            "currently ship internationally."
        ),
    },
    {
        "id": "password-reset",
        "title": "Password Reset Procedure",
        "text": (
            "Users can reset their password from the login screen by "
            "selecting 'Forgot password'. A reset link is emailed and "
            "expires after 1 hour. Support agents can never see or "
            "reset a password directly; they can only trigger a new "
            "reset email."
        ),
    },
    {
        "id": "data-retention",
        "title": "Data Retention Policy",
        "text": (
            "Account data is retained for 90 days after account "
            "deletion to allow for recovery, then permanently purged. "
            "Billing records are retained for 7 years to satisfy tax "
            "and audit requirements, independent of account status."
        ),
    },
    {
        "id": "rate-limits",
        "title": "API Rate Limits",
        "text": (
            "The public API allows 100 requests per minute per API key "
            "on the free tier, and 1,000 requests per minute on paid "
            "tiers. Exceeding the limit returns a 429 status code with "
            "a Retry-After header indicating the wait time."
        ),
    },
    {
        "id": "on-call",
        "title": "On-Call Escalation Policy",
        "text": (
            "Primary on-call engineers must acknowledge a page within "
            "10 minutes. If unacknowledged, the page escalates to the "
            "secondary on-call, then to the engineering manager after "
            "another 10 minutes."
        ),
    },
]

# Unrelated filler documents used to pad the corpus for the scaling demo —
# distinct enough in topic that they should never win the similarity
# search or get pulled by the agentic search tool for our test query.
_NOISE_TOPICS = [
    ("Coffee Brewing", "Pour-over coffee extracts best with water just off "
     "the boil, around 200F, poured in slow concentric circles."),
    ("Houseplant Care", "Most tropical houseplants prefer bright, indirect "
     "light and should dry out between waterings to avoid root rot."),
    ("Bicycle Maintenance", "Chain lubrication should happen roughly every "
     "100-150 miles of riding, wiped clean of excess before it collects grit."),
    ("Sourdough Starter", "A sourdough starter needs daily feeding at room "
     "temperature to stay active, doubling in size within 4-8 hours."),
    ("Marathon Training", "Most training plans peak mileage 3 weeks before "
     "race day, then taper volume while keeping some intensity."),
]


def build_noise_docs(count: int) -> list[dict]:
    docs = []
    for i in range(count):
        title, text = _NOISE_TOPICS[i % len(_NOISE_TOPICS)]
        docs.append({"id": f"noise-{i}", "title": f"{title} (variant {i})", "text": text})
    return docs


# ---------------------------------------------------------------------------
# Classical RAG: a minimal local stand-in for an embedding model + vector DB
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")
VECTOR_DIMS = 128


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def embed(text: str) -> list[float]:
    """A hashed bag-of-words vector, standing in for a real embedding
    model. Real RAG uses a trained model (e.g. Voyage AI) so semantically
    similar words land close together even without sharing exact tokens;
    this hashing trick only catches literal word overlap. The chunk ->
    vector -> similarity-search PIPELINE is the real thing being taught,
    not this particular vector's quality."""
    counts = Counter(_tokenize(text))
    vec = [0.0] * VECTOR_DIMS
    for word, count in counts.items():
        vec[hash(word) % VECTOR_DIMS] += count
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine_sim(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # already L2-normalized


def build_vector_index(docs: list[dict]) -> list[tuple]:
    """The 'upfront indexing' step — done once, before any question exists."""
    return [(doc, embed(doc["text"])) for doc in docs]


def retrieve(query: str, index: list[tuple], k: int = 2) -> list[dict]:
    query_vec = embed(query)
    scored = [(cosine_sim(query_vec, vec), doc) for doc, vec in index]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in scored[:k]]


def demo_classical_rag():
    print("\n" + "=" * 70)
    print("1. Classical RAG — index built upfront, retrieval by similarity")
    print("=" * 70)

    query = "How long do customers have to request a refund?"

    print(f"\nIndexing {len(KNOWLEDGE_BASE)} documents (upfront cost, paid once)...")
    index = build_vector_index(KNOWLEDGE_BASE)

    print(f"Query: {query!r}")
    top_docs = retrieve(query, index, k=2)
    print("Retrieved (by cosine similarity, no model involved yet):")
    for doc in top_docs:
        print(f"  • {doc['title']} ({doc['id']})")

    context = "\n\n".join(f"# {d['title']}\n{d['text']}" for d in top_docs)
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=(
            "Answer only using the provided context. If the answer isn't "
            "in it, say so."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            }
        ],
    )
    print(f"\nAnswer: {response.content[0].text}")
    print_usage(response, model=MODEL)

    print("\n-- Now scaling the corpus to 26 documents (20 irrelevant 'noise' docs) --")
    padded_kb = KNOWLEDGE_BASE + build_noise_docs(20)
    padded_index = build_vector_index(padded_kb)
    padded_top_docs = retrieve(query, padded_index, k=2)
    print("Retrieved from the padded corpus:")
    for doc in padded_top_docs:
        print(f"  • {doc['title']} ({doc['id']})")

    padded_context = "\n\n".join(f"# {d['title']}\n{d['text']}" for d in padded_top_docs)
    padded_response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=(
            "Answer only using the provided context. If the answer isn't "
            "in it, say so."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{padded_context}\n\nQuestion: {query}",
            }
        ],
    )
    print(f"\nAnswer: {padded_response.content[0].text}")
    print_usage(padded_response, model=MODEL)
    print(
        "\nNote: the corpus grew 4.3x (6 -> 26 docs) but the retrieved set "
        "and the input tokens sent to the model barely moved — the model "
        "never sees the noise docs at all. That's the flat-cost property: "
        "the index absorbed the growth, the request didn't."
    )


# ---------------------------------------------------------------------------
# Agentic search: no index — the model decides what to look up, live
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "search_docs",
        "description": "Search the document library by keyword and get back matching titles with short snippets. Does not return full text.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "read_doc",
        "description": "Read the full text of one document by its id, as returned by search_docs.",
        "input_schema": {
            "type": "object",
            "properties": {"doc_id": {"type": "string"}},
            "required": ["doc_id"],
        },
    },
]


def _search_docs(corpus: list[dict], query: str, k: int = 3) -> list[dict]:
    """Naive keyword overlap scored AT CALL TIME — nothing about this
    corpus was pre-processed before the question arrived. Contrast with
    build_vector_index() above, which does its work before any query
    exists."""
    query_words = set(_tokenize(query))
    scored = []
    for doc in corpus:
        doc_words = set(_tokenize(doc["title"] + " " + doc["text"]))
        overlap = len(query_words & doc_words)
        if overlap:
            scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {"id": doc["id"], "title": doc["title"], "snippet": doc["text"][:80] + "..."}
        for _, doc in scored[:k]
    ]


def _run_tool_loop(corpus: list[dict], query: str) -> tuple:
    """Same shape as 04-tool-use-schema-design/1_simple_loop.py: call the
    model, execute whatever tool it asks for, feed the result back, repeat
    until it stops asking for tools. Every call the model makes here is
    ITS decision, made live — nothing was precomputed for it."""
    messages = [{"role": "user", "content": query}]
    tool_calls_made = []
    total_input = total_output = 0

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            tools=TOOLS,
            messages=messages,
        )
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        if response.stop_reason != "tool_use":
            final_text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return final_text, tool_calls_made, total_input, total_output

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_calls_made.append((block.name, block.input))
            if block.name == "search_docs":
                result = _search_docs(corpus, **block.input)
            elif block.name == "read_doc":
                doc = next((d for d in corpus if d["id"] == block.input["doc_id"]), None)
                result = doc["text"] if doc else "Not found."
            else:
                result = "Unknown tool."
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )
        messages.append({"role": "user", "content": tool_results})


def demo_agentic_search():
    print("\n" + "=" * 70)
    print("2. Agentic search — no index; the model searches live, per question")
    print("=" * 70)

    query = "How long do customers have to request a refund?"
    print(f"\nQuery: {query!r}")
    print(f"Corpus: {len(KNOWLEDGE_BASE)} docs, no pre-processing done on any of them.")

    answer, calls, in_tok, out_tok = _run_tool_loop(KNOWLEDGE_BASE, query)
    print("\nTool calls the model chose to make:")
    for name, args in calls:
        print(f"  • {name}({args})")
    print(f"\nAnswer: {answer}")
    print(f"💰 Usage across the whole loop: {in_tok} in / {out_tok} out")

    print("\n-- Now scaling the corpus to 26 documents (20 irrelevant 'noise' docs) --")
    padded_kb = KNOWLEDGE_BASE + build_noise_docs(20)
    answer2, calls2, in_tok2, out_tok2 = _run_tool_loop(padded_kb, query)
    print("\nTool calls the model chose to make:")
    for name, args in calls2:
        print(f"  • {name}({args})")
    print(f"\nAnswer: {answer2}")
    print(f"💰 Usage across the whole loop: {in_tok2} in / {out_tok2} out")
    print(
        "\nNote: search_docs always returns at most 3 snippets, regardless "
        "of corpus size, so the model's context stays flat here too — the "
        "same guarantee classical RAG gives, achieved by capping what a "
        "live search returns instead of by pre-indexing."
    )


def main():
    demo_classical_rag()
    demo_agentic_search()

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(
        "Classical RAG paid an indexing cost upfront (embedding all 6, "
        "then all 26, documents) so that each query is just a similarity "
        "lookup plus one model call. Agentic search paid nothing upfront, "
        "but each query cost multiple model round trips (one per tool "
        "call) while the model figured out what to look up. Both kept the "
        "model's own context flat as the corpus grew to 26 docs — they "
        "just moved the cost to different places: before the question "
        "(classical RAG's index) vs. inside the answer (agentic search's "
        "extra round trips)."
    )


if __name__ == "__main__":
    main()
