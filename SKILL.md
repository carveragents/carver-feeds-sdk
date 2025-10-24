---
name: carver-feeds-skill
description: Use this skill when the user needs to fetch, analyze, or query regulatory feed data from the Carver Horizon platform. Supports listing topics/feeds/entries, constructing hierarchical data views, and searching by keywords.
---

# Carver Feeds Skill

## When to Use This Skill

Activate this skill when the user wants to:
- List or explore regulatory topics, feeds, or entries from Carver
- Search feed entries by keywords (e.g., "regulation", "compliance")
- Filter entries by topic, feed, date range, or active status
- Build hierarchical data views showing topic → feed → entry relationships
- Export feed data to CSV, JSON, or pandas DataFrames
- Analyze regulatory feed patterns and trends

## Prerequisites

Before using this skill:

1. **Environment Setup**: Ensure `CARVER_API_KEY` is set in `.env` file
2. **Python Version**: Python 3.10 or higher required
3. **Dependencies**: Install packages from `requirements.txt`
4. **Virtual Environment**: Activate the project's virtual environment

If environment isn't configured, guide user to:
```bash
cp .env.example .env
# Edit .env and add API key
source .venv/bin/activate
```

## Core Operations

### 1. Query and Search Entries

The primary use case is searching and filtering feed entries. Use the `EntryQueryEngine` for all query operations:

```python
from scripts.query_engine import create_query_engine

# Initialize query engine (uses .env for API key)
qe = create_query_engine()

# Search for entries containing keywords
results = qe.search_entries("regulation").to_dataframe()

# Filter by topic
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Chain multiple filters
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries(["regulation", "compliance"]) \
    .to_dataframe()
```

**Important Optimization**: When filtering by feed or topic, the query engine loads only the necessary data to minimize API calls.

### 2. List Topics and Feeds

For metadata exploration, use the `FeedsDataManager`:

```python
from scripts.data_manager import create_data_manager

# Initialize data manager
dm = create_data_manager()

# Get all topics
topics_df = dm.get_topics_df()
print(f"Found {len(topics_df)} topics")
print(topics_df[['id', 'name', 'is_active']].head())

# Get all feeds
feeds_df = dm.get_feeds_df()
print(f"Found {len(feeds_df)} feeds")

# Get feeds for a specific topic
topic_feeds = dm.get_feeds_df(topic_id="topic-123")
```

### 3. Build Hierarchical Views

Construct denormalized views showing the full data hierarchy:

```python
# Topic + Feed hierarchy (fast, no entries)
hierarchy = dm.get_hierarchical_view(include_entries=False)
print(hierarchy[['topic_name', 'feed_name', 'feed_url']].head())

# Full hierarchy for a specific feed (includes entries)
# WARNING: Including all entries is slow. Always filter by feed_id when possible
full_hierarchy = dm.get_hierarchical_view(
    include_entries=True,
    feed_id="feed-456"
)
print(full_hierarchy[['topic_name', 'feed_name', 'entry_title']].head())
```

## Quick Examples

### Example 1: Find Recent Banking Regulations
```python
from scripts.query_engine import create_query_engine
from datetime import datetime

qe = create_query_engine()
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 10, 1)) \
    .search_entries("regulation") \
    .to_dataframe()

print(f"Found {len(results)} banking regulations from Oct 2024")
print(results[['topic_name', 'feed_name', 'entry_title', 'entry_published_at']].head())
```

### Example 2: Export Feed Entries to CSV
```python
qe = create_query_engine()
csv_path = qe \
    .filter_by_feed(feed_name="SEC News") \
    .filter_by_active(is_active=True) \
    .to_csv("sec_news_entries.csv")

print(f"Exported to {csv_path}")
```

### Example 3: Search Across Multiple Keywords
```python
# OR logic: entries containing ANY keyword
results = qe.search_entries(
    ["banking", "regulation", "compliance"],
    match_all=False
).to_dataframe()

# AND logic: entries containing ALL keywords
results = qe.search_entries(
    ["banking", "regulation"],
    match_all=True
).to_dataframe()
```

