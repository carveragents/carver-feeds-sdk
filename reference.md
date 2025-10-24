# Carver Feeds Skill - API Reference

Complete technical reference for the Carver Feeds Skill, including API endpoints, data schemas, module documentation, and common patterns.

---

## Table of Contents

1. [API Information](#api-information)
2. [Endpoint Documentation](#endpoint-documentation)
3. [Data Schemas](#data-schemas)
4. [Module API Reference](#module-api-reference)
5. [Common Patterns](#common-patterns)
6. [Error Handling](#error-handling)
7. [Performance Considerations](#performance-considerations)

---

## API Information

### Base Configuration

- **Base URL**: `https://app.carveragents.ai`
- **Authentication**: API key via `X-API-Key` header
- **Response Format**: JSON
- **Pagination**: Limit/offset based
- **Rate Limits**: 10 requests/second (standard), 5 requests/second (admin)

### Authentication

All requests require an API key passed in the request header:

```
X-API-Key: your_api_key_here
```

The API client automatically includes this header when initialized with an API key from the environment.

### Rate Limiting

The API enforces rate limits. The client includes automatic retry logic with exponential backoff for rate limit errors (429 status).

**Retry Strategy**:
- Initial delay: 1 second
- Exponential backoff with jitter
- Maximum retries: 3 (configurable)
- Applies to: 429 (rate limit) and 500 (server error) responses

---

## Endpoint Documentation

### 1. List Topics

**Endpoint**: `GET /api/v1/feeds/topics`

**Description**: Fetch all regulatory topics available in the system.

**Parameters**: None

**Response**:
```json
[
  {
    "id": "topic-123",
    "name": "Banking Regulation",
    "description": "Updates on banking and financial regulations",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T14:22:00Z",
    "is_active": true
  }
]
```

**Python Usage**:
```python
from scripts.carver_api import get_client

client = get_client()
topics = client.list_topics()
```

---

### 2. List Feeds

**Endpoint**: `GET /api/v1/feeds/`

**Description**: Fetch all RSS feeds, optionally filtered by topic.

**Parameters**:
- `topic_id` (optional): Filter feeds by topic ID

**Response**:
```json
[
  {
    "id": "feed-456",
    "name": "SEC News Feed",
    "url": "https://www.sec.gov/news/rss",
    "topic": {
      "id": "topic-123",
      "name": "Banking Regulation"
    },
    "description": "Latest news from the SEC",
    "created_at": "2024-01-15T10:30:00Z",
    "is_active": true,
    "color": "#FF5733",
    "fetch_frequency_minutes": 60
  }
]
```

**Python Usage**:
```python
# All feeds
feeds = client.list_feeds()

# Feeds for specific topic
topic_feeds = client.list_feeds(topic_id="topic-123")
```

**Note**: The response includes a nested `topic` object which the data manager flattens to `topic_id` and `topic_name` fields for easier DataFrame operations.

---

### 3. List All Entries (Paginated)

**Endpoint**: `GET /api/v1/feeds/entries/list`

**Description**: Fetch feed entries with pagination. Use this for broad queries or when feed association is not needed.

**Parameters**:
- `limit` (optional): Number of entries per page (default: 50)
- `offset` (optional): Starting position for pagination (default: 0)
- `is_active` (optional): Filter by active status (true/false)

**Response**:
```json
{
  "items": [
    {
      "id": "entry-789",
      "title": "New Banking Regulation Proposed",
      "link": "https://example.com/article/123",
      "content_markdown": "# Regulation Details\n\nFull article content in markdown...",
      "description": "Brief summary of the article",
      "published_date": "2024-10-24T08:00:00Z",
      "created_at": "2024-10-24T09:15:00Z",
      "is_active": true
    }
  ],
  "total": 10247,
  "limit": 50,
  "offset": 0
}
```

**Python Usage**:
```python
# First page only
entries = client.list_entries(limit=50, fetch_all=False)

# All entries (automatic pagination)
all_entries = client.list_entries(fetch_all=True)

# Active entries only
active_entries = client.list_entries(is_active=True, fetch_all=True)
```

**Important Limitation**: This endpoint does NOT include `feed_id` in the response. Use the feed-specific or topic-specific endpoints if you need feed association.

---

### 4. Get Feed Entries

**Endpoint**: `GET /api/v1/feeds/{feed_id}/entries`

**Description**: Fetch all entries for a specific feed. This endpoint includes feed context.

**Parameters**:
- `limit` (optional): Maximum number of entries to return (default: 100)

**Response**:
```json
{
  "items": [
    {
      "id": "entry-789",
      "title": "SEC Proposes New Rule",
      "link": "https://www.sec.gov/news/article-123",
      "content_markdown": "# Article Content\n\nDetailed content...",
      "description": "Brief summary",
      "published_date": "2024-10-24T08:00:00Z",
      "created_at": "2024-10-24T09:15:00Z",
      "is_active": true
    }
  ]
}
```

**Python Usage**:
```python
feed_entries = client.get_feed_entries("feed-456", limit=100)
```

**Note**: The data manager automatically injects `feed_id` into each entry when using this endpoint, enabling proper relationship tracking.

---

### 5. Get Topic Entries

**Endpoint**: `GET /api/v1/feeds/topics/{topic_id}/entries`

**Description**: Fetch all entries for feeds within a specific topic. Optimized endpoint for topic-level queries.

**Parameters**:
- `limit` (optional): Maximum number of entries to return

**Response**: Same format as feed entries endpoint

**Python Usage**:
```python
# Via API client
topic_entries = client.get_topic_entries("topic-123", limit=500)

# Via query engine (recommended)
qe = create_query_engine()
results = qe.filter_by_topic(topic_id="topic-123").to_dataframe()
```

**Performance**: Faster than fetching all entries and filtering, especially for large datasets.

**Note**: Entries from this endpoint do NOT include `feed_id` (API limitation).

---

## Data Schemas

### Topic Schema

**DataFrame Columns** (from `get_topics_df()`):

| Column | Type | Description |
|--------|------|-------------|
| `id` | str | Unique topic identifier |
| `name` | str | Topic name |
| `description` | str | Topic description |
| `created_at` | datetime64 | Creation timestamp |
| `updated_at` | datetime64 | Last update timestamp |
| `is_active` | bool | Active status |

**Extra columns**: API may return additional undocumented fields (e.g., `color`, `icon`). These are preserved in the DataFrame.

---

### Feed Schema

**DataFrame Columns** (from `get_feeds_df()`):

| Column | Type | Description |
|--------|------|-------------|
| `id` | str | Unique feed identifier |
| `name` | str | Feed name |
| `url` | str | RSS feed URL |
| `topic_id` | str | Associated topic ID (foreign key) |
| `topic_name` | str | Associated topic name (denormalized) |
| `description` | str | Feed description |
| `created_at` | datetime64 | Creation timestamp |
| `is_active` | bool | Active status |

**Extra columns**: `color`, `fetch_frequency_minutes`, `max_depth`, `tags`, and other metadata fields.

**Relationships**:
- `topic_id` → `topics.id` (one-to-one)

---

### Entry Schema

**DataFrame Columns** (from `get_entries_df()`):

| Column | Type | Description |
|--------|------|-------------|
| `id` | str | Unique entry identifier |
| `title` | str | Entry headline |
| `link` | str | URL to original article |
| `content_markdown` | str | Full article content in markdown |
| `description` | str | Brief summary |
| `published_at` | datetime64 | Publication date (mapped from `published_date`) |
| `created_at` | datetime64 | Creation timestamp in Carver system |
| `is_active` | bool | Active status |
| `feed_id` | str | Associated feed ID (only when fetched via feed endpoint) |

**Relationships**:
- `feed_id` → `feeds.id` (many-to-one, when available)

**Important**: `feed_id` is only present when entries are fetched via:
- `get_feed_entries(feed_id)`
- `get_hierarchical_view(feed_id=...)`

It is NOT present when fetched via:
- `list_entries()` (general entry list)
- `get_topic_entries(topic_id)` (topic-specific entries)

---

### Hierarchical View Schema

**DataFrame Columns** (from `get_hierarchical_view()`):

Hierarchical views merge topics, feeds, and optionally entries into a single denormalized DataFrame.

**Without entries** (`include_entries=False`):

| Column Prefix | Fields | Description |
|---------------|--------|-------------|
| `topic_*` | id, name, description, created_at, updated_at, is_active | Topic fields |
| `feed_*` | id, name, url, description, created_at, is_active | Feed fields |

**With entries** (`include_entries=True`):

| Column Prefix | Fields | Description |
|---------------|--------|-------------|
| `topic_*` | id, name, description, created_at, updated_at, is_active | Topic fields |
| `feed_*` | id, name, url, description, created_at, is_active | Feed fields |
| `entry_*` | id, title, link, content_markdown, description, published_at, created_at, is_active | Entry fields |

**Example columns**: `topic_id`, `topic_name`, `feed_id`, `feed_name`, `entry_id`, `entry_title`, `entry_content_markdown`, etc.

**Performance Warning**: Including entries without filtering by `feed_id` creates a very large DataFrame (~10,000 rows). Always filter when possible.

---

## Module API Reference

### scripts.carver_api

#### `CarverFeedsAPIClient`

**Initialization**:
```python
from scripts.carver_api import CarverFeedsAPIClient

client = CarverFeedsAPIClient(
    base_url="https://app.carveragents.ai",
    api_key="your_api_key",
    max_retries=3,
    initial_retry_delay=1.0
)
```

**Methods**:

##### `list_topics() -> List[Dict]`
Fetch all topics from the API.

**Returns**: List of topic dictionaries

**Raises**:
- `AuthenticationError`: Invalid API key
- `CarverAPIError`: API request failed

---

##### `list_feeds(topic_id: Optional[str] = None) -> List[Dict]`
Fetch feeds, optionally filtered by topic.

**Parameters**:
- `topic_id`: Filter by topic ID (optional)

**Returns**: List of feed dictionaries

---

##### `list_entries(feed_id: Optional[str] = None, is_active: Optional[bool] = None, limit: int = 50, fetch_all: bool = False) -> List[Dict]`
Fetch entries with automatic pagination.

**Parameters**:
- `feed_id`: Filter by feed ID (optional)
- `is_active`: Filter by active status (optional)
- `limit`: Entries per page (default: 50)
- `fetch_all`: If True, fetch all pages; if False, fetch first page only (default: False)

**Returns**: List of entry dictionaries

**Performance**: With `fetch_all=True`, may take 30-60 seconds for ~10,000 entries.

---

##### `get_feed_entries(feed_id: str, limit: int = 100) -> List[Dict]`
Fetch entries for a specific feed.

**Parameters**:
- `feed_id`: Feed identifier (required)
- `limit`: Maximum entries to return (default: 100)

**Returns**: List of entry dictionaries

**Note**: Data manager injects `feed_id` into each entry for relationship tracking.

---

##### `get_topic_entries(topic_id: str, limit: int = 500) -> List[Dict]`
Fetch entries for all feeds in a topic.

**Parameters**:
- `topic_id`: Topic identifier (required)
- `limit`: Maximum entries to return (default: 500)

**Returns**: List of entry dictionaries

**Optimization**: Faster than fetching all entries when you only need one topic.

---

#### `get_client() -> CarverFeedsAPIClient`
Factory function to create client from environment variables.

**Environment Variables**:
- `CARVER_API_KEY`: API key (required)
- `CARVER_BASE_URL`: Base URL (optional, defaults to `https://app.carveragents.ai`)

**Returns**: Configured `CarverFeedsAPIClient` instance

**Raises**: `AuthenticationError` if `CARVER_API_KEY` not set

**Example**:
```python
from scripts.carver_api import get_client

client = get_client()  # Uses .env configuration
topics = client.list_topics()
```

---

### scripts.data_manager

#### `FeedsDataManager`

**Initialization**:
```python
from scripts.data_manager import FeedsDataManager
from scripts.carver_api import get_client

client = get_client()
dm = FeedsDataManager(client)
```

**Methods**:

##### `get_topics_df() -> pd.DataFrame`
Fetch all topics as a pandas DataFrame.

**Returns**: DataFrame with topic schema

**Example**:
```python
topics_df = dm.get_topics_df()
print(topics_df[['id', 'name', 'is_active']].head())
```

---

##### `get_feeds_df(topic_id: Optional[str] = None) -> pd.DataFrame`
Fetch feeds as a pandas DataFrame, optionally filtered by topic.

**Parameters**:
- `topic_id`: Filter by topic ID (optional)

**Returns**: DataFrame with feed schema

**Example**:
```python
# All feeds
feeds_df = dm.get_feeds_df()

# Feeds for specific topic
topic_feeds = dm.get_feeds_df(topic_id="topic-123")
```

---

##### `get_entries_df(feed_id: Optional[str] = None, topic_id: Optional[str] = None, is_active: Optional[bool] = None, fetch_all: bool = True) -> pd.DataFrame`
Fetch entries as a pandas DataFrame with flexible filtering.

**Parameters**:
- `feed_id`: Filter by feed ID (optional, uses optimized endpoint)
- `topic_id`: Filter by topic ID (optional, uses optimized endpoint)
- `is_active`: Filter by active status (optional)
- `fetch_all`: Fetch all pages vs first page only (default: True)

**Returns**: DataFrame with entry schema

**Performance**:
- With `feed_id` or `topic_id`: Fast, fetches only relevant entries
- Without filters + `fetch_all=True`: Slow (~30-60s), fetches all ~10,000 entries

**Example**:
```python
# All entries (slow)
all_entries = dm.get_entries_df()

# Entries for specific feed (fast)
feed_entries = dm.get_entries_df(feed_id="feed-456")

# Entries for topic (medium speed)
topic_entries = dm.get_entries_df(topic_id="topic-123")
```

---

##### `get_hierarchical_view(include_entries: bool = True, feed_id: Optional[str] = None, topic_id: Optional[str] = None) -> pd.DataFrame`
Build denormalized hierarchical view merging topics, feeds, and optionally entries.

**Parameters**:
- `include_entries`: Include entry data (default: True)
- `feed_id`: Filter entries by feed (optional, recommended)
- `topic_id`: Filter entries by topic (optional)

**Returns**: DataFrame with hierarchical schema (topic_*, feed_*, entry_* columns)

**Performance Warning**: With `include_entries=True` and no `feed_id`/`topic_id`, creates ~10,000 row DataFrame. Always filter when possible.

**Example**:
```python
# Topic + Feed only (fast)
hierarchy = dm.get_hierarchical_view(include_entries=False)

# Full hierarchy for specific feed (medium speed)
full = dm.get_hierarchical_view(include_entries=True, feed_id="feed-456")
```

---

#### `create_data_manager() -> FeedsDataManager`
Factory function to create data manager from environment configuration.

**Returns**: Configured `FeedsDataManager` instance

**Example**:
```python
from scripts.data_manager import create_data_manager

dm = create_data_manager()  # Uses .env for API key
topics = dm.get_topics_df()
```

---

### scripts.query_engine

#### `EntryQueryEngine`

**Initialization**:
```python
from scripts.query_engine import EntryQueryEngine
from scripts.data_manager import create_data_manager

dm = create_data_manager()
qe = EntryQueryEngine(dm)
```

**Methods**:

##### `chain() -> EntryQueryEngine`
Reset query to start fresh with all data.

**Returns**: Self for method chaining

**Example**:
```python
# First query
results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Reset and new query
results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
```

---

##### `search_entries(keywords: Union[str, List[str]], search_fields: List[str] = ['entry_content_markdown'], case_sensitive: bool = False, match_all: bool = False) -> EntryQueryEngine`
Search entries by keywords across specified fields.

**Parameters**:
- `keywords`: Single keyword or list of keywords
- `search_fields`: Fields to search in (default: `['entry_content_markdown']`)
- `case_sensitive`: Case-sensitive search (default: False)
- `match_all`: All keywords must match (AND) vs any keyword (OR) (default: False)

**Available search fields**:
- `entry_content_markdown` (default, full article content)
- `entry_title` (headline)
- `entry_link` (URL)
- `entry_description` (summary)

**Returns**: Self for method chaining

**Example**:
```python
# Search for "regulation" in content
results = qe.search_entries("regulation").to_dataframe()

# Search for any of multiple keywords
results = qe.search_entries(["banking", "finance"], match_all=False).to_dataframe()

# Search for all keywords
results = qe.search_entries(["banking", "regulation"], match_all=True).to_dataframe()

# Search in title and content
results = qe.search_entries(
    "SEC",
    search_fields=['entry_title', 'entry_content_markdown']
).to_dataframe()
```

---

##### `filter_by_topic(topic_id: Optional[str] = None, topic_name: Optional[str] = None) -> EntryQueryEngine`
Filter entries by topic.

**Parameters**:
- `topic_id`: Exact topic ID match (optional)
- `topic_name`: Partial topic name match, case-insensitive (optional)

**Returns**: Self for method chaining

**Example**:
```python
# Filter by topic name (partial match)
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Filter by topic ID (exact match)
results = qe.filter_by_topic(topic_id="topic-123").to_dataframe()
```

---

##### `filter_by_feed(feed_id: Optional[str] = None, feed_name: Optional[str] = None) -> EntryQueryEngine`
Filter entries by feed.

**Parameters**:
- `feed_id`: Exact feed ID match (optional)
- `feed_name`: Partial feed name match, case-insensitive (optional)

**Returns**: Self for method chaining

**Example**:
```python
# Filter by feed name (partial match)
results = qe.filter_by_feed(feed_name="SEC News").to_dataframe()

# Filter by feed ID (exact match)
results = qe.filter_by_feed(feed_id="feed-456").to_dataframe()
```

---

##### `filter_by_date(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> EntryQueryEngine`
Filter entries by publication date range.

**Parameters**:
- `start_date`: Start of date range, inclusive (optional)
- `end_date`: End of date range, inclusive (optional)

**Returns**: Self for method chaining

**Example**:
```python
from datetime import datetime

# Entries from 2024 onwards
results = qe.filter_by_date(start_date=datetime(2024, 1, 1)).to_dataframe()

# Entries in specific date range
results = qe.filter_by_date(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
).to_dataframe()
```

---

##### `filter_by_active(is_active: bool) -> EntryQueryEngine`
Filter entries by active status.

**Parameters**:
- `is_active`: True for active entries, False for inactive

**Returns**: Self for method chaining

**Example**:
```python
# Only active entries
results = qe.filter_by_active(is_active=True).to_dataframe()
```

---

##### `to_dataframe() -> pd.DataFrame`
Export results as pandas DataFrame.

**Returns**: Copy of results DataFrame

**Example**:
```python
df = qe.filter_by_topic(topic_name="Banking").to_dataframe()
print(df[['entry_title', 'entry_published_at']].head())
```

---

##### `to_dict() -> List[Dict]`
Export results as list of dictionaries.

**Returns**: List of dictionaries, one per entry

**Example**:
```python
entries = qe.filter_by_topic(topic_name="Banking").to_dict()
for entry in entries[:3]:
    print(f"{entry['entry_title']}: {entry['entry_link']}")
```

---

##### `to_json(indent: Optional[int] = None) -> str`
Export results as JSON string.

**Parameters**:
- `indent`: JSON indentation level (optional)

**Returns**: JSON string

**Example**:
```python
json_str = qe.filter_by_topic(topic_name="Banking").to_json(indent=2)
with open('banking_entries.json', 'w') as f:
    f.write(json_str)
```

---

##### `to_csv(filepath: str) -> str`
Export results to CSV file.

**Parameters**:
- `filepath`: Output file path

**Returns**: Absolute path to created CSV file

**Example**:
```python
csv_path = qe.filter_by_topic(topic_name="Banking").to_csv("banking_entries.csv")
print(f"Exported to {csv_path}")
```

---

#### `create_query_engine() -> EntryQueryEngine`
Factory function to create query engine from environment configuration.

**Returns**: Configured `EntryQueryEngine` instance

**Example**:
```python
from scripts.query_engine import create_query_engine

qe = create_query_engine()  # Uses .env for API key
results = qe.search_entries("regulation").to_dataframe()
```

---

## Common Patterns

### Pattern 1: Basic Topic Exploration

```python
from scripts.data_manager import create_data_manager

dm = create_data_manager()

# List all topics
topics_df = dm.get_topics_df()
print(f"Available topics: {len(topics_df)}")
print(topics_df[['id', 'name', 'is_active']].head(10))

# List feeds for a topic
topic_id = topics_df['id'].iloc[0]
feeds_df = dm.get_feeds_df(topic_id=topic_id)
print(f"Feeds in topic: {len(feeds_df)}")
```

### Pattern 2: Keyword Search with Filters

```python
from scripts.query_engine import create_query_engine
from datetime import datetime

qe = create_query_engine()

# Search with multiple filters
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .filter_by_active(is_active=True) \
    .search_entries(["regulation", "compliance"]) \
    .to_dataframe()

print(f"Found {len(results)} results")
print(results[['entry_title', 'feed_name', 'entry_published_at']].head())
```

### Pattern 3: Feed-Specific Analysis

```python
from scripts.query_engine import create_query_engine

qe = create_query_engine()

# Get all entries from specific feed
results = qe.filter_by_feed(feed_name="SEC News").to_dataframe()

# Analyze by date
results['month'] = results['entry_published_at'].dt.to_period('M')
monthly_counts = results.groupby('month').size()
print("Entries per month:")
print(monthly_counts.tail(6))
```

### Pattern 4: Export Workflow

```python
from scripts.query_engine import create_query_engine

qe = create_query_engine()

# Filter data
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .search_entries("regulation")

# Export in multiple formats
df = results.to_dataframe()
dict_list = results.to_dict()
json_str = results.to_json(indent=2)
csv_path = results.to_csv("banking_regulations.csv")

print(f"Exported {len(df)} entries to CSV at {csv_path}")
```

### Pattern 5: Multi-Topic Comparison

```python
from scripts.query_engine import create_query_engine
import pandas as pd

qe = create_query_engine()

# Get entries from multiple topics
banking = qe.filter_by_topic(topic_name="Banking").to_dataframe()
healthcare = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
energy = qe.chain().filter_by_topic(topic_name="Energy").to_dataframe()

# Combine and analyze
all_results = pd.concat([banking, healthcare, energy])
topic_counts = all_results.groupby('topic_name').size()
print("Entries per topic:")
print(topic_counts)
```

### Pattern 6: Optimized Large Query

```python
from scripts.data_manager import create_data_manager

dm = create_data_manager()

# Instead of loading all entries, filter by topic first
entries = dm.get_entries_df(topic_id="topic-123")  # Fast, optimized endpoint

# Then do analysis on filtered data
print(f"Loaded {len(entries)} entries for topic")
keyword_matches = entries[
    entries['content_markdown'].str.contains("regulation", case=False, na=False)
]
print(f"Found {len(keyword_matches)} matching entries")
```

---

## Error Handling

### Common Exceptions

#### `AuthenticationError`
**Cause**: Missing or invalid API key

**Solution**:
1. Check `.env` file exists
2. Verify `CARVER_API_KEY` is set
3. Ensure no extra spaces or quotes around key

**Example**:
```python
from scripts.carver_api import get_client, AuthenticationError

try:
    client = get_client()
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    print("Check your .env file and CARVER_API_KEY")
```

#### `RateLimitError`
**Cause**: Exceeded API rate limit (10 req/sec)

**Solution**: Client automatically retries with backoff. If persistent, reduce request frequency.

#### `CarverAPIError`
**Cause**: General API error (network, server error, etc.)

**Solution**: Check error message for details. May need to retry manually.

### Error Handling Best Practices

```python
from scripts.query_engine import create_query_engine
from scripts.carver_api import CarverAPIError, AuthenticationError
import logging

logging.basicConfig(level=logging.INFO)

try:
    qe = create_query_engine()
    results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

    if len(results) == 0:
        print("No results found. Try broadening search criteria.")
    else:
        print(f"Found {len(results)} results")

except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    print("Action: Check .env file and CARVER_API_KEY")

except CarverAPIError as e:
    print(f"API error: {e}")
    print("Action: Check network connection and API status")

except Exception as e:
    print(f"Unexpected error: {e}")
    logging.exception("Full traceback:")
```

---

## Performance Considerations

### Data Loading Times

**Approximate fetch times** (with good network connection):

| Operation | Volume | Time |
|-----------|--------|------|
| List topics | ~114 | < 1 second |
| List feeds | ~827 | ~3-5 seconds |
| List all entries | ~10,000 | ~30-60 seconds |
| Entries for specific feed | Varies | ~2-10 seconds |
| Entries for specific topic | Varies | ~5-20 seconds |

### Optimization Strategies

1. **Use Filtered Endpoints**: When possible, filter at the API level
   ```python
   # Slow: fetch all, then filter
   all_entries = dm.get_entries_df()
   filtered = all_entries[all_entries['feed_id'] == 'feed-456']

   # Fast: filter at API
   filtered = dm.get_entries_df(feed_id='feed-456')
   ```

2. **Lazy Loading**: Query engine loads data only on first filter/search
   ```python
   qe = create_query_engine()  # Fast, no API call
   results = qe.search_entries("regulation")  # API call happens here
   ```

3. **Reuse Query Engine**: Data is cached after first load
   ```python
   qe = create_query_engine()

   # First query: loads data (~30-60s)
   results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()

   # Subsequent queries: use cached data (instant)
   results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
   ```

4. **Limit Entry Fetches**: Use `fetch_all=False` for exploration
   ```python
   # Exploration: first page only
   sample = dm.get_entries_df(fetch_all=False)  # Fast, ~50 entries

   # Production: all data
   all_data = dm.get_entries_df(fetch_all=True)  # Slow, ~10,000 entries
   ```

### Memory Considerations

**DataFrame sizes** (approximate):

| Data | Rows | Memory |
|------|------|--------|
| Topics | ~114 | < 1 MB |
| Feeds | ~827 | ~5 MB |
| Entries (all) | ~10,000 | ~50-100 MB |
| Hierarchical (with entries) | ~10,000 | ~100-200 MB |

**Recommendation**: For large result sets, export to CSV and process externally rather than loading full DataFrame into context.

---

## Additional Resources

- **Implementation Plan**: `/docs/implementation-plan.md` - Complete technical specifications
- **Lessons Learned**: `/docs/LESSONS.md` - Gotchas and patterns discovered during implementation
- **OpenAPI Spec**: `/docs/openapi-spec.json` - API specification (note: actual responses may differ)
- **Examples**: `examples.md` - Comprehensive usage examples

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Status**: Production Ready
