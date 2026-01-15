# Carver Feeds SDK - API Reference

Complete technical reference for the Carver Feeds SDK, including API endpoints, data schemas, module documentation, and common patterns.

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
- **Pagination**: Limit/offset based (maximum page size: 100 entries)
- **Rate Limits**: 10 requests/second (standard), 5 requests/second (admin)

**Important:** The API server enforces a maximum page size of 100 entries per request. Requesting `limit > 100` will return at most 100 entries. Use `fetch_all=True` in SDK methods for automatic pagination beyond this limit.

### Authentication

All requests require an API key passed in the request header:

```
X-API-Key: your_api_key_here
```

The SDK automatically includes this header when initialized with an API key from the environment.

### Rate Limiting

The API enforces rate limits. The SDK includes automatic retry logic with exponential backoff for rate limit errors (429 status).

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

**SDK Usage**:
```python
from carver_feeds import get_client

client = get_client()
topics = client.list_topics()
```

---

### 2. List All Entries (Paginated)

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
      "description": "Brief summary of the article",
      "published_date": "2024-10-24T08:00:00Z",
      "created_at": "2024-10-24T09:15:00Z",
      "is_active": true,
      "extracted_metadata": {
        "feed_id": "feed-456",
        "topic_id": "topic-123",
        "content_status": "extracted",
        "timestamp": "2024-11-18T17:35:34.258Z",
        "s3_content_md_path": "s3://bucket/path/content.md",
        "s3_content_html_path": "s3://bucket/path/content.html",
        "s3_aggregated_content_md_path": "s3://bucket/path/aggregated.md"
      }
    }
  ],
  "total": 10247,
  "limit": 50,
  "offset": 0
}
```

**Note (v0.2.0+):** `content_markdown` is no longer returned by this endpoint. Content is now stored in S3 and must be fetched separately using the S3 paths provided in `extracted_metadata`. Use `get_entries_df(fetch_content=True)` to automatically fetch content from S3.

**SDK Usage**:
```python
# First page only
entries = client.list_entries(limit=50, fetch_all=False)

# All entries (automatic pagination)
all_entries = client.list_entries(fetch_all=True)

# Active entries only
active_entries = client.list_entries(is_active=True, fetch_all=True)
```

---

### 3. Get Topic Entries

**Endpoint**: `GET /api/v1/feeds/topics/{topic_id}/entries`

**Description**: Fetch all entries for feeds within a specific topic. Optimized endpoint for topic-level queries.

**Parameters**:
- `limit` (optional): Maximum number of entries to return (max: 100)

**Response**: Same format as feed entries endpoint (includes `extracted_metadata`)

**SDK Usage**:
```python
# Via API client
topic_entries = client.get_topic_entries("topic-123", limit=100)

# Via query engine (recommended)
from carver_feeds import create_query_engine
qe = create_query_engine()
results = qe.filter_by_topic(topic_id="topic-123").to_dataframe()
```

**Performance**: Faster than fetching all entries and filtering, especially for large datasets.

**Note**: **API Limit:** Requesting `limit > 100` returns at most 100 entries. **Content (v0.2.0+):** `content_markdown` not included; requires S3 fetch.

---

### 4. Get User Topic Subscriptions

**Endpoint**: `GET /api/v1/core/users/{user_id}/topics/subscriptions`

**Description**: Fetch the list of topics that a specific user has subscribed to.

**Parameters**:
- `user_id` (required, path parameter): User identifier

**Response**:
```json
{
  "subscriptions": [
    {
      "id": "topic-123",
      "name": "Abu Dhabi Global Market",
      "description": "A financial free zone in Abu Dhabi...",
      "base_domain": null
    },
    {
      "id": "topic-456",
      "name": "Reserve Bank of India",
      "description": "India's central banking institution...",
      "base_domain": "rbi.org.in"
    }
  ],
  "total_count": 2
}
```

**SDK Usage**:
```python
from carver_feeds import get_client, create_data_manager

# Via API client (raw response)
client = get_client()
response = client.get_user_topic_subscriptions("user-123")
print(f"User has {response['total_count']} subscriptions")
for topic in response['subscriptions']:
    print(f"- {topic['name']}")

