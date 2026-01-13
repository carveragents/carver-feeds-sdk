"""
Basic Usage Example

This example demonstrates basic usage of the Carver Feeds SDK:
- Fetching topics and entries
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

    print("\n" + "="*60 + "\n")

    # Example 2: Using the data manager for DataFrames
    print("=== Example 2: DataFrame Usage ===")
    dm = create_data_manager()

    # Get topics as DataFrame
    topics_df = dm.get_topics_df()
    print(f"Topics DataFrame shape: {topics_df.shape}")
    print("\nFirst 3 topics:")
    print(topics_df[['id', 'name', 'is_active']].head(3))

    # Get entries for a specific topic
    if len(topics_df) > 0:
        topic_num = 1
        first_topic_id = topics_df['id'].iloc[topic_num]
        first_topic_name = topics_df['name'].iloc[topic_num]

        entries_df = dm.get_topic_entries_df(topic_id=first_topic_id)
        print(f"\nEntries for topic '{first_topic_name}':")
        print(f"  Total entries: {len(entries_df)}")
        if len(entries_df) > 0:
            print("\nFirst 3 entries:")
            print(entries_df[['id', 'title', 'published_at']].head(3))

    print("\n" + "="*60 + "\n")

    # Example 3: Fetching content from S3
    print("=== Example 3: Fetch Content from S3 (v0.2.0+) ===")
    print("Note: Requires AWS_PROFILE_NAME configured in .env")

    if len(topics_df) > 0:
        first_topic_id = topics_df['id'].iloc[topic_num]

        # Fetch entries WITH content from S3
        entries_with_content = dm.get_topic_entries_df(
            topic_id=first_topic_id,
            fetch_content=True  # Fetch content from S3
        )

        print(f"\nEntries with S3 content:")
        print(f"  Total entries: {len(entries_with_content)}")

        if len(entries_with_content) > 0:
            # Check how many have content
            has_content = entries_with_content['entry_content_markdown'].notna().sum()
            print(f"  Entries with content: {has_content}/{len(entries_with_content)}")

            # Show first entry with content
            for idx, row in entries_with_content.iterrows():
                if row.get('entry_content_markdown'):
                    print(f"\nFirst entry with content:")
                    print(f"  Title: {row['title']}")
                    print(f"  Content length: {len(row['entry_content_markdown'])} characters")
                    print(f"  Content preview: {row['entry_content_markdown'][:500]}...")
                    break
        else:
            print("\n  Tip: Set AWS_PROFILE_NAME in .env to fetch content from S3")


if __name__ == "__main__":
    main()
