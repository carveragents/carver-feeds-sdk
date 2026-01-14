"""
Annotations Example

This example demonstrates how to work with annotations:
- Fetching annotations by feed entry IDs
- Fetching annotations by topic IDs
- Fetching annotations by user IDs
- Analyzing annotation scores and classifications
- Working with annotation summaries

Prerequisites:
- Install: pip install carver-feeds-sdk
- Create .env file with CARVER_API_KEY

Note: This script automatically fetches topics and entries from your
Carver system, so no manual ID configuration is required.
"""

from carver_feeds import get_client, create_data_manager


def get_sample_data(client):
    """
    Fetch sample topics and feed entries from the API for demonstration.

    This helper function:
    1. Fetches all topics
    2. Selects the first 2-3 active topics
    3. Fetches feed entries for those topics
    4. Returns topic IDs and feed entry IDs for use in examples

    Returns:
        tuple: (topic_ids, feed_entry_ids, dm) where dm is the data manager
    """
    print("Fetching sample data from Carver API...")

    # Use data manager for easier DataFrame operations
    dm = create_data_manager()

    # Get all topics
    topics_df = dm.get_topics_df()

    # Filter for active topics only
    active_topics = topics_df[topics_df['is_active'] == True]

    if len(active_topics) == 0:
        raise ValueError("No active topics found in your Carver system")

    # Take first 2-3 active topics
    sample_topics = active_topics.head(3)
    topic_ids = sample_topics['id'].tolist()

    print(f"  Found {len(active_topics)} active topics")
    print(f"  Using {len(topic_ids)} topics for examples:")
    for idx, row in sample_topics.iterrows():
        print(f"    - {row['name']} (ID: {row['id'][:20]}...)")

    # Get feed entries for the first topic
    first_topic_id = topic_ids[0]
    entries_df = dm.get_topic_entries_df(topic_id=first_topic_id)

    if len(entries_df) == 0:
        raise ValueError(f"No entries found for topic {first_topic_id}")

    # Take first 3-5 feed entry IDs
    sample_entries = entries_df.head(5)
    feed_entry_ids = sample_entries['id'].tolist()

    print(f"  Found {len(entries_df)} entries in first topic")
    print(f"  Using {len(feed_entry_ids)} feed entries for examples")
    print()

    return topic_ids, feed_entry_ids, dm