# Via data manager (DataFrame)
dm = create_data_manager()
subscriptions_df = dm.get_user_topic_subscriptions_df("user-123")
print(subscriptions_df[['id', 'name', 'description']])
```

**Response Fields**:
- `subscriptions`: List of topic objects (id, name, description, base_domain)
- `total_count`: Total number of subscriptions

**Use Cases**:
- Display user's subscribed topics in UI
- Filter content based on user preferences
- Track user interests for analytics

---

### 5. Get Annotations

**Endpoint**: `GET /api/v1/core/annotations`

**Description**: Retrieve annotations filtered by specific criteria. Annotations provide AI-generated insights, classifications, and summaries for feed entries.

**Query Parameters** (exactly one required):
- `feed_entry_ids_in` (string, CSV): Comma-separated list of Feed Entry UUIDs
- `topic_ids_in` (string, CSV): Comma-separated list of Topic UUIDs
- `user_ids_in` (string, CSV): Comma-separated list of User UUIDs

**Priority Order**: If multiple filters are provided (not recommended), the API uses this priority:
1. `feed_entry_ids_in` (highest priority)
2. `topic_ids_in`
3. `user_ids_in` (lowest priority)

**Response**:
```json
[
  {
    "annotation": {
      "scores": {
        "relevance": 0.95,
        "importance": 0.87,
        "confidence": 0.92
      },
      "classification": {
        "category": "regulatory_update",
        "subcategory": "compliance",
        "tags": ["banking", "aml", "kyc"]
      },
      "summary": "New AML regulations require enhanced KYC procedures..."
    },
    "feed_entry_id": "entry-uuid-123",
    "topic_id": "topic-uuid-456",
    "user_id": "user-uuid-789"
  }
]
```

**SDK Usage**:
```python
from carver_feeds import get_client

client = get_client()

# Filter by feed entry IDs
annotations = client.get_annotations(
    feed_entry_ids=["entry-uuid-1", "entry-uuid-2"]
)

# Filter by topic IDs
annotations = client.get_annotations(
    topic_ids=["topic-uuid-1"]
)

# Filter by user IDs
annotations = client.get_annotations(
    user_ids=["user-uuid-1", "user-uuid-2"]
)

# Process annotations
for ann in annotations:
    print(f"Entry: {ann['feed_entry_id']}")
    print(f"Summary: {ann['annotation']['summary']}")
    print(f"Relevance: {ann['annotation']['scores']['relevance']:.2f}")
```

**Response Fields**:
- `annotation`: Dict containing AI-generated insights
  - `scores`: Dict with relevance, importance, confidence scores (0.0-1.0)
  - `classification`: Dict with category, subcategory, and tags
  - `summary`: Text summary of the entry
- `feed_entry_id`: UUID of the annotated feed entry
- `topic_id`: UUID of the topic (present when filtered by topic/user)
- `user_id`: UUID of the user (present when filtered by user)

**Important Notes**:
- Only one filter type can be used per request
- Empty filter lists will raise a `ValueError`
- SDK validates that exactly one filter is provided
- Returns empty list if no annotations match the filter

**Use Cases**:
- Retrieve AI insights for specific entries
- Analyze all annotations for a topic
- Get user-specific annotation data
- Filter entries by relevance/importance scores
- Build custom analytics dashboards
- Generate reports based on classifications

**Example - Advanced Usage**:
```python
# Get annotations and filter by score threshold
annotations = client.get_annotations(topic_ids=["topic-123"])

high_importance = [
    ann for ann in annotations
    if ann['annotation']['scores']['importance'] > 0.8
]

# Analyze tags
from collections import Counter
all_tags = []
for ann in annotations:
    all_tags.extend(ann['annotation']['classification'].get('tags', []))
