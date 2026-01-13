# Carver Feeds SDK Examples

This directory contains example scripts and comprehensive usage documentation for the Carver Feeds SDK.

---

## Table of Contents

### Quick Start
- [Prerequisites](#prerequisites)
- [Running Example Scripts](#running-example-scripts)

### Comprehensive Examples
1. [Example 1: List All Topics](#example-1-list-all-topics)
2. [Example 2: Search Entries in a Topic](#example-2-search-entries-in-a-topic)
3. [Example 3: Complex Multi-Filter Query](#example-3-complex-multi-filter-query)
4. [Example 4: Export Results to Different Formats](#example-4-export-results-to-different-formats)
5. [Example 5: Date Range Analysis](#example-5-date-range-analysis)
6. [Example 6: Multi-Topic Comparison](#example-6-multi-topic-comparison)

### Additional Resources
- [Tips for Effective Usage](#tips-for-effective-usage)
- [Common Workflows](#common-workflows)
- [Getting Help](#getting-help)

---

## Prerequisites

1. Install the SDK:
   ```bash
   pip install carver-feeds-sdk
   ```

2. Create a `.env` file in your working directory:
   ```bash
   CARVER_API_KEY=your_api_key_here
   CARVER_BASE_URL=https://app.carveragents.ai  # optional

   # NEW in v0.2.0: S3 Content Fetching (optional)
   AWS_PROFILE_NAME=your-aws-profile  # optional, for S3 content
   AWS_REGION=us-east-1  # optional, defaults to us-east-1
   ```

3. (Optional) For S3 content fetching, configure AWS credentials:
   ```bash
   # Create/edit ~/.aws/credentials
   [your-aws-profile]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

---

## Running Example Scripts

This directory contains runnable Python scripts demonstrating SDK features:

### Basic Usage

Demonstrates fundamental SDK operations:

```bash
python basic_usage.py
```

Features:
- Direct API client usage
- DataFrame operations
- Fetching topics and entries
- **NEW in v0.2.0**: S3 content fetching

### Advanced Queries

Shows advanced querying capabilities:

```bash
python advanced_queries.py
```

Features:
- Method chaining
- Multi-filter queries
- Keyword search
- Date range filtering
- Export to CSV/JSON
- **NEW in v0.2.0**: Lazy loading with S3 content

### S3 Content Fetching (v0.2.0+)

Demonstrates S3 content fetching capabilities:

```bash
python s3_content_fetching.py
```

Features:
- **NEW in v0.2.0**: S3 client configuration and setup
- **NEW in v0.2.0**: Eager loading (fetch content immediately)
- **NEW in v0.2.0**: Lazy loading (filter first, fetch later)
- **NEW in v0.2.0**: Direct S3 client usage
- **NEW in v0.2.0**: Batch fetching with parallel workers
- **NEW in v0.2.0**: Working with extracted_metadata fields

**Note:** Requires AWS credentials configured. See prerequisites above.

---

# Comprehensive Usage Examples

The following examples provide detailed, copy-paste code for common use cases.

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

## Example 2: Search Entries in a Topic

**Scenario**: You want to search for "compliance" in entries from the Banking topic.

**Code**:
```python
from carver_feeds import create_query_engine

qe = create_query_engine()

# Search for compliance in banking entries (title/description, no S3 required)
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .search_entries("compliance", search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

print(f"Found {len(results)} entries about compliance in Banking topic\n")

# Display sample entries
if len(results) > 0:
    print("Sample entries:")
    for idx, row in results.head(3).iterrows():
        print(f"\nTitle: {row['entry_title']}")
        print(f"Published: {row['entry_published_at']}")
        print(f"Link: {row['entry_link']}")
        if row.get('entry_description'):
            print(f"Description: {row['entry_description'][:150]}...")
```

**Expected Output**:
```
Found 387 entries about compliance in Banking topic

Sample entries:

Title: SEC Announces New Compliance Requirements for Investment Advisers
Published: 2024-10-20 15:00:00
Link: https://www.sec.gov/news/press-release/2024-145
Description: The Securities and Exchange Commission today announced new compliance requirements for investment advisers focusing on cybersecurity and risk management...

Title: FDIC Issues Guidance on Compliance with New Capital Standards
Published: 2024-10-18 09:30:00
Link: https://www.fdic.gov/news/press-releases/2024/pr24178.html
Description: The Federal Deposit Insurance Corporation issued new guidance for banks on compliance with updated capital adequacy standards...
...
```

**Use Cases**:
- Topic-wide research: Understanding how a keyword appears in a regulatory topic
- Quick monitoring: Finding relevant updates without fetching full content
- Efficient searching: Working without AWS credentials

**Variation - Search in Full Content (requires S3)**:
```python
# Search in full article content (requires AWS credentials configured)
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .fetch_content() \
    .search_entries("compliance") \
    .to_dataframe()

print(f"Found {len(results)} entries with 'compliance' in full content")

# Show content snippet
for idx, row in results.head(2).iterrows():
    print(f"\nTitle: {row['entry_title']}")
    if row.get('entry_content_markdown'):
        # Find keyword in content
        content = row['entry_content_markdown']
        keyword_pos = content.lower().find('compliance')
        if keyword_pos != -1:
            start = max(0, keyword_pos - 50)
            end = min(len(content), keyword_pos + 100)
            snippet = content[start:end].replace('\n', ' ')
            print(f"Context: ...{snippet}...")
```

**Variation - Multiple Topics**:
```python
# Search across multiple topics
banking_results = qe.filter_by_topic(topic_name="Banking") \
    .search_entries("compliance", search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()
healthcare_results = qe.chain().filter_by_topic(topic_name="Healthcare") \
    .search_entries("compliance", search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

import pandas as pd
all_results = pd.concat([banking_results, healthcare_results])

print(f"Total compliance mentions: {len(all_results)}")
print(f"Banking: {len(banking_results)}, Healthcare: {len(healthcare_results)}")
```

---

## Example 3: Complex Multi-Filter Query

**Scenario**: You want to find recent active entries from Banking topic that mention both "regulation" AND "fintech", published in the last 3 months.

**Code**:
```python
from carver_feeds import create_query_engine
from datetime import datetime, timedelta

qe = create_query_engine()

# Calculate date 3 months ago
three_months_ago = datetime.now() - timedelta(days=90)

# Build complex query with multiple filters (search in title/description)
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_active(is_active=True) \
    .filter_by_date(start_date=three_months_ago) \
    .search_entries(["regulation", "fintech"], match_all=True,
                   search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

print(f"Found {len(results)} recent banking entries about fintech regulation\n")

if len(results) > 0:
    # Sort by date (most recent first)
    results_sorted = results.sort_values('entry_published_at', ascending=False)

    print("Most recent entries:")
    for idx, row in results_sorted.head(5).iterrows():
        print(f"\n{'='*80}")
        print(f"Title: {row['entry_title']}")
        print(f"Topic: {row['topic_name']}")
        print(f"Published: {row['entry_published_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"Link: {row['entry_link']}")

        # Show description if available
        if row.get('entry_description'):
            preview = row['entry_description'][:300].replace('\n', ' ')
            print(f"Preview: {preview}...")

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
Topic: Banking Regulation
Published: 2024-10-22 14:30
Link: https://www.federalreserve.gov/newsevents/pressreleases/2024/20241022a.htm
Preview: The Federal Reserve Board today issued final guidance on managing risks in third-party fintech relationships. The regulation addresses key areas including due diligence, ongoing monitoring, and risk management...

================================================================================
Title: OCC Announces Fintech Charter Regulation Framework
Topic: Banking Regulation
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
    .search_entries(["regulation", "fintech"], match_all=False,
                   search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

print(f"Found {len(results)} entries (OR logic - broader results)")
```

---

## Example 4: Export Results to Different Formats

**Scenario**: You want to export search results in multiple formats for different uses (analysis, reporting, API integration).

**Code**:
```python
from carver_feeds import create_query_engine
import json

qe = create_query_engine()

# Perform search (in title/description, no S3 required)
print("Searching for healthcare compliance entries...")
qe.filter_by_topic(topic_name="Healthcare") \
    .search_entries("compliance", search_fields=['entry_title', 'entry_description'])

# Export Format 1: Pandas DataFrame (for further Python analysis)
df = qe.to_dataframe()
print(f"\n1. DataFrame: {len(df)} rows × {len(df.columns)} columns")
print(f"   Columns: {', '.join(df.columns[:5])}...")

# Analyze in pandas
print(f"\n   Sample analysis:")
print(f"   - Date range: {df['entry_published_at'].min()} to {df['entry_published_at'].max()}")
print(f"   - Topics: {df['topic_name'].unique()}")

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
df_minimal = df[['entry_title', 'entry_link', 'entry_published_at', 'topic_name']]
df_minimal.to_csv('healthcare_compliance_minimal.csv', index=False)
print(f"\n5. Minimal CSV: healthcare_compliance_minimal.csv")
print(f"   Columns: {', '.join(df_minimal.columns)}")
```

**Expected Output**:
```
Searching for healthcare compliance entries...

1. DataFrame: 156 rows × 23 columns
   Columns: topic_id, topic_name, topic_description, entry_id, entry_title...

   Sample analysis:
   - Date range: 2024-01-05 08:30:00 to 2024-10-24 16:45:00
   - Topics: ['Healthcare Compliance' 'Medical Devices' 'FDA Regulations']

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
   Columns: entry_title, entry_link, entry_published_at, topic_name
```

**Use Cases**:
- Multi-format export: Preparing data for different stakeholders
- Integration: Feeding data to other systems
- Reporting: Creating reports in various formats
- Archival: Saving search results for later reference

---

## Example 5: Date Range Analysis

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
        # Topic analysis
        print(f"  Entries published this quarter")

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
  Entries published this quarter

Q2 2024 (2024-04-01 to 2024-06-30):
  Total entries: 267
  Entries published this quarter

Q3 2024 (2024-07-01 to 2024-09-30):
  Total entries: 198
  Entries published this quarter

Q4 2024 (2024-10-01 to 2024-12-31):
  Total entries: 145
  Entries published this quarter

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

## Example 6: Multi-Topic Comparison

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
            'Date Range': f"{results['entry_published_at'].min().date()} to {results['entry_published_at'].max().date()}",
            'Avg Entries/Day': round(len(results) / 180, 2)
        })

        print(f"\n{topic}:")
        print(f"  Entries: {len(results)}")
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
  Avg per day: 2.71

Healthcare:
  Entries: 356
  Avg per day: 1.98

Energy:
  Entries: 234
  Avg per day: 1.3

Technology:
  Entries: 189
  Avg per day: 1.05

Environment:
  Entries: 412
  Avg per day: 2.29

======================================================================

Summary Table:
        Topic  Total Entries               Date Range  Avg Entries/Day
      Banking            487  2024-04-25 to 2024-10-24             2.71
   Healthcare            356  2024-04-26 to 2024-10-24             1.98
       Energy            234  2024-04-27 to 2024-10-23             1.30
   Technology            189  2024-04-28 to 2024-10-22             1.05
  Environment            412  2024-04-25 to 2024-10-24             2.29


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
# Partial, case-insensitive match
qe.filter_by_topic(topic_name="bank")      # Matches "Banking", "Bank Regulation", etc.
```

### 5. Combine AND/OR Logic Strategically
```python
# Use AND (match_all=True) for precise queries
narrow = qe.filter_by_topic(topic_name="Banking") \
    .search_entries(["banking", "regulation", "fintech"], match_all=True,
                   search_fields=['entry_title', 'entry_description'])

# Use OR (match_all=False) for broad queries
broad = qe.filter_by_topic(topic_name="Banking") \
    .search_entries(["banking", "finance", "credit"], match_all=False,
                   search_fields=['entry_title', 'entry_description'])
```

### 6. Specify Search Fields for Faster Queries
```python
# Fast: Search in title/description (no S3 required)
results = qe.filter_by_topic(topic_name="Banking") \
    .search_entries("regulation", search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

# Slower but comprehensive: Search in full content (requires S3)
results = qe.filter_by_topic(topic_name="Banking") \
    .fetch_content() \
    .search_entries("regulation") \
    .to_dataframe()
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

# Get yesterday's entries (must filter by topic first)
results = qe \
    .filter_by_topic(topic_name="Banking") \
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

# Monitor specific keywords in Banking topic
alerts = ["cryptocurrency", "fintech", "digital assets"]

for keyword in alerts:
    results = qe.chain() \
        .filter_by_topic(topic_name="Banking") \
        .search_entries(keyword, search_fields=['entry_title', 'entry_description']) \
        .to_dataframe()

    if len(results) > 0:
        print(f"\nALERT: {len(results)} new mentions of '{keyword}' in Banking")
        print(results[['topic_name', 'entry_title', 'entry_link']].head(3))
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

# 2. Get all entries for the topic
entries = qe.filter_by_topic(topic_name=topic_name).to_dataframe()

# 3. Analyze and export
print(f"Topic: {topic_name}")
print(f"Entries: {len(entries)}")
print(f"Date range: {entries['entry_published_at'].min()} to {entries['entry_published_at'].max()}")

entries.to_csv(f'{topic_name.lower()}_deep_dive.csv', index=False)
```

---

## Getting Help

- **Main Documentation**: [../README.md](../README.md)
- **API Reference**: [../docs/api-reference.md](../docs/api-reference.md)
- **Issues**: [GitHub Issues](https://github.com/carveragents/carver-feeds-sdk/issues)

---

**Document Version**: 2.0
**Last Updated**: 2025-01-12
**SDK Version**: 0.2.0+
**Status**: Production Ready