def main():
    # Initialize the API client
    client = get_client()

    print("=" * 60)
    print("Carver Feeds SDK - Annotations Examples")
    print("=" * 60 + "\n")

    # Fetch sample data from the API
    try:
        topic_ids, feed_entry_ids, dm = get_sample_data(client)
    except Exception as e:
        print(f"Error fetching sample data: {e}")
        print("Please ensure your CARVER_API_KEY is configured correctly.")
        return

    # Example 1: Fetch annotations by feed entry IDs
    print("=== Example 1: Fetch Annotations by Feed Entry IDs ===")
    print(f"Using {len(feed_entry_ids)} feed entries from the API\n")

    try:
        annotations = client.get_annotations(feed_entry_ids=feed_entry_ids)

        print(f"Found {len(annotations)} annotations for {len(feed_entry_ids)} feed entries")

        for ann in annotations:
            print(f"\nFeed Entry: {ann['feed_entry_id']}")

            # Display impact summary (what/why/objective)
            impact_summary = ann.get('annotation', {}).get('metadata', {}).get('impact_summary', {})
            if impact_summary:
                if impact_summary.get('objective'):
                    obj = impact_summary['objective']
                    print(f"  Objective: {obj[:150]}..." if len(obj) > 150 else f"  Objective: {obj}")
                if impact_summary.get('why_it_matters'):
                    why = impact_summary['why_it_matters']
                    print(f"  Why it matters: {why[:150]}..." if len(why) > 150 else f"  Why it matters: {why}")

            # Display scores (now objects with label, score, confidence)
            scores = ann.get("annotation", {}).get("scores", {})
            if scores:
                print("  Scores:")
                for score_name, score_obj in scores.items():
                    if isinstance(score_obj, dict):
                        label = score_obj.get('label', 'N/A')
                        score = score_obj.get('score', 0)
                        confidence = score_obj.get('confidence', 0)
                        print(f"    - {score_name}: {label} (score: {score}, confidence: {confidence:.2f})")
                    else:
                        print(f"    - {score_name}: {score_obj}")

            # Display classification
            classification = ann.get("annotation", {}).get("classification", {})
            if classification:
                update_type = classification.get('update_type', 'N/A')
                print(f"  Update Type: {update_type}")

                reg_source = classification.get('regulatory_source', {})
                if reg_source and reg_source.get('name'):
                    print(f"  Regulatory Source: {reg_source['name']}")

            # Display tags from metadata
            tags = ann.get("annotation", {}).get("metadata", {}).get("tags", [])
            if tags:
                print(f"  Tags: {', '.join(tags[:5])}" + (f" (+{len(tags)-5} more)" if len(tags) > 5 else ""))

    except ValueError as e:
        print(f"Validation Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 2: Fetch annotations by topic IDs
    print("=== Example 2: Fetch Annotations by Topic IDs ===")
    print(f"Using {len(topic_ids[:1])} topic from the API\n")

    try:
        # Use first topic ID for this example
        annotations = client.get_annotations(topic_ids=topic_ids[:1])

        print(f"Found {len(annotations)} annotations for {len(topic_ids[:1])} topic(s)")

        # Group annotations by topic
        by_topic = {}
        for ann in annotations:
            topic_id = ann.get("topic_id")
            if topic_id:
                if topic_id not in by_topic:
                    by_topic[topic_id] = []
                by_topic[topic_id].append(ann)

        for topic_id, topic_annotations in by_topic.items():
            print(f"\nTopic ID: {topic_id}")
            print(f"  Annotations: {len(topic_annotations)}")

            # Calculate average scores (scores are now objects with 'score' field)
            if topic_annotations:
                relevance_scores = [
                    a["annotation"]["scores"].get("relevance", {}).get("score", 0)
                    for a in topic_annotations
                ]
                impact_scores = [
                    a["annotation"]["scores"].get("impact", {}).get("score", 0)
                    for a in topic_annotations
                ]

                avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
                avg_impact = sum(impact_scores) / len(impact_scores) if impact_scores else 0

                print(f"  Average Relevance Score: {avg_relevance:.2f}")
                print(f"  Average Impact Score: {avg_impact:.2f}")

            # Show first few objectives
            print("  Recent objectives:")
            for ann in topic_annotations[:3]:
                impact_summary = ann.get("annotation", {}).get("metadata", {}).get("impact_summary", {})
                objective = impact_summary.get("objective", "N/A")
                obj_preview = objective[:100] + "..." if len(objective) > 100 else objective
                print(f"    - {obj_preview}")

    except ValueError as e:
        print(f"Validation Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 3: Fetch annotations by user IDs
    print("=== Example 3: Fetch Annotations by User IDs ===")
    print("Note: User IDs must be provided manually (replace 'your-user-id-here')\n")

    # User IDs cannot be auto-fetched - must be provided manually
    user_ids = ["your-user-id-here"]

    try:
        annotations = client.get_annotations(user_ids=user_ids)

        print(f"Found {len(annotations)} annotations for {len(user_ids)} user(s)")

        if annotations:
            # Analyze update types
            update_types = {}
            for ann in annotations:
                update_type = ann.get("annotation", {}).get("classification", {}).get("update_type", "Unknown")
                update_types[update_type] = update_types.get(update_type, 0) + 1

            print("\nAnnotation update types:")
            for update_type, count in sorted(update_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {update_type}: {count}")

            # Show high-impact annotations (impact score > 5)
            high_impact = [
                ann for ann in annotations
                if ann.get("annotation", {}).get("scores", {}).get("impact", {}).get("score", 0) > 5
            ]

            if high_impact:
                print(f"\nHigh-impact annotations ({len(high_impact)}):")
                for ann in high_impact[:5]:
                    impact_obj = ann.get("annotation", {}).get("scores", {}).get("impact", {})
                    impact_score = impact_obj.get("score", 0)
                    impact_label = impact_obj.get("label", "N/A")
                    objective = ann.get("annotation", {}).get("metadata", {}).get("impact_summary", {}).get("objective", "N/A")
                    obj_preview = objective[:80] + "..." if len(objective) > 80 else objective
                    print(f"  [{impact_label}, score: {impact_score}] {obj_preview}")

    except ValueError as e:
        print(f"Validation Error: {e}")
        print("Expected: Replace 'your-user-id-here' with a valid user UUID")
    except Exception as e:
        print(f"Error: {e}")
        print("Expected: User ID 'your-user-id-here' is a placeholder")

    print("\n" + "=" * 60 + "\n")

    # Example 4: Error handling - only one filter allowed
    print("=== Example 4: Error Handling - Single Filter Only ===")

    try:
        # This will raise a ValueError
        annotations = client.get_annotations(feed_entry_ids=["entry-1"], topic_ids=["topic-1"])
    except ValueError as e:
        print(f"Expected error: {e}")
        print("\nNote: Only one filter type can be used per request")

    print("\n" + "=" * 60 + "\n")

    # Example 5: Error handling - empty filter lists
    print("=== Example 5: Error Handling - Empty Filter Lists ===")

    try:
        # This will raise a ValueError
        annotations = client.get_annotations(feed_entry_ids=[])
    except ValueError as e:
        print(f"Expected error: {e}")
        print("\nNote: Filter lists cannot be empty")

    print("\n" + "=" * 60 + "\n")

    # Example 6: Working with annotation scores
    print("=== Example 6: Filtering and Sorting by Scores ===")
    print(f"Using {len(feed_entry_ids[:3])} feed entries\n")

    try:
        # Use first 3 feed entries
        annotations = client.get_annotations(feed_entry_ids=feed_entry_ids[:3])

        if annotations:
            # Sort by relevance score (now need to extract score from object)
            sorted_by_relevance = sorted(
                annotations,
                key=lambda x: x.get("annotation", {}).get("scores", {}).get("relevance", {}).get("score", 0),
                reverse=True,
            )

            print("Annotations sorted by relevance score:")
            for ann in sorted_by_relevance[:5]:
                relevance_obj = ann.get("annotation", {}).get("scores", {}).get("relevance", {})
                relevance_score = relevance_obj.get("score", 0)
                relevance_label = relevance_obj.get("label", "N/A")
                entry_id = ann["feed_entry_id"]
                objective = ann.get("annotation", {}).get("metadata", {}).get("impact_summary", {}).get("objective", "N/A")
                obj_preview = objective[:60] + "..." if len(objective) > 60 else objective
                print(f"  [{relevance_label}, {relevance_score:.1f}] {entry_id[:8]}... - {obj_preview}")

            # Filter by high relevance confidence
            confidence_threshold = 0.90
            high_confidence = [
                ann
                for ann in annotations
                if ann.get("annotation", {}).get("scores", {}).get("relevance", {}).get("confidence", 0) >= confidence_threshold
            ]

            print(f"\nHigh-confidence relevance scores (>= {confidence_threshold}):")
            print(f"  Found {len(high_confidence)} out of {len(annotations)} total")

        else:
            print("No annotations found for the provided feed entry IDs")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 7: Analyzing tags across annotations
    print("=== Example 7: Tag Analysis ===")
    print(f"Using first topic from the API\n")

    try:
        # Use first topic
        annotations = client.get_annotations(topic_ids=topic_ids[:1])

        if annotations:
            # Collect all tags (tags are in metadata.tags, not classification)
            all_tags = []
            for ann in annotations:
                tags = ann.get("annotation", {}).get("metadata", {}).get("tags", [])
                all_tags.extend(tags)

            if all_tags:
                # Count tag frequencies
                from collections import Counter

                tag_counts = Counter(all_tags)

                print(f"Tag frequency distribution ({len(tag_counts)} unique tags):")
                for tag, count in tag_counts.most_common(10):
                    print(f"  - {tag}: {count}")
            else:
                print("No tags found in annotations")
        else:
            print("No annotations found for the provided topic IDs")

    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("\nExamples complete!")
    print("\nNext steps:")
    print("  1. Explore different topic combinations")
    print("  2. Add user IDs to test user-based annotation filtering")
    print("  3. Build custom analytics using annotation data")
    print("  4. Export annotations to pandas DataFrames for deeper analysis")
    print("=" * 60)


if __name__ == "__main__":
    main()