tag_counts = Counter(all_tags)
print(f"Most common tags: {tag_counts.most_common(5)}")
```

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

### Entry Schema

**DataFrame Columns** (from `get_topic_entries_df()`):

| Column | Type | Description |
|--------|------|-------------|
| `id` | str | Unique entry identifier |
| `title` | str | Entry headline |
| `link` | str | URL to original article |
| `entry_content_markdown` | str | Full article content in markdown (requires `fetch_content=True` in v0.2.0+) |
| `description` | str | Brief summary |
| `published_at` | datetime64 | Publication date (mapped from `published_date`) |
| `created_at` | datetime64 | Creation timestamp in Carver system |
| `is_active` | bool | Active status |
| `feed_id` | str | Associated feed ID (from extracted_metadata) |
| `topic_id` | str | Associated topic ID (from extracted_metadata) |
| `content_status` | str | Content extraction status (from extracted_metadata) |
| `content_timestamp` | datetime64 | When content was fetched (from extracted_metadata) |
| `s3_content_md_path` | str | S3 path to markdown content (from extracted_metadata) |
| `s3_content_html_path` | str | S3 path to HTML content (from extracted_metadata) |
| `s3_aggregated_content_md_path` | str | S3 path to aggregated content (from extracted_metadata) |

**Important Changes in v0.2.0:**
- `entry_content_markdown` (renamed from `content_markdown`) is **NOT** returned by the API by default
- To fetch content, use `get_topic_entries_df(fetch_content=True)` with AWS credentials configured
- New metadata fields from `extracted_metadata` provide S3 paths and content status
- `feed_id` and `topic_id` now available from `extracted_metadata` for all entries

**Relationships**:
- `feed_id` → Associated feed (metadata only, feed endpoints removed)
- `topic_id` → `topics.id` (many-to-one)

---

### Hierarchical View Schema

**DataFrame Columns** (from `get_hierarchical_view()`):

Hierarchical views merge topics and entries into a single denormalized DataFrame.

**Without entries** (`include_entries=False`):

| Column Prefix | Fields | Description |
|---------------|--------|-------------|
| `topic_*` | id, name, description, created_at, updated_at, is_active | Topic fields |

**With entries** (`include_entries=True`):

| Column Prefix | Fields | Description |
|---------------|--------|-------------|
| `topic_*` | id, name, description, created_at, updated_at, is_active | Topic fields |
| `entry_*` | id, title, link, entry_content_markdown, description, published_at, created_at, is_active | Entry fields |

**Example columns**: `topic_id`, `topic_name`, `entry_id`, `entry_title`, `entry_content_markdown`, etc.

**Performance Warning**: Including entries without filtering by `topic_id` creates a very large DataFrame (~10,000 rows). Always filter by topic when possible.

---

### Annotation Schema

**Response Structure** (from `get_annotations()`):

Annotations are returned as a list of dictionaries with the following structure:

| Field | Type | Description |
|-------|------|-------------|
| `annotation` | dict | AI-generated insights for the entry |
| `feed_entry_id` | str | UUID of the annotated feed entry |
| `topic_id` | str/null | UUID of the topic (present when filtered by topic/user) |
| `user_id` | str/null | UUID of the user (present when filtered by user) |

**Annotation Object Structure**:

#### Scores
Each score is an object with label, score value, and confidence:

| Field | Type | Description |
|-------|------|-------------|
| `annotation.scores.impact` | dict | Impact assessment |
| `annotation.scores.impact.label` | str | Label: "low", "medium", "high" |
| `annotation.scores.impact.score` | int | Numeric score (0-10) |
| `annotation.scores.impact.confidence` | float | Confidence level (0.0-1.0) |
| `annotation.scores.urgency` | dict | Urgency assessment |
| `annotation.scores.urgency.label` | str | Label: "low", "medium", "high" |
| `annotation.scores.urgency.score` | int | Numeric score (0-10) |
| `annotation.scores.urgency.confidence` | float | Confidence level (0.0-1.0) |
| `annotation.scores.relevance` | dict | Relevance assessment |
| `annotation.scores.relevance.label` | str | Label: "low", "medium", "high" |
| `annotation.scores.relevance.score` | float | Numeric score (0.0-10.0) |
| `annotation.scores.relevance.confidence` | float | Confidence level (0.0-1.0) |

#### Classification
| Field | Type | Description |
|-------|------|-------------|
| `annotation.classification.update_type` | str | Type of update (e.g., "trend report", "policy change") |
| `annotation.classification.regulatory_source` | dict | Source information |
| `annotation.classification.regulatory_source.name` | str | Source organization name |
| `annotation.classification.regulatory_source.division_office` | str | Division/office within org |
| `annotation.classification.metadata` | dict | Document metadata (title, language, etc.) |

#### Metadata
Rich metadata providing detailed insights:

| Field | Type | Description |
|-------|------|-------------|
| `annotation.metadata.tags` | list[str] | Topic tags (e.g., ["Abu Dhabi", "GDP Growth", "Banking"]) |
| `annotation.metadata.impact_summary` | dict | Detailed impact analysis |
| `annotation.metadata.impact_summary.objective` | str | Primary objective of the document |
| `annotation.metadata.impact_summary.why_it_matters` | str | Explanation of significance |
| `annotation.metadata.impact_summary.what_changed` | str | Summary of changes |
| `annotation.metadata.impact_summary.risk_impact` | str | Risk implications |
| `annotation.metadata.impact_summary.key_requirements` | list[str] | Key requirements or actions |
| `annotation.metadata.impacted_business` | dict | Business impact details |
| `annotation.metadata.impacted_business.industry` | list[str] | Affected industries |
| `annotation.metadata.impacted_business.jurisdiction` | list[str] | Affected jurisdictions |
| `annotation.metadata.impacted_business.type` | list[str] | Business types affected |
| `annotation.metadata.impacted_functions` | list[str] | Impacted business functions |
| `annotation.metadata.critical_dates` | dict | Important dates (effective, compliance, etc.) |
| `annotation.metadata.actionables` | dict | Required actions by category |

**Example Annotation Object**:
```python
{
    "annotation": {
        "scores": {
            "impact": {
                "label": "medium",
                "score": 4,
                "confidence": 0.9
            },
            "urgency": {
                "label": "low",
                "score": 0,
                "confidence": 1.0
            },
            "relevance": {
                "label": "low",
                "score": 2.0,
                "confidence": 0.95
            }
        },
        "classification": {
            "update_type": "trend report",
            "regulatory_source": {
                "name": "Abu Dhabi Department of Economic Development",
                "division_office": "Economic Strategy Sector"
            },
            "metadata": {
                "title": "ABU DHABI Q4 2022 ECONOMIC UPDATE",
                "language": ["English"]
            }
        },
        "metadata": {
            "tags": [
                "Abu Dhabi", "Economic Update", "Q4 2022", "GDP Growth",
                "Inflation", "Oil Market", "Banking Indicators"
            ],
            "impact_summary": {
                "objective": "To provide an economic update for Abu Dhabi and the GCC region...",
                "why_it_matters": "The update informs stakeholders about economic conditions...",
                "what_changed": "The document reports on economic growth rates...",
                "risk_impact": "The economic slowdown presents risks...",
                "key_requirements": []
            },
            "impacted_business": {
                "industry": ["Economic development", "Manufacturing", "Oil and gas", "Banking"],
                "jurisdiction": ["Abu Dhabi", "GCC region"],
                "type": ["Public sector", "Private sector"]
            },
            "impacted_functions": [
                "Economic Strategy", "Risk Management", "Compliance"
            ]
        },
        "entry_id": "04cd53c3-b84c-4f0d-bd22-011ec8174c4d",
        "reconciled_published_date": {
            "date": "2026-01-13",
            "valid": true,
            "source": "API"
        }
    },
    "feed_entry_id": "1885f505-d2c1-429e-9039-69865c5bd2a8",
    "topic_id": null,
    "user_id": null
}
```

**Working with Annotations**:
- Annotations are returned as raw Python dictionaries (not DataFrames)
- Use pandas for advanced analysis: `pd.json_normalize(annotations)`
- Scores are objects with `label`, `score`, and `confidence` fields
- Access impact summary: `ann['annotation']['metadata']['impact_summary']['objective']`

**Common Patterns**:
```python
import pandas as pd
from collections import Counter