## Data Volumes and Performance

**Performance Tips**:
1. **Filter by feed or topic first** before loading entries to reduce data volume
2. **Use lazy loading**: Query engine only fetches data when needed
3. **Reuse query engine**: Data is cached after first load
4. **Chain filters**: More efficient than separate queries

## Export Formats

The query engine supports multiple export formats:

```python
# DataFrame (for further pandas operations)
df = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# List of dictionaries (for iteration)
entries = qe.filter_by_topic(topic_name="Banking").to_dict()

# JSON string (for API responses)
json_str = qe.filter_by_topic(topic_name="Banking").to_json(indent=2)

# CSV file (for spreadsheet tools)
csv_path = qe.filter_by_topic(topic_name="Banking").to_csv("output.csv")
```

## Resources

For detailed information:
- **reference.md**: Complete API documentation, schemas, and endpoint details
- **examples.md**: Comprehensive usage examples and workflows
- **docs/implementation-plan.md**: Full implementation specifications

## Common Issues and Solutions

### Authentication Error
```
AuthenticationError: API key is required
```
**Solution**: Ensure `CARVER_API_KEY` is set in `.env` file. Copy `.env.example` to `.env` and add your API key.

### Import Error
```
ModuleNotFoundError: No module named 'scripts'
```
**Solution**: Activate virtual environment: `source .venv/bin/activate`

### Empty Results
```
No entries found matching criteria
```
**Solution**:
- Verify filters are correct (check topic/feed names)
- Try broadening search (remove filters, use OR logic)
- Check if entries exist for that topic/feed

### Slow Performance
```
Query taking too long (> 60 seconds)
```
**Solution**:
- Filter by feed_id or topic_id before loading entries
- Use `fetch_all=False` for exploratory queries
- Avoid including entries in hierarchical view without filtering

## Guidelines

1. **Read-Only Operations**: This skill only reads data, never modifies the Carver API
2. **API Rate Limits**: Standard rate limit is 10 requests/second. The client handles this automatically with retry logic
3. **Security**: Never log or display API keys. They're automatically loaded from environment
4. **Context Window**: Use scripts to process data rather than loading large DataFrames into context
5. **Error Handling**: All methods have comprehensive error handling. Check logs for detailed error messages

## Method Chaining Pattern

The query engine uses a fluent interface for building complex queries:

```python
# Each method returns self, enabling chaining
results = qe \
    .filter_by_topic(topic_name="Banking") \      # Narrows to banking topic
    .filter_by_feed(feed_name="SEC") \            # Further narrows to SEC feed
    .filter_by_active(is_active=True) \           # Only active entries
    .search_entries("regulation") \               # Search within filtered results
    .to_dataframe()                               # Export as DataFrame

# Reset query to start fresh
results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
```

## Search Field Priority

Default search field: `entry_content_markdown` (the full article content)

Additional searchable fields:
- `entry_title`: Entry headline
- `entry_link`: Entry URL
- `entry_description`: Brief summary

Specify fields explicitly:
```python
results = qe.search_entries(
    "SEC",
    search_fields=['entry_title', 'entry_content_markdown']
).to_dataframe()
```

## Workflow Recommendations

For most user requests, follow this pattern:

1. **Initialize query engine**: `qe = create_query_engine()`
2. **Apply filters first**: Narrow by topic/feed/date to reduce data
3. **Then search**: Apply keyword search to filtered results
4. **Export results**: Choose appropriate format (DataFrame, CSV, JSON)
5. **Present to user**: Format results clearly with relevant columns

Example:
```python
from scripts.query_engine import create_query_engine
from datetime import datetime

qe = create_query_engine()
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries("regulation") \
    .to_dataframe()

# Present key columns to user
print(results[['topic_name', 'feed_name', 'entry_title', 'entry_link', 'entry_published_at']].head(10))
```
