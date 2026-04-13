"""
Statutes Example

This example demonstrates how to work with statutes:
- Listing all statutes (no filters)
- Fetching available filter options
- Filtering statutes by jurisdiction
- Fetching a specific statute by ID
- Fetching feed entry annotations linked to a statute

Prerequisites:
- Install: pip install carver-feeds-sdk
- Create .env file with CARVER_API_KEY
"""

from carver_feeds import get_client


def main():
    client = get_client()

    print("=" * 60)
    print("Carver Feeds SDK - Statutes Examples")
    print("=" * 60 + "\n")

    # Example 1: List all statutes (no filters)
    print("=== Example 1: List All Statutes ===")
    try:
        result = client.list_statutes()
        print(f"Total statutes: {result['total']}")
        print(f"Returned: {len(result['statutes'])} (limit={result['limit']}, offset={result['offset']})")
        for statute in result["statutes"][:3]:
            print(f"  - [{statute.get('jurisdiction', 'N/A')}] {statute['canonical_name']} ({statute.get('year', 'N/A')})")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 2: Get available filter options
    print("=== Example 2: Get Filter Options ===")
    try:
        options = client.get_statute_filter_options()
        print(f"Jurisdictions: {', '.join(options.get('jurisdictions', []))}")
        print(f"Legal levels:  {', '.join(options.get('legal_levels', []))}")
        print(f"Document types: {', '.join(options.get('document_types', []))}")
        print(f"Languages:     {', '.join(options.get('languages', []))}")
        years = options.get("years", [])
        if years:
            print(f"Year range:    {min(years)} – {max(years)}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 3: Filter statutes by jurisdiction (US)
    print("=== Example 3: Filter Statutes by Jurisdiction (US) ===")
    try:
        result = client.list_statutes(jurisdiction="US", limit=5)
        print(f"US statutes found: {result['total']}")
        for statute in result["statutes"]:
            citation = statute.get("code_citation", "N/A")
            print(f"  - {statute['canonical_name']} ({statute.get('year', 'N/A')}) — {citation}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 4: Get a specific statute by ID
    print("=== Example 4: Get a Specific Statute ===")
    try:
        # Fetch first statute from the list and retrieve it by ID
        all_statutes = client.list_statutes(limit=1)
        statutes = all_statutes.get("statutes", [])
        if statutes:
            first_id = statutes[0]["id"]
            statute = client.get_statute(first_id)
            print(f"Statute ID:       {statute['id']}")
            print(f"Canonical name:   {statute['canonical_name']}")
            print(f"Jurisdiction:     {statute.get('jurisdiction', 'N/A')}")
            print(f"Legal level:      {statute.get('legal_level', 'N/A')}")
            print(f"Document type:    {statute.get('document_type', 'N/A')}")
            print(f"Year:             {statute.get('year', 'N/A')}")
            variants = statute.get("variants", [])
            if variants:
                print(f"Also known as:    {', '.join(variants)}")
        else:
            print("No statutes found.")
            first_id = None
    except Exception as e:
        print(f"Error: {e}")
        first_id = None

    print("\n" + "=" * 60 + "\n")

    # Example 5: Get annotations for a statute
    print("=== Example 5: Get Annotations for a Statute ===")
    if first_id:
        try:
            result = client.get_statute_annotations(first_id, limit=10)
            print(f"Statute:          {result.get('statute_name', first_id)}")
            print(f"Related entries:  {result['total']}")
            for entry in result.get("feed_entries", [])[:5]:
                print(f"  - {entry.get('title', entry.get('id', 'N/A'))}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Skipped — no statute ID available from Example 4.")

    print("\n" + "=" * 60)
    print("\nExamples complete!")
    print("\nNext steps:")
    print("  1. Try filtering by legal_level, document_type, or search keyword")
    print("  2. Use pagination (limit/offset) to browse large result sets")
    print("  3. Combine statute data with feed entry annotations for deeper analysis")
    print("=" * 60)


if __name__ == "__main__":
    main()