annotations = client.get_annotations(topic_ids=["topic-123"])

# Extract impact scores
for ann in annotations:
    impact = ann['annotation']['scores']['impact']
    print(f"Impact: {impact['label']} (score: {impact['score']}, confidence: {impact['confidence']})")

# Filter by high impact
high_impact = [
    a for a in annotations
    if a['annotation']['scores']['impact']['score'] > 5
]

# Analyze update types
df = pd.json_normalize(annotations)
print(df['annotation.classification.update_type'].value_counts())

# Aggregate tags across all annotations
all_tags = []
for ann in annotations:
    tags = ann['annotation']['metadata'].get('tags', [])
    all_tags.extend(tags)
tag_counts = Counter(all_tags)
print(tag_counts.most_common(10))

# Analyze impacted industries
industries = []
for ann in annotations:
    industries.extend(
        ann['annotation']['metadata']['impacted_business'].get('industry', [])
    )
industry_counts = Counter(industries)
```

---

## Module API Reference

### carver_feeds.carver_api

#### `CarverFeedsAPIClient`

**Initialization**:
```python
from carver_feeds import CarverFeedsAPIClient

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

##### `get_topic_entries(topic_id: str, limit: int = 500) -> List[Dict]`
Fetch entries for all feeds in a topic.

**Parameters**:
- `topic_id`: Topic identifier (required)
- `limit`: Maximum entries to return (default: 500)

**Returns**: List of entry dictionaries

**Optimization**: Faster than fetching all entries when you only need one topic.

---

##### `get_user_topic_subscriptions(user_id: str) -> Dict[str, Any]`
Fetch topic subscriptions for a specific user.

