"""
Advanced Query Example

This example demonstrates advanced querying capabilities:
- Method chaining
- Filtering by topic, date, and status
- Keyword search (in title/description and full S3 content)
- Exporting results to different formats
- Working with S3 content

Prerequisites:
- Install: pip install carver-feeds-sdk
- Create .env file with CARVER_API_KEY
- Optional: Configure AWS_PROFILE_NAME for S3 content access
"""

from carver_feeds import create_query_engine
from datetime import datetime, timedelta

def main():
    # Create query engine
    qe = create_query_engine()

    # Example 1: Filter by topic
    print("=== Example 1: Filter by Topic ===")
    topic_contains_str = "Abu Dhabi"
    results = qe.filter_by_topic(topic_name=topic_contains_str).to_dataframe()
    print(f"Found {len(results)} entries in topics containing '{topic_contains_str}'")
    if len(results) > 0:
        print("\nSample entries:")
        print(results[['entry_title', 'topic_name', 'entry_published_at']].head(3))

    print("\n" + "="*60 + "\n")

    # Example 2: Filter by date range
    print("=== Example 2: Filter by Date Range ===")
    qe2 = qe.chain()  # Create fresh instance

    # Get entries from last 30 days (must filter by topic first)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    results = qe2 \
        .filter_by_topic(topic_name=topic_contains_str) \
        .filter_by_date(start_date=thirty_days_ago) \
        .to_dataframe()
    print(f"Found {len(results)} entries from last 30 days for '{topic_contains_str}' topics")
    if len(results) > 0:
        print("\nRecent entries:")
        print(results[['entry_title', 'entry_published_at']].head(3))

    print("\n" + "="*60 + "\n")

    # Example 3: Keyword Search (in title/description, no S3 needed)
    print("=== Example 3: Keyword Search (Title/Description) ===")
    qe3 = qe.chain()  # Create fresh instance

    # Search in title and description fields (no S3 content needed)
    results = qe3 \
        .filter_by_topic(topic_name=topic_contains_str) \
        .search_entries("regulation", search_fields=["entry_title", "entry_description"]) \
        .to_dataframe()
    print(f"Found {len(results)} entries with 'regulation' in title/description")
    if len(results) > 0:
        print("\nSearch results:")
        print(results[['entry_title', 'topic_name']].head(3))
    else:
        print("Tip: Try different keywords like 'market', 'financial', 'securities', etc.")

    print("\n" + "="*60 + "\n")

    # Example 4: Keyword Search with S3 Content
    print("=== Example 4: Keyword Search (Full Content from S3) ===")
    print("Note: Requires AWS_PROFILE_NAME configured in .env")
    qe4 = qe.chain()  # Create fresh instance

    # Fetch content from S3 first, then search in full content body
    results = qe4 \
        .filter_by_topic(topic_name=topic_contains_str) \
        .filter_by_date(start_date=datetime(2024, 10, 1)) \
        .fetch_content() \
        .search_entries("regulation") \
        .to_dataframe()

    print(f"Found {len(results)} entries with 'regulation' in full content (Oct 2024+)")
    if len(results) > 0:
        print("\nSearch results:")
        for idx, row in results.head(3).iterrows():
            print(f"  - {row['entry_title']}")
            if row.get('entry_content_markdown'):
                # Show snippet around the keyword
                content = row['entry_content_markdown']
                keyword_pos = content.lower().find('regulation')
                if keyword_pos != -1:
                    start = max(0, keyword_pos - 50)
                    end = min(len(content), keyword_pos + 100)
                    snippet = content[start:end].replace('\n', ' ')
                    print(f"    ...{snippet}...")
    else:
        print("\nTip: Configure AWS_PROFILE_NAME in .env to search full content")
        print("Without S3, search is limited to title/description fields")

    print("\n" + "="*60 + "\n")

    # Example 5: Complex query with multiple filters
    print("=== Example 5: Complex Multi-Filter Query ===")
    qe5 = qe.chain()  # Create fresh instance

    # Combine topic filter + date filter + keyword search (in title/description)
    results = qe5 \
        .filter_by_topic(topic_name=topic_contains_str) \
        .filter_by_date(start_date=datetime(2024, 1, 1)) \
        .search_entries(["regulation", "compliance"], match_all=False, search_fields=["entry_title", "entry_description"]) \
        .to_dataframe()

    print(f"Found {len(results)} matching entries")
    if len(results) > 0:
        print("\nMatching entries:")
        print(results[['entry_title', 'topic_name', 'entry_published_at']].head(5))
    else:
        print("Tip: Try different keywords or broader date ranges")

    print("\n" + "="*60 + "\n")

    # Example 6: Export results to different formats
    print("=== Example 6: Export Results ===")
    qe6 = qe.chain()

    # Filter by topic first, then by active status
    qe6 = qe6.filter_by_topic(topic_name=topic_contains_str).filter_by_active(is_active=True)

    # Export to CSV
    csv_path = qe6.to_csv("results.csv")
    print(f"Exported to CSV: {csv_path}")

    # Export to JSON (returns JSON string, not filepath)
    json_str = qe6.to_json(indent=2)
    with open("results.json", "w") as f:
        f.write(json_str)
    print(f"Exported to JSON: results.json")

    # Get as dictionary
    results_dict = qe6.to_dict()
    print(f"Got {len(results_dict)} results as dictionary")

    print("\n" + "="*60 + "\n")

    # Example 7: Lazy Loading with S3 Content
    print("=== Example 7: Lazy Loading with S3 Content ===")
    print("Note: Requires AWS_PROFILE_NAME configured in .env")

    qe7 = qe.chain()

    # Filter first, THEN fetch content (more efficient)
    results = qe7 \
        .filter_by_topic(topic_name=topic_contains_str) \
        .filter_by_date(start_date=datetime(2024, 10, 1)) \
        .fetch_content() \
        .to_dataframe()

    print(f"Found {len(results)} entries from Oct 2024+")

    if len(results) > 0:
        has_content = results['entry_content_markdown'].notna().sum()
        print(f"Entries with S3 content: {has_content}/{len(results)}")

        # Show first entry with content
        for idx, row in results.iterrows():
            if row.get('entry_content_markdown'):
                print(f"\nSample entry with content:")
                print(f"  Title: {row['entry_title']}")
                print(f"  Topic: {row['topic_name']}")
                print(f"  Content length: {len(row['entry_content_markdown'])} characters")
                print(f"  Content preview: {row['entry_content_markdown'][:100]}...")
                break
    else:
        print("\nTip: Configure AWS_PROFILE_NAME in .env to fetch content from S3")
        print("Without S3 config, entry_content_markdown will be None")


if __name__ == "__main__":
    main()
