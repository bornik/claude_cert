"""
EXAMPLE 3: Schema Design — Good vs Bad

Claude picks tools based on:
1. Tool name (specificity matters)
2. Description (clarity beats length)
3. Input schema (required fields force Claude to guess)

This example shows BAD design and GOOD design side by side.
No API calls — just print and compare.
"""

import json


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
    print("   Claude cannot tell them apart!")
    print("   Will randomly pick one when they serve different purposes.")

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


def show_required_fields_issue():
    """Show why marking too many fields as required is bad"""
    print("\n" + "="*70)
    print("❌ BAD: Too many required fields")
    print("="*70)

    bad_schema = {
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
    show_bad_schema()
    show_good_schema()
    show_required_fields_issue()
    show_good_required_fields()
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
