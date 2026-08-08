"""
EXAMPLE 3: Schema Design — Good vs Bad

Claude picks tools based on:
1. Tool name (specificity matters)
2. Description (clarity beats length)
3. Input schema (required fields force Claude to guess)

This example shows BAD design and GOOD design side by side, then proves
the point with real API calls: the same ambiguous query sent against the
bad schema and the good schema, so you see Claude's actual tool choice
rather than just reading a claim about it.
"""

import json
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()


def show_bad_schema():
    """Schema that causes wrong tool selection"""
    print("\n" + "="*70)
    print("❌ BAD SCHEMA: Overlapping descriptions")
    print("="*70)

    bad_tools = [
        {
            "name": "search_kb",
            "description": "Use this to find information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        },
        {
            "name": "get_cache",
            "description": "Use this to find information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }
    ]

    print("\nBoth descriptions say 'find information':")
    for tool in bad_tools:
        print(f"  • {tool['name']}: '{tool['description']}'")

    print("\n❌ Problem:")
    print("   The description gives Claude nothing to disambiguate with.")
    print("   It may still guess right on easy queries (see the live check below) —")
    print("   but on a genuinely ambiguous one, it has nothing but the name to go on.")

    return bad_tools


def show_good_schema():
    """Schema with clear distinctions"""
    print("\n" + "="*70)
    print("✓ GOOD SCHEMA: Clear distinctions with exclusion conditions")
    print("="*70)

    good_tools = [
        {
            "name": "search_kb",
            "description": "Search the knowledge base for current information. Use when the user asks a question that requires looking up new data. Do not use if a prior search in this session already covered the question.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_cache",
            "description": "Retrieve a result that was already fetched during this session. Use only if search_kb was called earlier for the same query. Do not use to find new information.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The query key to retrieve"}
                },
                "required": ["query"]
            }
        }
    ]

    print("\nEach has a clear role:")
    for tool in good_tools:
        # Show first 60 chars of description
        desc_preview = tool['description'][:60] + "..."
        print(f"  • {tool['name']}: {desc_preview}")

    print("\n✓ Benefit:")
    print("   Each description has a 'do not use' clause.")
    print("   Claude knows when to pick which one.")

    return good_tools


def demo_live_tool_selection(bad_tools, good_tools):
    """Send the SAME ambiguous query against both schemas and see which
    tool Claude actually picks — real evidence instead of a claim."""
    print("\n" + "=" * 70)
    print("🔴 LIVE CHECK: Same query, bad schema vs good schema")
    print("=" * 70)

    query = "What's the refund policy?"
    print(f"\nQuery: {query!r}")
    print("(No mention of a prior search — the correct tool is search_kb, a fresh lookup.)")

    picks = {}
    for label, tools in [("❌ Bad schema", bad_tools), ("✓ Good schema", good_tools)]:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            tools=tools,
            tool_choice={"type": "any"},  # force a tool call so we always get a pick
            messages=[{"role": "user", "content": query}],
        )
        print_usage(response)
        tool_call = next((b for b in response.content if b.type == "tool_use"), None)
        picked = tool_call.name if tool_call else "(no tool called)"
        picks[label] = picked
        print(f"{label}: Claude picked → {picked}")

    if len(set(picks.values())) == 1:
        print(
            "\n📝 Note: both picked correctly here — the tool NAMES alone "
            "(search_kb vs get_cache) already carry enough signal, even with "
            "identical descriptions. Bad descriptions don't always fail on an "
            "easy query; they fail once a query is genuinely ambiguous between "
            "two similarly-named tools. Try rewriting the query (or the tool "
            "names) to see it break."
        )


def demo_live_required_fields(bad_schema, good_schema):
    """Same idea for required fields: give Claude only a user_id and see
    whether it invents values for fields it wasn't told about."""
    print("\n" + "=" * 70)
    print("🔴 LIVE CHECK: Required fields — does Claude invent values?")
    print("=" * 70)

    query = "List the items for user usr_789."
    print(f"\nQuery: {query!r} (no filter/sort/page_size mentioned)")

    for label, schema in [("❌ All required", bad_schema), ("✓ Only user_id required", good_schema)]:
        tools = [{
            "name": "list_items",
            "description": "List items belonging to a user.",
            "input_schema": schema,
        }]
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            tools=tools,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": query}],
        )
        print_usage(response)
        tool_call = next((b for b in response.content if b.type == "tool_use"), None)
        print(f"{label}: input → {tool_call.input if tool_call else '(no tool called)'}")


