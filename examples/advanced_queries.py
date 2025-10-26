"""
Advanced Query Example

This example demonstrates advanced querying capabilities:
- Method chaining
- Filtering by topic, feed, date, and status
- Keyword search
- Exporting results to different formats

Prerequisites:
- Install: pip install carver-feeds-sdk
- Create .env file with CARVER_API_KEY
"""

from carver_feeds import create_query_engine
from datetime import datetime, timedelta

def main():
    # Create query engine
    qe = create_query_engine()

    # Example 1: Filter by topic
    print("=== Example 1: Filter by Topic ===")
    results = qe.filter_by_topic(topic_name="Banking").to_dataframe()
    print(f"Found {len(results)} entries in Banking topics")
    if len(results) > 0:
        print("\nSample entries:")
        print(results[['entry_title', 'topic_name', 'entry_published_at']].head(3))

    print("\n" + "="*60 + "\n")

    # Example 2: Filter by date range
    print("=== Example 2: Filter by Date Range ===")
    qe2 = qe.chain()  # Create fresh instance

    # Get entries from last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    results = qe2.filter_by_date(start_date=thirty_days_ago).to_dataframe()
    print(f"Found {len(results)} entries from last 30 days")
    if len(results) > 0:
        print("\nRecent entries:")
        print(results[['entry_title', 'entry_published_at']].head(3))

    print("\n" + "="*60 + "\n")

    # Example 3: Complex query with multiple filters
    print("=== Example 3: Complex Multi-Filter Query ===")
    qe3 = qe.chain()  # Create fresh instance

    results = qe3 \
        .filter_by_topic(topic_name="Ireland") \
        .filter_by_active(is_active=True) \
        .filter_by_date(start_date=datetime(2024, 1, 1)) \
        .search_entries(["regulation", "compliance"], match_all=False) \
        .to_dataframe()

    print(f"Found {len(results)} matching entries")
    if len(results) > 0:
        print("\nMatching entries:")
        print(results[['entry_title', 'topic_name', 'entry_published_at']].head(5))

    print("\n" + "="*60 + "\n")

    # Example 4: Search with keyword
    print("=== Example 4: Keyword Search ===")
    qe4 = qe.chain()  # Create fresh instance

    results = qe4.search_entries("regulation").to_dataframe()
    print(f"Found {len(results)} entries containing 'regulation'")
    if len(results) > 0:
        print("\nSearch results:")
        print(results[['entry_title', 'topic_name']].head(3))

    print("\n" + "="*60 + "\n")

    # Example 5: Export results to different formats
    print("=== Example 5: Export Results ===")
    qe5 = qe.chain()
    qe5.filter_by_active(is_active=True)

    # Export to CSV
    csv_path = qe5.to_csv("results.csv")
    print(f"Exported to CSV: {csv_path}")

    # Export to JSON (returns JSON string, not filepath)
    json_str = qe5.to_json(indent=2)
    with open("results.json", "w") as f:
        f.write(json_str)
    print(f"Exported to JSON: results.json")

    # Get as dictionary
    results_dict = qe5.to_dict()
    print(f"Got {len(results_dict)} results as dictionary")


if __name__ == "__main__":
    main()
