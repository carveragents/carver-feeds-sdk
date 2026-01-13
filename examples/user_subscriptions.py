"""
User Topic Subscriptions Example

This example demonstrates how to work with user topic subscriptions:
- Fetching user subscriptions via API client
- Working with subscriptions as DataFrames
- Filtering entries based on user subscriptions
- Analyzing subscription patterns

Prerequisites:
- Install: pip install carver-feeds-sdk
- Create .env file with CARVER_API_KEY
- Valid user_id from your Carver system
"""

from carver_feeds import create_data_manager, create_query_engine, get_client


def main():
    # Example 1: Using the API client to fetch subscriptions
    print("=== Example 1: Fetch User Subscriptions (API Client) ===")
    client = get_client()

    # Replace with actual user ID from your system
    user_id = "your-user-id-here"

    print(f"Fetching subscriptions for user: {user_id}")

    try:
        result = client.get_user_topic_subscriptions(user_id)

        print(f"\nUser has {result['total_count']} topic subscriptions")
        print("\nSubscribed topics:")
        for topic in result["subscriptions"]:
            domain_info = f" ({topic['base_domain']})" if topic.get("base_domain") else ""
            print(f"  - {topic['name']}{domain_info}")
            print(f"    ID: {topic['id']}")
            if topic.get("description"):
                desc = (
                    topic["description"][:80] + "..."
                    if len(topic["description"]) > 80
                    else topic["description"]
                )
                print(f"    Description: {desc}")
            print()
    except Exception as e:
        print(f"Error: {e}")
        print("\nTip: Replace 'your-user-id-here' with a valid user ID from your Carver system")
        return

    print("=" * 60 + "\n")

    # Example 2: Using the data manager for DataFrame operations
    print("=== Example 2: User Subscriptions as DataFrame ===")
    dm = create_data_manager()

    try:
        subscriptions_df = dm.get_user_topic_subscriptions_df(user_id)

        print(f"Subscriptions DataFrame shape: {subscriptions_df.shape}")
        print(f"\nColumns: {list(subscriptions_df.columns)}")

        if len(subscriptions_df) > 0:
            print("\nSubscribed topics:")
            print(subscriptions_df[["name", "base_domain"]])

            # Show topics with base_domain
            has_domain = subscriptions_df[subscriptions_df["base_domain"].notna()]
            if len(has_domain) > 0:
                print(f"\n{len(has_domain)} topics have base domains:")
                print(has_domain[["name", "base_domain"]])
        else:
            print("\nUser has no subscriptions yet")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 3: Fetch entries for user's subscribed topics
    print("=== Example 3: Fetch Entries from Subscribed Topics ===")

    if "subscriptions_df" in locals() and len(subscriptions_df) > 0:
        print(f"Fetching entries for {len(subscriptions_df)} subscribed topics...")

        # Get first subscribed topic for demonstration
        first_topic_id = subscriptions_df["id"].iloc[0]
        first_topic_name = subscriptions_df["name"].iloc[0]

        print(f"\nFetching entries for: {first_topic_name}")

        entries_df = dm.get_topic_entries_df(topic_id=first_topic_id)
        print(f"  Found {len(entries_df)} entries")

        if len(entries_df) > 0:
            print("\nRecent entries:")
            print(entries_df[["title", "published_at"]].head(5))
    else:
        print("No subscriptions to fetch entries for")

    print("\n" + "=" * 60 + "\n")

    # Example 4: Query engine filtering by user subscriptions
    print("=== Example 4: Advanced Filtering with Query Engine ===")

    if "subscriptions_df" in locals() and len(subscriptions_df) > 0:
        qe = create_query_engine()

        # Get first subscribed topic name for filtering
        first_topic_name = subscriptions_df["name"].iloc[0]

        print(f"Filtering entries from '{first_topic_name}'...")

        results = (
            qe.filter_by_topic(topic_name=first_topic_name)
            .filter_by_active(is_active=True)
            .to_dataframe()
        )

        print(f"Found {len(results)} active entries")

        if len(results) > 0:
            print("\nEntry details:")
            print(results[["entry_title", "topic_name", "entry_published_at"]].head(3))

            # Search within subscribed topic
            print(f"\nSearching for 'regulation' in {first_topic_name}...")
            qe2 = qe.chain()
            search_results = (
                qe2.filter_by_topic(topic_name=first_topic_name)
                .search_entries("regulation", search_fields=["entry_title", "entry_description"])
                .to_dataframe()
            )

            print(f"Found {len(search_results)} entries matching 'regulation'")
            if len(search_results) > 0:
                print("\nMatching entries:")
                print(search_results[["entry_title"]].head(3))
    else:
        print("No subscriptions to query")

    print("\n" + "=" * 60 + "\n")

    # Example 5: Aggregate statistics across all subscribed topics
    print("=== Example 5: Subscription Statistics ===")

    if "subscriptions_df" in locals() and len(subscriptions_df) > 0:
        print(f"Analyzing {len(subscriptions_df)} subscribed topics...\n")

        total_entries = 0
        topic_stats = []

        for _idx, row in subscriptions_df.iterrows():
            topic_id = row["id"]
            topic_name = row["name"]

            # Get entries for this topic (without content for speed)
            entries = dm.get_topic_entries_df(topic_id=topic_id, fetch_content=False)
            entry_count = len(entries)
            total_entries += entry_count

            topic_stats.append({"topic": topic_name, "entries": entry_count})

        print(f"Total entries across all subscriptions: {total_entries}")
        print(f"Average entries per topic: {total_entries / len(subscriptions_df):.1f}")

        print("\nEntries per subscribed topic:")
        for stat in sorted(topic_stats, key=lambda x: x["entries"], reverse=True):
            print(f"  - {stat['topic']}: {stat['entries']} entries")
    else:
        print("No subscriptions to analyze")

    print("\n" + "=" * 60 + "\n")

    # Example 6: Export user subscription data
    print("=== Example 6: Export Subscription Data ===")

    if "subscriptions_df" in locals() and len(subscriptions_df) > 0:
        # Export subscriptions to CSV
        output_file = f"user_{user_id}_subscriptions.csv"
        subscriptions_df.to_csv(output_file, index=False)
        print(f"Exported subscriptions to: {output_file}")

        # Export with entry counts
        if topic_stats:
            import pandas as pd

            stats_df = pd.DataFrame(topic_stats)
            stats_file = f"user_{user_id}_topic_stats.csv"
            stats_df.to_csv(stats_file, index=False)
            print(f"Exported topic statistics to: {stats_file}")
    else:
        print("No subscriptions to export")


if __name__ == "__main__":
    main()