**Parameters**:
- `user_id`: User identifier (required)

**Returns**: Dictionary with:
- `subscriptions`: List of topic dictionaries
- `total_count`: Total number of subscriptions

**Raises**:
- `ValueError`: If `user_id` is not provided
- `AuthenticationError`: Invalid API key
- `CarverAPIError`: API request failed or response validation failed

**Example**:
```python
from carver_feeds import get_client

client = get_client()
result = client.get_user_topic_subscriptions("user-123")
print(f"User has {result['total_count']} subscriptions")
for topic in result['subscriptions']:
    print(f"- {topic['name']}")
```

---

##### `get_annotations(feed_entry_ids=None, topic_ids=None, user_ids=None) -> List[Dict[str, Any]]`
Retrieve annotations filtered by specific criteria.

**Parameters** (exactly one required):
- `feed_entry_ids`: List of Feed Entry UUIDs (optional)
- `topic_ids`: List of Topic UUIDs (optional)
- `user_ids`: List of User UUIDs (optional)

**Returns**: List of annotation dictionaries (see Annotation Schema)

**Raises**:
- `ValueError`: If no filter provided, multiple filters provided, or empty filter list
- `AuthenticationError`: Invalid API key
- `CarverAPIError`: API request failed or response validation failed

**Important**: Only one filter type can be used per request. The SDK validates this constraint.

**Examples**:
```python
from carver_feeds import get_client

client = get_client()

# Filter by feed entry IDs
annotations = client.get_annotations(
    feed_entry_ids=["entry-uuid-1", "entry-uuid-2"]
)

# Filter by topic IDs
annotations = client.get_annotations(topic_ids=["topic-uuid-1"])

# Filter by user IDs
annotations = client.get_annotations(user_ids=["user-uuid-1"])

# Process results
for ann in annotations:
    print(f"Entry: {ann['feed_entry_id']}")
    print(f"Summary: {ann['annotation']['summary']}")
    print(f"Relevance: {ann['annotation']['scores']['relevance']:.2f}")

# Filter by importance score
high_importance = [
    a for a in annotations
    if a['annotation']['scores']['importance'] > 0.8
]
```

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
from carver_feeds import get_client

client = get_client()  # Uses .env configuration
topics = client.list_topics()
```

---

### carver_feeds.data_manager

#### `FeedsDataManager`

**Initialization**:
```python
from carver_feeds import FeedsDataManager, get_client

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

##### `get_topic_entries_df(topic_id: str, is_active: Optional[bool] = None, fetch_content: bool = False, s3_client: Optional[S3ContentClient] = None) -> pd.DataFrame`
Fetch entries for a specific topic as a pandas DataFrame.

**Parameters**:
- `topic_id`: Topic identifier (required)
- `is_active`: Filter by active status (optional)
- `fetch_content`: Fetch content from S3 (default: False, requires AWS credentials)
- `s3_client`: S3 client instance (optional, auto-created if not provided)

**Returns**: DataFrame with entry schema

**Performance**:
- Without `fetch_content`: Fast, fetches only metadata
- With `fetch_content=True`: Additional time for S3 fetches (~1-2s per 100 entries)

**S3 Content Fetching (v0.2.0+)**:
Content is no longer returned by the API. To fetch content from S3:
1. Configure AWS credentials (AWS profile or direct credentials)
2. Use `fetch_content=True` to automatically fetch from S3
3. Content will be populated in `entry_content_markdown` column

**Example**:
```python
# Entries without content (fast)
entries = dm.get_topic_entries_df(topic_id="topic-123")

# Entries with content from S3 (requires AWS credentials)
entries_with_content = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=True)
```

---

##### `get_user_topic_subscriptions_df(user_id: str) -> pd.DataFrame`
Fetch user topic subscriptions as a pandas DataFrame.

**Parameters**:
- `user_id`: User identifier (required)

**Returns**: DataFrame with columns:
- `id`: Topic ID
- `name`: Topic name
- `description`: Topic description
- `base_domain`: Base domain (may be null)

**Raises**:
- `ValueError`: If `user_id` is not provided
- `CarverAPIError`: If API request fails

**Use Cases**:
- Display user's subscribed topics
- Filter content based on user preferences
- Track user interests for analytics

**Example**:
```python
from carver_feeds import create_data_manager

dm = create_data_manager()
subscriptions = dm.get_user_topic_subscriptions_df("user-123")
print(f"User has {len(subscriptions)} subscriptions")
print(subscriptions[['id', 'name']].head())
```

