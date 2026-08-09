"""
EXAMPLE 1: Files API — Upload Once, Reference Many Times

Without the Files API, sending a document to Claude means inlining its
full content into every single message that needs it — if you ask 5
questions about the same report, you pay to re-send that report 5 times.

The Files API lets you upload a file once and get back a file_id, then
reference that id from as many messages as you want. The file's bytes
are stored by Anthropic, not resent by your application each turn.

Requires the `files-api-2025-04-14` beta header.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

SAMPLE_FILE = Path(__file__).resolve().parent / "sample.txt"
FILES_BETA = "files-api-2025-04-14"


def upload_file():
    print("\n" + "=" * 70)
    print("Step 1: Upload the file once")
    print("=" * 70)
    with open(SAMPLE_FILE, "rb") as f:
        uploaded = client.beta.files.upload(
            file=(SAMPLE_FILE.name, f, "text/plain"),
            extra_headers={"anthropic-beta": FILES_BETA},
        )
    print(f"Uploaded: file_id={uploaded.id!r}, filename={uploaded.filename!r}, size={uploaded.size_bytes} bytes")
    return uploaded.id


def ask_about_file(file_id, question):
    response = client.beta.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        betas=[FILES_BETA],
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "document", "source": {"type": "file", "file_id": file_id}},
                    {"type": "text", "text": question},
                ],
            }
        ],
    )
    print_usage(response, model="claude-haiku-4-5")
    return next((b.text for b in response.content if b.type == "text"), "")


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Files API — Upload Once, Reference by file_id")
    print("=" * 70)

    file_id = upload_file()

    print("\n" + "=" * 70)
    print("Step 2: Ask MULTIPLE questions, referencing the SAME file_id each time")
    print("=" * 70)

    for question in [
        "What was Q1 revenue and how much did it grow?",
        "Why did support ticket volume rise?",
    ]:
        print(f"\nQ: {question}")
        answer = ask_about_file(file_id, question)
        print(f"A: {answer}")

    print(f"""
📝 Takeaway: both questions above referenced file_id={file_id!r} — the
report's text was uploaded ONCE, not inlined into each message. Compare
this to putting the full document text directly in the `content` array
of every request (the pre-Files-API way): that approach re-sends and
re-bills the document's tokens on every single call. The Files API
trades a one-time upload for cheaper, simpler repeat access.

Cleanup: files persist on Anthropic's side until deleted — in a real
app, call client.beta.files.delete(file_id) when you're done with it.
""")
    client.beta.files.delete(file_id, extra_headers={"anthropic-beta": FILES_BETA})
    print(f"Deleted file_id={file_id!r}.")


if __name__ == "__main__":
    main()
