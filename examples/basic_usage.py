"""
Basic Usage Example

This example demonstrates basic usage of the Carver Feeds SDK:
- Fetching topics, feeds, and entries
- Working with DataFrames
- Simple filtering

Prerequisites:
- Install: pip install carver-feeds-sdk
- Create .env file with CARVER_API_KEY
"""

from carver_feeds import get_client, create_data_manager

def main():
    # Example 1: Using the API client directly
    print("=== Example 1: Direct API Client Usage ===")
    client = get_client()

    # Fetch topics
    topics = client.list_topics()
    print(f"Found {len(topics)} topics")
    for topic in topics[:3]:  # Show first 3
        print(f"  - {topic['name']}: {topic.get('description', 'N/A')}")

    # Fetch feeds
    feeds = client.list_feeds()
    print(f"\nFound {len(feeds)} feeds")
    for feed in feeds[:3]:  # Show first 3
        topic_name = feed.get('topic', {}).get('name', 'Unknown')
        print(f"  - {feed['name']} (Topic: {topic_name})")

    print("\n" + "="*60 + "\n")

    # Example 2: Using the data manager for DataFrames
    print("=== Example 2: DataFrame Usage ===")
    dm = create_data_manager()

    # Get topics as DataFrame
    topics_df = dm.get_topics_df()
    print(f"Topics DataFrame shape: {topics_df.shape}")
    print("\nFirst 3 topics:")
    print(topics_df[['id', 'name', 'is_active']].head(3))

    # Get feeds as DataFrame
    feeds_df = dm.get_feeds_df()
    print(f"\nFeeds DataFrame shape: {feeds_df.shape}")
    print("\nFirst 3 feeds:")
    print(feeds_df[['id', 'name', 'topic_name', 'is_active']].head(3))

    # Get entries for a specific feed
    if len(feeds_df) > 0:
        first_feed_id = feeds_df['id'].iloc[0]
        first_feed_name = feeds_df['name'].iloc[0]

        entries_df = dm.get_entries_df(feed_id=first_feed_id)
        print(f"\nEntries for feed '{first_feed_name}':")
        print(f"  Total entries: {len(entries_df)}")
        if len(entries_df) > 0:
            print("\nFirst 3 entries:")
            print(entries_df[['id', 'title', 'published_at']].head(3))


if __name__ == "__main__":
    main()