**Note**: The API response includes a `total_count` field which is not included in the DataFrame. Use the raw API method `get_user_topic_subscriptions()` if you need this value.

---

##### `get_hierarchical_view(include_entries: bool = True, topic_id: Optional[str] = None) -> pd.DataFrame`
Build denormalized hierarchical view combining topics and entries.

**Parameters**:
- `include_entries`: Include entry data (default: True)
- `topic_id`: Filter to specific topic (optional)

**Returns**: DataFrame with hierarchical schema (topic_*, entry_* columns)

**Implementation Details**:
- Fetches topics and optionally entries
- Enriches each entry with topic metadata: topic_id, topic_name
- **Guarantees**: ALL entries ALWAYS have complete topic metadata

**Performance Characteristics**:
- `topic_id` specified: 1 API call for topic entries (fast)
- No filter: Fetches entries for ALL topics (slow, not recommended)

**Example**:
```python
# Topic only (fast, no entries)
hierarchy = dm.get_hierarchical_view(include_entries=False)

# Full hierarchy for specific topic (fast, 1 API call)
topic_full = dm.get_hierarchical_view(include_entries=True, topic_id="topic-123")
```

---

#### `create_data_manager() -> FeedsDataManager`
Factory function to create data manager from environment configuration.

**Returns**: Configured `FeedsDataManager` instance

**Example**:
```python
from carver_feeds import create_data_manager

dm = create_data_manager()  # Uses .env for API key
topics = dm.get_topics_df()
```

---

### carver_feeds.s3_client

#### `S3ContentClient`

**Description**: Client for fetching entry content from AWS S3 storage (v0.2.0+).

**Initialization**:
```python
from carver_feeds import S3ContentClient

# Method 1: Using AWS Profile (recommended for local development)
s3_client = S3ContentClient(
    aws_profile_name="your-aws-profile",
    aws_region="us-east-1"
)

# Method 2: Using Direct Credentials (for CI/CD)
s3_client = S3ContentClient(
    aws_access_key_id="your_access_key",
    aws_secret_access_key="your_secret_key",
    aws_region="us-east-1"
)
```

**Authentication Priority**:
1. AWS Profile (`aws_profile_name`) takes precedence if provided
2. Falls back to direct credentials (`aws_access_key_id` + `aws_secret_access_key`)
3. Falls back to boto3 default credential chain

**Methods**:

##### `fetch_content(s3_path: str) -> Optional[str]`
Fetch content from S3 given an S3 path.

**Parameters**:
- `s3_path`: Full S3 path (e.g., "s3://bucket/path/content.md")

**Returns**: Content as string, or None if fetch fails

**Example**:
```python
s3_client = S3ContentClient(aws_profile_name="my-profile")
content = s3_client.fetch_content("s3://bucket/path/content.md")
```

##### `fetch_content_batch(s3_paths: List[str]) -> Dict[str, Optional[str]]`
Fetch multiple content files from S3 in batch.

**Parameters**:
- `s3_paths`: List of S3 paths

**Returns**: Dictionary mapping S3 path to content (or None if failed)

**Example**:
```python
paths = ["s3://bucket/path1.md", "s3://bucket/path2.md"]
contents = s3_client.fetch_content_batch(paths)
for path, content in contents.items():
    print(f"{path}: {len(content) if content else 0} chars")
```

---

#### `get_s3_client() -> S3ContentClient`
Factory function to create S3 client from environment variables.

**Environment Variables**:
- `AWS_PROFILE_NAME`: AWS profile name (Method 1)
- `AWS_ACCESS_KEY_ID`: Access key (Method 2)
- `AWS_SECRET_ACCESS_KEY`: Secret key (Method 2)
- `AWS_REGION`: AWS region (optional, defaults to us-east-1)

**Returns**: Configured `S3ContentClient` instance, or None if no credentials available

**Graceful Degradation**: Returns None if no AWS credentials configured. SDK continues to work without S3 content fetching.

**Example**:
```python
from carver_feeds import get_s3_client, create_data_manager

# Auto-load from environment
s3_client = get_s3_client()

if s3_client:
    # Fetch content with S3 client
    dm = create_data_manager()
    entries = dm.get_entries_df(feed_id="feed-456", fetch_content=True, s3_client=s3_client)
else:
    print("AWS credentials not configured. Content fetching disabled.")
```

---

### carver_feeds.query_engine

#### `EntryQueryEngine`