def show_required_fields_issue():
    """Show why marking too many fields as required is bad"""
    print("\n" + "="*70)
    print("❌ BAD: Too many required fields")
    print("="*70)

    bad_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "User ID"},
            "filter": {"type": "string", "description": "Filter type"},
            "sort": {"type": "string", "description": "Sort order"},
            "page_size": {"type": "integer", "description": "Items per page"}
        },
        "required": ["user_id", "filter", "sort", "page_size"]
    }

    print("\nRequired fields: ['user_id', 'filter', 'sort', 'page_size']")
    print("\n❌ Problem:")
    print("   Claude HAS user_id from context")
    print("   But it doesn't know what filter/sort/page_size to use")
    print("   So it INVENTS values that might be wrong")

    print("\nJSON:")
    print(json.dumps(bad_schema, indent=2))

    return bad_schema


def show_good_required_fields():
    """Show the right way to use required fields"""
    print("\n" + "="*70)
    print("✓ GOOD: Only essentials are required")
    print("="*70)

    good_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "User ID"},
            "filter": {"type": "string", "description": "Filter type (optional)"},
            "sort": {"type": "string", "description": "Sort order (optional)"},
            "page_size": {"type": "integer", "description": "Items per page (optional)"}
        },
        "required": ["user_id"]
    }

    print("\nRequired fields: ['user_id']")
    print("\n✓ Benefit:")
    print("   Claude only fills in user_id (it has this)")
    print("   Omits filter/sort/page_size if it doesn't have them")
    print("   Better tool calls, fewer hallucinations")

    print("\nJSON:")
    print(json.dumps(good_schema, indent=2))

    return good_schema


def show_description_length():
    """Show why description length matters"""
    print("\n" + "="*70)
    print("Description Length Matters")
    print("="*70)

    print("\n❌ Too short (Claude guesses):")
    print('   "Get user information"')
    print("   → Does this mean profile? Preferences? Contact?")

    print("\n❌ Too long (signal lost in noise):")
    too_long = "This tool retrieves user information from the database. It was implemented in Q2 2024 and uses the legacy user_info endpoint which was deprecated in favor of the new unified user service. When calling this tool, you may pass user_id or email. Note that the tool was designed for internal use and some fields may be null. The endpoint returns a JSON object with fields like name, email, phone, address, and preferences. You should call this before calling get_user_preferences because of caching behavior."
    print(f'   "{too_long[:60]}..."')
    print("   → Too much detail, Claude loses the decision rule")

    print("\n✓ Just right (3-4 sentences):")
    perfect = "Retrieve a user's profile data including name, email, and account creation date. Use this when the user asks about their profile or personal information. Do not use this for preferences or notification settings — those have separate tools. Example user_id: 'usr_12345'."
    print(f'   "{perfect}"')
    print("   → Clear, includes do-not-use, has example format")


def main():
    bad_tools = show_bad_schema()
    good_tools = show_good_schema()
    demo_live_tool_selection(bad_tools, good_tools)

    bad_schema = show_required_fields_issue()
    good_schema = show_good_required_fields()
    demo_live_required_fields(bad_schema, good_schema)

    show_description_length()

    print("\n" + "="*70)
    print("KEY TAKEAWAY")
    print("="*70)
    print("""
When writing schemas:
1. Name should be specific (not "get_data")
2. Description should have 3-4 sentences with:
   - What it does
   - When to use it
   - When NOT to use it
   - Example of valid input format
3. Required fields = only the ones Claude truly cannot call without
4. Optional fields = everything else (Claude omits when unsure)

Test your schema: does Claude pick it correctly?
If not, add a "do not use for X" clause to disambiguate.
    """)


if __name__ == "__main__":
    main()
