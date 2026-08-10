# Module 09 — Memory

## Files

### 1️⃣ `1_session_vs_persistent_memory.py` — Where "Memory" Actually Lives
**What:** A fact learned mid-conversation (session memory) disappears the instant a fresh `messages[]` list starts. A fact written to a file (persistent memory) can be read back and re-injected into a brand new conversation's system prompt.

**Key concepts:**
- Claude has no memory of its own between separate API calls — "memory" is always just text re-entering the context window somehow
- Session memory = earlier turns in the same `messages[]` list
- Persistent memory = storage outside the context window (file/DB) that your code reads and re-injects — proven live: a fresh conversation with no injected memory forgot the preference; the same fresh conversation with `memory_store.json` read into the system prompt recalled it correctly
- The real design question is what to store, where, and when to re-inject it — not "how Claude remembers"

```bash
uv run 09-memory/1_session_vs_persistent_memory.py
```