**Initialization**:
```python
from carver_feeds import EntryQueryEngine, create_data_manager

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

**Prerequisites**: Must call `filter_by_topic()` before searching to load data.

**Parameters**:
- `keywords`: Single keyword or list of keywords
- `search_fields`: Fields to search in (default: `['entry_content_markdown']`)
- `case_sensitive`: Case-sensitive search (default: False)
- `match_all`: All keywords must match (AND) vs any keyword (OR) (default: False)

**Available search fields**:
- `entry_content_markdown` (full article content, requires `fetch_content()` in v0.2.0+)
- `entry_title` (headline)
- `entry_link` (URL)
- `entry_description` (summary)

**Returns**: Self for method chaining

**Example**:
```python
# Search in title/description (no S3 required)
results = qe.filter_by_topic(topic_name="Banking") \
    .search_entries("regulation", search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

# Search in full content (requires fetch_content)
results = qe.filter_by_topic(topic_name="Banking") \
    .fetch_content() \
    .search_entries("regulation") \
    .to_dataframe()

# Search for any of multiple keywords
results = qe.filter_by_topic(topic_name="Banking") \
    .search_entries(["banking", "finance"], match_all=False,
                   search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

# Search for all keywords
results = qe.filter_by_topic(topic_name="Banking") \
    .search_entries(["banking", "regulation"], match_all=True,
                   search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()
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
from carver_feeds import create_query_engine

qe = create_query_engine()  # Uses .env for API key
results = qe.search_entries("regulation").to_dataframe()
```

---

## Common Patterns

### Pattern 1: Basic Topic Exploration

```python
from carver_feeds import create_data_manager

dm = create_data_manager()

# List all topics
topics_df = dm.get_topics_df()
print(f"Available topics: {len(topics_df)}")
print(topics_df[['id', 'name', 'is_active']].head(10))

# Get entries for a topic without content (fast, works without AWS)
topic_id = topics_df['id'].iloc[0]
entries_df = dm.get_topic_entries_df(topic_id=topic_id)
print(f"Entries: {len(entries_df)}")

# Get entries with content from S3 (requires AWS credentials)
entries_with_content = dm.get_topic_entries_df(topic_id=topic_id, fetch_content=True)
print(f"Entries with content: {len(entries_with_content)}")
```

### Pattern 2: Keyword Search with Filters

```python
from carver_feeds import create_query_engine
from datetime import datetime

qe = create_query_engine()

# Search with multiple filters (in title/description, no S3 required)
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .filter_by_active(is_active=True) \
    .search_entries(["regulation", "compliance"],
                   search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

print(f"Found {len(results)} results")
print(results[['entry_title', 'topic_name', 'entry_published_at']].head())
```

### Pattern 3: Topic-Specific Analysis

```python
from carver_feeds import create_query_engine

qe = create_query_engine()

# Get all entries from specific topic
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Analyze by date
results['month'] = results['entry_published_at'].dt.to_period('M')
monthly_counts = results.groupby('month').size()
print("Entries per month:")
print(monthly_counts.tail(6))
```

### Pattern 4: Export Workflow

```python
from carver_feeds import create_query_engine

qe = create_query_engine()

# Filter data (search in title/description, no S3 required)
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .search_entries("regulation", search_fields=['entry_title', 'entry_description'])

# Export in multiple formats
df = results.to_dataframe()
dict_list = results.to_dict()
json_str = results.to_json(indent=2)
csv_path = results.to_csv("banking_regulations.csv")

print(f"Exported {len(df)} entries to CSV at {csv_path}")
```

### Pattern 5: Multi-Topic Comparison

```python
from carver_feeds import create_query_engine
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
from carver_feeds import create_data_manager

dm = create_data_manager()

# Filter by topic for optimized endpoint
entries = dm.get_topic_entries_df(topic_id="topic-123")  # Fast, optimized endpoint

# Then do analysis on filtered data
print(f"Loaded {len(entries)} entries for topic")

# Note: In v0.2.0+, entry_content_markdown requires S3 fetch
# Use fetch_content=True to enable content search
entries_with_content = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=True)
keyword_matches = entries_with_content[
    entries_with_content['entry_content_markdown'].str.contains("regulation", case=False, na=False)
]
print(f"Found {len(keyword_matches)} matching entries")
```

### Pattern 7: Lazy vs Eager Content Loading (v0.2.0+)

```python
from carver_feeds import create_data_manager, get_s3_client

dm = create_data_manager()
s3_client = get_s3_client()

# Lazy loading: Fetch metadata first, content only when needed
entries = dm.get_topic_entries_df(topic_id="topic-123")  # Fast, no S3 fetch
print(f"Found {len(entries)} entries")

# Filter based on metadata (title, description, dates)
recent_entries = entries[entries['published_at'] > '2024-01-01']
print(f"Filtered to {len(recent_entries)} recent entries")

# Eager loading: Fetch content for filtered subset only
if s3_client and len(recent_entries) > 0:
    for idx, row in recent_entries.iterrows():
        s3_path = row['s3_content_md_path']
        if s3_path:
            content = s3_client.fetch_content(s3_path)
            recent_entries.at[idx, 'entry_content_markdown'] = content
    print(f"Fetched content for {len(recent_entries)} entries")

# Alternative: Fetch all content upfront (easier but slower)
all_with_content = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=True)
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
from carver_feeds import get_client, AuthenticationError

try:
    client = get_client()
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    print("Check your .env file and CARVER_API_KEY")
```

#### `RateLimitError`
**Cause**: Exceeded API rate limit (10 req/sec)

**Solution**: SDK automatically retries with backoff. If persistent, reduce request frequency.

#### `CarverAPIError`
**Cause**: General API error (network, server error, etc.)

**Solution**: Check error message for details. May need to retry manually.

### Error Handling Best Practices

```python
from carver_feeds import create_query_engine, CarverAPIError, AuthenticationError
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
| List all entries (no content) | ~10,000 | ~30-60 seconds |
| List all entries (with S3 content) | ~10,000 | ~60-120 seconds |
| Entries for specific feed (no content) | Varies | ~2-10 seconds |
| Entries for specific feed (with S3 content) | Varies | ~3-15 seconds |
| Entries for specific topic (no content) | Varies | ~5-20 seconds |
| Entries for specific topic (with S3 content) | Varies | ~10-40 seconds |
| S3 content fetch (per 100 entries) | 100 | ~1-2 seconds |

**Note (v0.2.0+):** Content fetching from S3 adds overhead. For large datasets, consider lazy loading: fetch metadata first, then fetch content only for filtered results.

### Optimization Strategies

1. **Use Topic Filtering**: Always filter by topic for optimized endpoint
   ```python
   # Optimized: filter by topic
   filtered = dm.get_topic_entries_df(topic_id='topic-123')
   ```

2. **Lazy Loading**: Query engine loads data only when filter_by_topic is called
   ```python
   qe = create_query_engine()  # Fast, no API call
   results = qe.filter_by_topic(topic_name="Banking") \
       .search_entries("regulation", search_fields=['entry_title']) \
       .to_dataframe()  # API call happens on filter_by_topic
   ```

3. **Reuse Query Engine**: Data is cached after first load
   ```python
   qe = create_query_engine()

   # First query: loads data (~30-60s)
   results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()

   # Subsequent queries: use cached data (instant)
   results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
   ```

4. **Always Start with Topic Filter**: The query engine requires filtering by topic first
   ```python
   # Required pattern
   results = qe.filter_by_topic(topic_name="Banking").to_dataframe()
   ```

### Memory Considerations

**DataFrame sizes** (approximate):

| Data | Rows | Memory |
|------|------|--------|
| Topics | ~114 | < 1 MB |
| Feeds | ~827 | ~5 MB |
| Entries (no content) | ~10,000 | ~20-50 MB |
| Entries (with S3 content) | ~10,000 | ~100-200 MB |
| Hierarchical (with entries, no content) | ~10,000 | ~50-100 MB |
| Hierarchical (with entries + content) | ~10,000 | ~200-400 MB |

**Recommendation**: For large result sets, export to CSV and process externally rather than loading full DataFrame into memory.

**v0.2.0+ Optimization**: Content is the largest component of memory usage. Fetch content only when needed using `fetch_content=True` selectively, or use lazy loading patterns to fetch content for filtered subsets.

---

## Additional Resources

- **[User Guide](README.md)**: Complete SDK documentation and usage guide
- **[Usage Examples](examples.md)**: 9 comprehensive examples covering common workflows
- **[PyPI Package](https://pypi.org/project/carver-feeds-sdk/)**: Package information and version history
- **[GitHub Repository](https://github.com/carveragents/carver-feeds-sdk)**: Source code and issue tracking

---

**Document Version**: 2.0
**Last Updated**: 2025-10-26
**SDK Version**: 0.2.0+
**Status**: Production Ready
