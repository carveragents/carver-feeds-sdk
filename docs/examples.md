# Carver Feeds SDK - Usage Examples

This document provides practical, copy-paste examples for common use cases of the Carver Feeds SDK.

---

## Table of Contents

1. [Example 1: List All Topics](#example-1-list-all-topics)
2. [Example 2: List Feeds for a Topic](#example-2-list-feeds-for-a-topic)
3. [Example 3: Search Feed Entries by Keyword](#example-3-search-feed-entries-by-keyword)
4. [Example 4: Search Entries Across All Feeds in a Topic](#example-4-search-entries-across-all-feeds-in-a-topic)
5. [Example 5: Complex Multi-Filter Query](#example-5-complex-multi-filter-query)
6. [Example 6: Export Results to Different Formats](#example-6-export-results-to-different-formats)
7. [Example 7: Date Range Analysis](#example-7-date-range-analysis)
8. [Example 8: Multi-Topic Comparison](#example-8-multi-topic-comparison)
9. [Example 9: Feed Activity Analysis](#example-9-feed-activity-analysis)

---

## Example 1: List All Topics

**Scenario**: You want to see what regulatory topics are available in the system.

**Code**:
```python
from carver_feeds import create_data_manager

# Initialize data manager
dm = create_data_manager()

# Fetch all topics
topics_df = dm.get_topics_df()

# Display summary
print(f"Total topics available: {len(topics_df)}")
print(f"Active topics: {topics_df['is_active'].sum()}")
print(f"Inactive topics: {(~topics_df['is_active']).sum()}")

# Show topic list
print("\nAvailable Topics:")
print(topics_df[['id', 'name', 'description', 'is_active']].head(20))
```

**Expected Output**:
```
Total topics available: 114
Active topics: 108
Inactive topics: 6

Available Topics:
                    id                           name                           description  is_active
0           topic-123                Banking Regulation  Updates on banking and financial...       True
1           topic-456          Healthcare Compliance  Healthcare regulatory changes...            True
2           topic-789         Environmental Standards  Environmental protection updates...        True
...
```

**Use Cases**:
- Exploration: Understanding what data is available
- Topic selection: Choosing topics for detailed analysis
- System overview: Getting a high-level view of regulatory domains

---

## Example 2: List Feeds for a Topic

**Scenario**: You want to see all RSS feeds available for a specific regulatory topic (e.g., Banking).

**Code**:
```python
from carver_feeds import create_data_manager

dm = create_data_manager()

# Get all topics to find the one we want
topics_df = dm.get_topics_df()

# Find banking topic (partial name match)
banking_topics = topics_df[
    topics_df['name'].str.contains('Banking', case=False, na=False)
]

if len(banking_topics) == 0:
    print("No banking topics found")
else:
    # Get the first matching topic
    topic_id = banking_topics['id'].iloc[0]
    topic_name = banking_topics['name'].iloc[0]

    print(f"Found topic: {topic_name} (ID: {topic_id})")

    # Fetch feeds for this topic
    feeds_df = dm.get_feeds_df(topic_id=topic_id)

    print(f"\nTotal feeds in '{topic_name}': {len(feeds_df)}")
    print(f"Active feeds: {feeds_df['is_active'].sum()}")

    # Display feed details
    print(f"\nFeeds in '{topic_name}':")
    print(feeds_df[['id', 'name', 'url', 'is_active']].head(10))
```

**Expected Output**:
```
Found topic: Banking Regulation (ID: topic-banking-123)

Total feeds in 'Banking Regulation': 47
Active feeds: 45

Feeds in 'Banking Regulation':
                    id                           name                                    url  is_active
0           feed-001                      SEC News Feed  https://www.sec.gov/news/rss           True
1           feed-002                  FDIC Press Releases  https://www.fdic.gov/news/rss         True
2           feed-003      Federal Reserve Board Updates  https://www.federalreserve.gov/rss    True
...
```

**Use Cases**:
- Feed discovery: Finding relevant RSS feeds for a topic
- Data source identification: Understanding where regulatory updates come from
- Feed filtering: Selecting specific feeds for monitoring

**Alternative - Using Query Engine**:
```python
from carver_feeds import create_query_engine

qe = create_query_engine()

# Filter feeds by topic name (partial match)
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Get unique feeds
feeds = results[['feed_id', 'feed_name', 'feed_url']].drop_duplicates()
print(f"Feeds in Banking topics: {len(feeds)}")
print(feeds.head(10))
```

---

## Example 3: Search Feed Entries by Keyword

**Scenario**: You want to find all entries from a specific feed that mention a keyword (e.g., "SEC News" feed with "cryptocurrency").

**Code**:
```python
from carver_feeds import create_query_engine

qe = create_query_engine()

# Search for cryptocurrency in SEC News feed
results = qe \
    .filter_by_feed(feed_name="SEC News") \
    .search_entries("cryptocurrency") \
    .to_dataframe()

print(f"Found {len(results)} entries in SEC News mentioning 'cryptocurrency'\n")

# Display key information
if len(results) > 0:
    print("Recent entries:")
    for idx, row in results.head(5).iterrows():
        print(f"\nTitle: {row['entry_title']}")
        print(f"Published: {row['entry_published_at']}")
        print(f"Link: {row['entry_link']}")
        print(f"Preview: {row['entry_content_markdown'][:200]}...")
else:
    print("No entries found. Try broadening your search.")
```

**Expected Output**:
```
Found 23 entries in SEC News mentioning 'cryptocurrency'

Recent entries:

Title: SEC Charges Cryptocurrency Exchange for Unregistered Securities
Published: 2024-10-15 14:30:00
Link: https://www.sec.gov/news/press-release/2024-123
Preview: The Securities and Exchange Commission today charged a major cryptocurrency exchange with operating as an unregistered securities exchange, broker, and clearing agency...

Title: SEC Proposes New Rules for Crypto Asset Custody
Published: 2024-09-28 10:00:00
Link: https://www.sec.gov/news/press-release/2024-118
Preview: The Securities and Exchange Commission today proposed amendments to rules governing the custody of crypto assets by registered investment advisers...
...
```

**Use Cases**:
- Topic monitoring: Tracking specific keywords in regulatory feeds
- Research: Finding all mentions of a subject in a feed
- Alert generation: Identifying relevant updates

**Variation - Case-Sensitive Search**:
```python
# Search for exact case match (e.g., "SEC" vs "sec")
results = qe \
    .filter_by_feed(feed_name="Banking News") \
    .search_entries("SEC", case_sensitive=True) \
    .to_dataframe()
```

**Variation - Multiple Keywords (OR logic)**:
```python
# Find entries mentioning ANY of the keywords
results = qe \
    .filter_by_feed(feed_name="SEC News") \
    .search_entries(["cryptocurrency", "blockchain", "digital assets"], match_all=False) \
    .to_dataframe()

print(f"Found {len(results)} entries mentioning crypto-related terms")
```

---

## Example 4: Search Entries Across All Feeds in a Topic

**Scenario**: You want to search for "compliance" across all feeds in the Banking topic.

**Code**:
```python
from carver_feeds import create_query_engine

qe = create_query_engine()

# Search for compliance in all banking feeds
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .search_entries("compliance") \
    .to_dataframe()

print(f"Found {len(results)} entries about compliance in Banking topic\n")

# Analyze by feed
if len(results) > 0:
    feed_counts = results.groupby('feed_name').size().sort_values(ascending=False)
    print("Top 10 feeds by number of compliance mentions:")
    print(feed_counts.head(10))

    print("\n\nSample entries:")
    for idx, row in results.head(3).iterrows():
        print(f"\nFeed: {row['feed_name']}")
        print(f"Title: {row['entry_title']}")
        print(f"Published: {row['entry_published_at']}")
        print(f"Link: {row['entry_link']}")
```

**Expected Output**:
```
Found 387 entries about compliance in Banking topic

Top 10 feeds by number of compliance mentions:
feed_name
SEC News Feed                           87
FDIC Press Releases                    62
Federal Reserve Board Updates          54
OCC Bulletins                          43
CFPB Updates                          38
FinCEN Notices                        31
...

Sample entries:

Feed: SEC News Feed
Title: SEC Announces New Compliance Requirements for Investment Advisers
Published: 2024-10-20 15:00:00
Link: https://www.sec.gov/news/press-release/2024-145

Feed: FDIC Press Releases
Title: FDIC Issues Guidance on Compliance with New Capital Standards
Published: 2024-10-18 09:30:00
Link: https://www.fdic.gov/news/press-releases/2024/pr24178.html
...
```

**Use Cases**:
- Topic-wide research: Understanding how a keyword appears across multiple sources
- Comparative analysis: Seeing which feeds cover a topic most
- Comprehensive monitoring: Not missing updates from any feed in a topic

**Variation - Multiple Topics**:
```python
# Search across multiple topics
banking_results = qe.filter_by_topic(topic_name="Banking").search_entries("compliance").to_dataframe()
healthcare_results = qe.chain().filter_by_topic(topic_name="Healthcare").search_entries("compliance").to_dataframe()

import pandas as pd
all_results = pd.concat([banking_results, healthcare_results])

print(f"Total compliance mentions: {len(all_results)}")
print(f"Banking: {len(banking_results)}, Healthcare: {len(healthcare_results)}")
```

---

## Example 5: Complex Multi-Filter Query

**Scenario**: You want to find recent active entries from Banking topic that mention both "regulation" AND "fintech", published in the last 3 months.

**Code**:
```python
from carver_feeds import create_query_engine
from datetime import datetime, timedelta

qe = create_query_engine()

# Calculate date 3 months ago
three_months_ago = datetime.now() - timedelta(days=90)

# Build complex query with multiple filters
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_active(is_active=True) \
    .filter_by_date(start_date=three_months_ago) \
    .search_entries(["regulation", "fintech"], match_all=True) \
    .to_dataframe()

print(f"Found {len(results)} recent banking entries about fintech regulation\n")

if len(results) > 0:
    # Sort by date (most recent first)
    results_sorted = results.sort_values('entry_published_at', ascending=False)

    print("Most recent entries:")
    for idx, row in results_sorted.head(5).iterrows():
        print(f"\n{'='*80}")
        print(f"Title: {row['entry_title']}")
        print(f"Feed: {row['feed_name']}")
        print(f"Published: {row['entry_published_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"Link: {row['entry_link']}")

        # Show snippet of content
        content_preview = row['entry_content_markdown'][:300].replace('\n', ' ')
        print(f"Preview: {content_preview}...")

    # Export to CSV for further analysis
    csv_path = results.to_csv("banking_fintech_regulations.csv")
    print(f"\n\nFull results exported to: {csv_path}")
else:
    print("No results found. Try:")
    print("- Using OR logic (match_all=False)")
    print("- Expanding date range")
    print("- Removing some filters")
```

**Expected Output**:
```
Found 12 recent banking entries about fintech regulation

Most recent entries:

================================================================================
Title: Federal Reserve Issues New Guidance on Fintech Partnerships
Feed: Federal Reserve Board Updates
Published: 2024-10-22 14:30
Link: https://www.federalreserve.gov/newsevents/pressreleases/2024/20241022a.htm
Preview: The Federal Reserve Board today issued final guidance on managing risks in third-party fintech relationships. The regulation addresses key areas including due diligence, ongoing monitoring, and risk management...

================================================================================
Title: OCC Announces Fintech Charter Regulation Framework
Feed: OCC Bulletins
Published: 2024-10-15 10:00
Link: https://www.occ.gov/news-issuances/bulletins/2024/bulletin-2024-45.html
Preview: The Office of the Comptroller of the Currency today released a comprehensive framework for regulating fintech companies seeking national bank charters. The new regulation establishes clear requirements...

...

Full results exported to: /Users/username/banking_fintech_regulations.csv
```

**Use Cases**:
- Targeted research: Very specific queries combining multiple criteria
- Trend analysis: Finding recent developments in specific areas
- Compliance monitoring: Tracking new regulations in specific domains

**Variation - OR Logic for Broader Results**:
```python
# Find entries mentioning regulation OR fintech (not necessarily both)
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_active(is_active=True) \
    .filter_by_date(start_date=three_months_ago) \
    .search_entries(["regulation", "fintech"], match_all=False) \
    .to_dataframe()

print(f"Found {len(results)} entries (OR logic - broader results)")
```

---

## Example 6: Export Results to Different Formats

**Scenario**: You want to export search results in multiple formats for different uses (analysis, reporting, API integration).

**Code**:
```python
from carver_feeds import create_query_engine
import json

qe = create_query_engine()

# Perform search
print("Searching for healthcare compliance entries...")
qe.filter_by_topic(topic_name="Healthcare").search_entries("compliance")

# Export Format 1: Pandas DataFrame (for further Python analysis)
df = qe.to_dataframe()
print(f"\n1. DataFrame: {len(df)} rows × {len(df.columns)} columns")
print(f"   Columns: {', '.join(df.columns[:5])}...")

# Analyze in pandas
print(f"\n   Sample analysis:")
print(f"   - Date range: {df['entry_published_at'].min()} to {df['entry_published_at'].max()}")
print(f"   - Unique feeds: {df['feed_name'].nunique()}")

# Export Format 2: CSV (for Excel, spreadsheets)
csv_path = qe.to_csv("healthcare_compliance.csv")
print(f"\n2. CSV file: {csv_path}")
print(f"   Use case: Open in Excel, Google Sheets")

# Export Format 3: JSON (for APIs, web applications)
json_str = qe.to_json(indent=2)
print(f"\n3. JSON string: {len(json_str)} characters")
print(f"   Use case: API responses, web apps")

# Save JSON to file
with open('healthcare_compliance.json', 'w') as f:
    f.write(json_str)
print(f"   Saved to: healthcare_compliance.json")

# Export Format 4: Dictionary list (for iteration, custom processing)
dict_list = qe.to_dict()
print(f"\n4. Dictionary list: {len(dict_list)} entries")
print(f"   Use case: Custom processing, iteration")

# Example: Extract just titles and links
for entry in dict_list[:3]:
    print(f"   - {entry['entry_title']}: {entry['entry_link']}")

# Export Format 5: Custom filtered columns to CSV
# Select only specific columns
df_minimal = df[['entry_title', 'entry_link', 'entry_published_at', 'feed_name']]
df_minimal.to_csv('healthcare_compliance_minimal.csv', index=False)
print(f"\n5. Minimal CSV: healthcare_compliance_minimal.csv")
print(f"   Columns: {', '.join(df_minimal.columns)}")
```

**Expected Output**:
```
Searching for healthcare compliance entries...

1. DataFrame: 156 rows × 23 columns
   Columns: topic_id, topic_name, topic_description, feed_id, feed_name...

   Sample analysis:
   - Date range: 2024-01-05 08:30:00 to 2024-10-24 16:45:00
   - Unique feeds: 18

2. CSV file: /Users/username/healthcare_compliance.csv
   Use case: Open in Excel, Google Sheets

3. JSON string: 245678 characters
   Use case: API responses, web apps
   Saved to: healthcare_compliance.json

4. Dictionary list: 156 entries
   Use case: Custom processing, iteration
   - FDA Issues New Drug Approval Compliance Guidelines: https://www.fda.gov/news/2024/123
   - CMS Updates Medicare Compliance Requirements: https://www.cms.gov/newsroom/2024/145
   - HHS Announces HIPAA Compliance Enforcement Changes: https://www.hhs.gov/about/news/2024/178

5. Minimal CSV: healthcare_compliance_minimal.csv
   Columns: entry_title, entry_link, entry_published_at, feed_name
```

**Use Cases**:
- Multi-format export: Preparing data for different stakeholders
- Integration: Feeding data to other systems
- Reporting: Creating reports in various formats
- Archival: Saving search results for later reference

---

## Example 7: Date Range Analysis

**Scenario**: You want to analyze regulatory activity over time, comparing different quarters.

**Code**:
```python
from carver_feeds import create_query_engine
from datetime import datetime
import pandas as pd

qe = create_query_engine()

# Define quarters
quarters = [
    ("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31)),
    ("Q2 2024", datetime(2024, 4, 1), datetime(2024, 6, 30)),
    ("Q3 2024", datetime(2024, 7, 1), datetime(2024, 9, 30)),
    ("Q4 2024", datetime(2024, 10, 1), datetime(2024, 12, 31)),
]

print("Banking Regulation Activity by Quarter (2024)\n")
print("="*60)

all_results = []

for quarter_name, start_date, end_date in quarters:
    # Get entries for this quarter
    results = qe.chain() \
        .filter_by_topic(topic_name="Banking") \
        .filter_by_date(start_date=start_date, end_date=end_date) \
        .to_dataframe()

    print(f"\n{quarter_name} ({start_date.date()} to {end_date.date()}):")
    print(f"  Total entries: {len(results)}")

    if len(results) > 0:
        # Feed activity
        feed_counts = results.groupby('feed_name').size().sort_values(ascending=False)
        print(f"  Active feeds: {len(feed_counts)}")
        print(f"  Top feed: {feed_counts.index[0]} ({feed_counts.iloc[0]} entries)")

        # Add quarter label and store
        results['quarter'] = quarter_name
        all_results.append(results)

# Combine all quarters
if all_results:
    combined = pd.concat(all_results)

    print(f"\n{'='*60}")
    print(f"\nYearly Summary:")
    print(f"  Total entries: {len(combined)}")
    print(f"  Date range: {combined['entry_published_at'].min().date()} to {combined['entry_published_at'].max().date()}")

    # Entries per quarter
    print(f"\n  Entries by quarter:")
    quarter_counts = combined.groupby('quarter').size()
    for quarter, count in quarter_counts.items():
        print(f"    {quarter}: {count}")

    # Export full analysis
    combined.to_csv('banking_regulation_2024_analysis.csv', index=False)
    print(f"\n  Full data exported to: banking_regulation_2024_analysis.csv")
```

**Expected Output**:
```
Banking Regulation Activity by Quarter (2024)

============================================================

Q1 2024 (2024-01-01 to 2024-03-31):
  Total entries: 234
  Active feeds: 23
  Top feed: SEC News Feed (45 entries)

Q2 2024 (2024-04-01 to 2024-06-30):
  Total entries: 267
  Active feeds: 25
  Top feed: Federal Reserve Board Updates (52 entries)

Q3 2024 (2024-07-01 to 2024-09-30):
  Total entries: 198
  Active feeds: 22
  Top feed: FDIC Press Releases (38 entries)

Q4 2024 (2024-10-01 to 2024-12-31):
  Total entries: 145
  Active feeds: 19
  Top feed: OCC Bulletins (31 entries)

============================================================

Yearly Summary:
  Total entries: 844
  Date range: 2024-01-03 to 2024-10-24

  Entries by quarter:
    Q1 2024: 234
    Q2 2024: 267
    Q3 2024: 198
    Q4 2024: 145

  Full data exported to: banking_regulation_2024_analysis.csv
```

**Use Cases**:
- Trend analysis: Understanding regulatory activity over time
- Reporting: Creating periodic reports
- Seasonal patterns: Identifying when regulatory activity peaks
- Planning: Forecasting future regulatory updates

---

## Example 8: Multi-Topic Comparison

**Scenario**: You want to compare regulatory activity across different topics to understand which areas are most active.

**Code**:
```python
from carver_feeds import create_query_engine
from datetime import datetime, timedelta
import pandas as pd

qe = create_query_engine()

# Topics to compare
topics_to_compare = ["Banking", "Healthcare", "Energy", "Technology", "Environment"]

# Date range: last 6 months
six_months_ago = datetime.now() - timedelta(days=180)

print("Regulatory Activity Comparison (Last 6 Months)")
print("="*70)

comparison_data = []

for topic in topics_to_compare:
    # Get recent entries for this topic
    results = qe.chain() \
        .filter_by_topic(topic_name=topic) \
        .filter_by_active(is_active=True) \
        .filter_by_date(start_date=six_months_ago) \
        .to_dataframe()

    if len(results) > 0:
        comparison_data.append({
            'Topic': topic,
            'Total Entries': len(results),
            'Active Feeds': results['feed_id'].nunique(),
            'Date Range': f"{results['entry_published_at'].min().date()} to {results['entry_published_at'].max().date()}",
            'Avg Entries/Day': round(len(results) / 180, 2)
        })

        print(f"\n{topic}:")
        print(f"  Entries: {len(results)}")
        print(f"  Active feeds: {results['feed_id'].nunique()}")
        print(f"  Avg per day: {round(len(results) / 180, 2)}")
    else:
        print(f"\n{topic}: No data found")

# Create comparison DataFrame
if comparison_data:
    comparison_df = pd.DataFrame(comparison_data)

    print(f"\n{'='*70}")
    print("\nSummary Table:")
    print(comparison_df.to_string(index=False))

    # Sort by activity
    print("\n\nTopics by Activity (Most Active First):")
    sorted_df = comparison_df.sort_values('Total Entries', ascending=False)
    for idx, row in sorted_df.iterrows():
        print(f"  {row['Topic']}: {row['Total Entries']} entries ({row['Avg Entries/Day']} per day)")

    # Export comparison
    comparison_df.to_csv('topic_comparison.csv', index=False)
    print(f"\nComparison exported to: topic_comparison.csv")
```

**Expected Output**:
```
Regulatory Activity Comparison (Last 6 Months)
======================================================================

Banking:
  Entries: 487
  Active feeds: 31
  Avg per day: 2.71

Healthcare:
  Entries: 356
  Active feeds: 24
  Avg per day: 1.98

Energy:
  Entries: 234
  Active feeds: 18
  Avg per day: 1.3

Technology:
  Entries: 189
  Active feeds: 15
  Avg per day: 1.05

Environment:
  Entries: 412
  Active feeds: 27
  Avg per day: 2.29

======================================================================

Summary Table:
        Topic  Total Entries  Active Feeds               Date Range  Avg Entries/Day
      Banking            487            31  2024-04-25 to 2024-10-24             2.71
   Healthcare            356            24  2024-04-26 to 2024-10-24             1.98
       Energy            234            18  2024-04-27 to 2024-10-23             1.30
   Technology            189            15  2024-04-28 to 2024-10-22             1.05
  Environment            412            27  2024-04-25 to 2024-10-24             2.29


Topics by Activity (Most Active First):
  Banking: 487 entries (2.71 per day)
  Environment: 412 entries (2.29 per day)
  Healthcare: 356 entries (1.98 per day)
  Energy: 234 entries (1.3 per day)
  Technology: 189 entries (1.05 per day)

Comparison exported to: topic_comparison.csv
```

**Use Cases**:
- Portfolio overview: Understanding which regulatory areas are most active
- Resource allocation: Deciding where to focus monitoring efforts
- Comparative analysis: Benchmarking activity across domains
- Reporting: Executive summaries of regulatory landscape

---

## Example 9: Feed Activity Analysis

**Scenario**: You want to understand which feeds are most active and identify feeds that might have stopped publishing.

**Code**:
```python
from carver_feeds import create_data_manager, create_query_engine
from datetime import datetime, timedelta
import pandas as pd

dm = create_data_manager()
qe = create_query_engine()

# Get all feeds
print("Analyzing feed activity...\n")
feeds_df = dm.get_feeds_df()
print(f"Total feeds: {len(feeds_df)}")
print(f"Active feeds: {feeds_df['is_active'].sum()}")

# Get all recent entries
thirty_days_ago = datetime.now() - timedelta(days=30)
recent_entries = qe \
    .filter_by_date(start_date=thirty_days_ago) \
    .filter_by_active(is_active=True) \
    .to_dataframe()

print(f"Entries in last 30 days: {len(recent_entries)}\n")

# Analyze feed activity
if len(recent_entries) > 0:
    feed_activity = recent_entries.groupby(['feed_id', 'feed_name']).agg({
        'entry_id': 'count',
        'entry_published_at': ['min', 'max']
    }).reset_index()

    feed_activity.columns = ['feed_id', 'feed_name', 'entry_count', 'first_entry', 'last_entry']

    # Sort by activity
    feed_activity = feed_activity.sort_values('entry_count', ascending=False)

    print("="*80)
    print("TOP 10 MOST ACTIVE FEEDS (Last 30 Days)")
    print("="*80)

    for idx, row in feed_activity.head(10).iterrows():
        print(f"\n{row['feed_name']}")
        print(f"  Entries: {row['entry_count']}")
        print(f"  Last entry: {row['last_entry'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Avg per day: {round(row['entry_count'] / 30, 2)}")

    # Identify potentially inactive feeds
    print(f"\n{'='*80}")
    print("POTENTIALLY INACTIVE FEEDS")
    print("="*80)
    print("(Active feeds with no entries in last 30 days)\n")

    # Find active feeds without recent entries
    active_feed_ids = set(feeds_df[feeds_df['is_active']]['id'])
    recent_feed_ids = set(recent_entries['feed_id'].unique())
    inactive_feed_ids = active_feed_ids - recent_feed_ids

    if inactive_feed_ids:
        inactive_feeds = feeds_df[feeds_df['id'].isin(inactive_feed_ids)]
        print(f"Found {len(inactive_feeds)} potentially inactive feeds:")

        for idx, feed in inactive_feeds.head(20).iterrows():
            print(f"  - {feed['name']} (Topic: {feed['topic_name']})")
    else:
        print("All active feeds have recent entries.")

    # Export analysis
    feed_activity.to_csv('feed_activity_analysis.csv', index=False)
    print(f"\nFull analysis exported to: feed_activity_analysis.csv")
```

**Expected Output**:
```
Analyzing feed activity...

Total feeds: 827
Active feeds: 798
Entries in last 30 days: 3,456

================================================================================
TOP 10 MOST ACTIVE FEEDS (Last 30 Days)
================================================================================

SEC News Feed
  Entries: 187
  Last entry: 2024-10-24 15:30
  Avg per day: 6.23

Federal Reserve Board Updates
  Entries: 156
  Last entry: 2024-10-24 14:15
  Avg per day: 5.2

FDA News Releases
  Entries: 143
  Last entry: 2024-10-24 16:00
  Avg per day: 4.77

EPA Environmental News
  Entries: 128
  Last entry: 2024-10-24 13:45
  Avg per day: 4.27

...

================================================================================
POTENTIALLY INACTIVE FEEDS
================================================================================
(Active feeds with no entries in last 30 days)

Found 47 potentially inactive feeds:
  - CFTC Historical Archives (Topic: Trading)
  - OSHA Seasonal Bulletins (Topic: Workplace Safety)
  - DOE Quarterly Reports (Topic: Energy)
  ...

Full analysis exported to: feed_activity_analysis.csv
```

**Use Cases**:
- Feed health monitoring: Identifying feeds that may need attention
- Data quality: Understanding which sources are most reliable
- Resource optimization: Focusing on most active feeds
- Anomaly detection: Finding feeds that have stopped publishing

---

## Tips for Effective Usage

### 1. Start Broad, Then Filter
```python
# Start with topic filter, then add more specific filters
qe.filter_by_topic(topic_name="Banking") \    # Broad
  .filter_by_date(start_date=recent_date) \   # More specific
  .search_entries("keyword")                  # Most specific
```

### 2. Use `chain()` to Reset Queries
```python
# First query
results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Reset and start new query
results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
```

### 3. Check Result Counts Before Processing
```python
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

if len(results) == 0:
    print("No results found. Try broadening search.")
else:
    # Process results
    print(f"Found {len(results)} entries")
```

### 4. Use Partial Name Matching
```python
# These are equivalent (partial, case-insensitive match)
qe.filter_by_topic(topic_name="bank")      # Matches "Banking", "Bank Regulation", etc.
qe.filter_by_feed(feed_name="sec")         # Matches "SEC News", "SEC Updates", etc.
```

### 5. Combine AND/OR Logic Strategically
```python
# Use AND (match_all=True) for precise queries
narrow = qe.search_entries(["banking", "regulation", "fintech"], match_all=True)

# Use OR (match_all=False) for broad queries
broad = qe.search_entries(["banking", "finance", "credit"], match_all=False)
```

---

## Common Workflows

### Workflow 1: Daily Regulatory Brief

```python
from carver_feeds import create_query_engine
from datetime import datetime, timedelta

qe = create_query_engine()
yesterday = datetime.now() - timedelta(days=1)
today = datetime.now()

# Get yesterday's entries
results = qe \
    .filter_by_date(start_date=yesterday, end_date=today) \
    .filter_by_active(is_active=True) \
    .to_dataframe()

# Group by topic
topic_summary = results.groupby('topic_name').size().sort_values(ascending=False)
print("Yesterday's Regulatory Updates by Topic:")
print(topic_summary)

# Export for daily brief
results.to_csv(f'daily_brief_{yesterday.strftime("%Y%m%d")}.csv', index=False)
```

### Workflow 2: Keyword Alert System

```python
from carver_feeds import create_query_engine

qe = create_query_engine()

# Monitor specific keywords
alerts = ["cryptocurrency", "climate change", "data privacy"]

for keyword in alerts:
    results = qe.chain().search_entries(keyword).to_dataframe()

    if len(results) > 0:
        print(f"\nALERT: {len(results)} new mentions of '{keyword}'")
        print(results[['feed_name', 'entry_title', 'entry_link']].head(3))
```

### Workflow 3: Topic Deep Dive

```python
from carver_feeds import create_data_manager, create_query_engine

dm = create_data_manager()
qe = create_query_engine()

topic_name = "Banking"

# 1. Get topic metadata
topics = dm.get_topics_df()
topic_info = topics[topics['name'].str.contains(topic_name, case=False)]

# 2. Get feed list
feeds = dm.get_feeds_df(topic_id=topic_info['id'].iloc[0])

# 3. Get all entries
entries = qe.filter_by_topic(topic_name=topic_name).to_dataframe()

# 4. Analyze and export
print(f"Topic: {topic_name}")
print(f"Feeds: {len(feeds)}")
print(f"Entries: {len(entries)}")

entries.to_csv(f'{topic_name.lower()}_deep_dive.csv', index=False)
```

---

**Document Version**: 2.0
**Last Updated**: 2025-10-26
**SDK Version**: 0.1.1+
**Status**: Production Ready
