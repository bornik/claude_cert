# Module 10 — Files API

## Files

### 1️⃣ `1_files_api_basics.py` — Upload Once, Reference Many Times
**What:** Uploads `sample.txt` once via `client.beta.files.upload()`, then asks two separate questions about it, each referencing the same `file_id` — instead of inlining the document's full text into every message.

**Key concepts:**
- Requires the `files-api-2025-04-14` beta header
- `{"type": "document", "source": {"type": "file", "file_id": ...}}` content block references an uploaded file
- Files persist on Anthropic's side until explicitly deleted (`client.beta.files.delete(file_id)`) — clean up when done
- The alternative (inlining the document text in every request) re-sends and re-bills those tokens on every single call

```bash
uv run 10-files-api/1_files_api_basics.py
```
