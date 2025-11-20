# Carver Feeds SDK Architecture - v0.2.0

## Current Architecture (v0.1.x)

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Application                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ create_query_engine()
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EntryQueryEngine                            │
│  - filter_by_topic()                                             │
│  - filter_by_feed()                                              │
│  - search_entries()                                              │
│  - to_dataframe()                                                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ get_hierarchical_view()
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FeedsDataManager                            │
│  - get_topics_df()                                               │
│  - get_feeds_df()                                                │
│  - get_entries_df()                                              │
│  - get_hierarchical_view()                                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ list_entries(), get_feed_entries()
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CarverFeedsAPIClient                          │
│  - list_topics()                                                 │
│  - list_feeds()                                                  │
│  - list_entries()                                                │
│  - get_feed_entries()                                            │
│  - get_topic_entries()                                           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ HTTPS + X-API-Key
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Carver API                                │
│  GET /api/v1/feeds/topics                                        │
│  GET /api/v1/feeds/                                              │
│  GET /api/v1/feeds/entries/list                                  │
│  GET /api/v1/feeds/{id}/entries                                  │
│  GET /api/v1/feeds/topics/{id}/entries                           │
│                                                                   │
│  Response: { id, title, link, content_markdown, ... }            │
│            ^^^^^^^^^^^^^^^^^^^^^^                                │
│            DEPRECATED - No longer returned                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## New Architecture (v0.2.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Application                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ create_query_engine(fetch_content=True)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EntryQueryEngine                            │
│  - filter_by_topic()                                             │
│  - filter_by_feed()                                              │
│  - search_entries()                                              │
│  - fetch_content() ◄──────────────────────────┐ NEW              │
│  - to_dataframe()                             │                  │
└─────────────────────────────────────────────┬─┘                  │
                               │              │                    │
                               │              │ S3 content         │
                               ▼              │ fetching           │
┌─────────────────────────────────────────────┼────────────────────┤
│                      FeedsDataManager        │                    │
│  - get_topics_df()                           │                    │
│  - get_feeds_df()                            │                    │
│  - get_entries_df(fetch_content=True) ◄──────┘ NEW               │
│  - get_hierarchical_view(fetch_content=True) ◄─ NEW              │
│  - _fetch_contents_from_s3() ◄──────────────────┐ NEW            │
└─────────────────────────────────────────────────┼────────────────┘
                    │                             │
                    │                             │ fetch_content_batch()
                    ▼                             ▼
┌────────────────────────────────┐  ┌───────────────────────────────┐
│   CarverFeedsAPIClient         │  │   S3ContentClient ◄────────── NEW
│  - list_topics()               │  │  - fetch_content()            │
│  - list_feeds()                │  │  - fetch_content_batch()      │
│  - list_entries()              │  │  - parse_s3_path()            │
│  - get_feed_entries()          │  │  - AWS profile auth           │
│  - get_topic_entries()         │  │  - Parallel fetching          │
└────────────────┬───────────────┘  └───────────────┬───────────────┘
                 │                                  │
                 │ HTTPS + X-API-Key                │ AWS S3 API
                 ▼                                  ▼
┌────────────────────────────────┐  ┌───────────────────────────────┐
│         Carver API             │  │         AWS S3                │
│  GET /api/v1/feeds/topics      │  │  Bucket: carver-prod-data     │
│  GET /api/v1/feeds/            │  │                               │
│  GET /api/v1/feeds/entries/list│  │  GET /regulatory/feeds/.../   │
│  GET /api/v1/feeds/{id}/entries│  │      content.md               │
│  GET /api/v1/feeds/topics/...  │  │                               │
│                                │  │  Returns: markdown content    │
│  Response:                     │  └───────────────────────────────┘
│  {                             │
│    id, title, link,            │
│    extracted_metadata: {       │
│      feed_id,                  │
│      topic_id,                 │
│      timestamp,                │
│      status,                   │
│      s3_content_md_path ◄──────┼─── Used to fetch from S3
│      ...                       │
│    }                           │
│  }                             │
└────────────────────────────────┘
```

---

## Data Flow - Content Fetching (v0.2.0)

### Flow 1: Without Content (Default, Fast)

```
User: dm.get_entries_df()
  │
  ├─► FeedsDataManager.get_entries_df(fetch_content=False)
  │     │
  │     ├─► CarverFeedsAPIClient.list_entries()
  │     │     │
  │     │     └─► API: { id, title, extracted_metadata: {...} }
  │     │
  │     ├─► Extract metadata fields: feed_id, topic_id, s3_content_md_path
  │     │
  │     └─► Return DataFrame:
  │           - content_markdown: None (not fetched)
  │           - feed_id: from extracted_metadata
  │           - topic_id: from extracted_metadata
  │           - s3_content_md_path: from extracted_metadata
  │
  └─► User gets DataFrame without content (fast, no S3 calls)
```

### Flow 2: With Content (Eager Loading)

```
User: dm.get_entries_df(fetch_content=True)
  │
  ├─► FeedsDataManager.get_entries_df(fetch_content=True)
  │     │
  │     ├─► CarverFeedsAPIClient.list_entries()
  │     │     │
  │     │     └─► API: { id, title, extracted_metadata: {...} }
  │     │
  │     ├─► Extract metadata fields
  │     │
  │     ├─► S3ContentClient.fetch_content_batch([s3_path1, s3_path2, ...])
  │     │     │
  │     │     ├─► Authenticate with AWS profile
  │     │     │
  │     │     ├─► Parallel S3 requests (10 workers)
  │     │     │     │
  │     │     │     └─► S3: GET content.md
  │     │     │
  │     │     └─► Return: {s3_path1: content1, s3_path2: content2, ...}
  │     │
  │     ├─► Map S3 content back to DataFrame rows
  │     │
  │     └─► Return DataFrame:
  │           - content_markdown: fetched from S3
  │           - feed_id: from extracted_metadata
  │           - topic_id: from extracted_metadata
  │
  └─► User gets DataFrame with content (slower, S3 calls made)
```

### Flow 3: Lazy Content Fetching (Recommended, Optimal)

```
User: qe.filter_by_topic(...).fetch_content().to_dataframe()
  │
  ├─► EntryQueryEngine.filter_by_topic(topic_name="Banking")
  │     │
  │     ├─► Load hierarchical view (fetch_content=False, fast)
  │     │     └─► DataFrame: 10,000 entries, no content
  │     │
  │     └─► Filter: topic_name="Banking"
  │           └─► Filtered: 500 entries
  │
  ├─► EntryQueryEngine.fetch_content()
  │     │
  │     ├─► S3ContentClient.fetch_content_batch([500 s3_paths])
  │     │     │
  │     │     └─► S3: Fetch only 500 entries (not 10,000!)
  │     │
  │     └─► Update DataFrame with content
  │
  └─► User gets filtered DataFrame with content (optimal performance)
```

---

## Component Responsibilities

### CarverFeedsAPIClient
- **HTTP communication** with Carver API
- **Authentication** (X-API-Key header)
- **Pagination** handling
- **Retry logic** for rate limits (429) and server errors (500)
- Returns **raw dict responses** (no transformation)

### FeedsDataManager
- **JSON to DataFrame** conversion
- **Schema validation** and field mapping
- **Metadata extraction** from `extracted_metadata`
- **Hierarchical view** construction (topic → feed → entry)
- **S3 content orchestration** (when fetch_content=True)

### EntryQueryEngine
- **Fluent query interface** with method chaining
- **Filtering** by topic, feed, date, status
- **Keyword search** across content fields
- **Lazy content fetching** via `fetch_content()` method
- **Export** to DataFrame, JSON, CSV

### S3ContentClient (NEW)
- **AWS profile-based authentication** (secure credential management)
- **Content fetching** from S3 paths
- **Batch fetching** with parallel requests (no built-in caching)
- **Error handling** and retry logic for S3 operations
- **Graceful degradation** when profile not configured

---

## Authentication Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                      S3ContentClient                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              AWS Profile Authentication                   │   │
│  │                                                            │   │
│  │  1. Read AWS_PROFILE_NAME from environment                │   │
│  │     └─► Example: "carver-prod"                            │   │
│  │                                                            │   │
│  │  2. boto3.Session(profile_name=profile_name)              │   │
│  │     └─► Loads credentials from ~/.aws/credentials         │   │
│  │                                                            │   │
│  │  3. Create S3 client with session                         │   │
│  │     └─► session.client('s3', region_name=region)          │   │
│  │                                                            │   │
│  │  ~/.aws/credentials format:                               │   │
│  │  [carver-prod]                                            │   │
│  │  aws_access_key_id = YOUR_KEY                             │   │
│  │  aws_secret_access_key = YOUR_SECRET                      │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Benefits:
- More secure (credentials not in .env or code)
- Follows AWS best practices
- Supports role assumption and MFA if configured
- Easier credential rotation
- Multiple profiles for different environments
```

---

## Performance Optimization

### Sequential Fetching (Slow)
```
For each entry in DataFrame:
    content = s3_client.fetch_content(entry.s3_path)  # 100-200ms per fetch
    entry.content_markdown = content

Total time for 100 entries: ~10-20 seconds
```

### Batch Fetching (Fast)
```
all_paths = [entry.s3_path for entry in DataFrame]
content_map = s3_client.fetch_content_batch(all_paths, max_workers=10)

# Parallel fetching with ThreadPoolExecutor
# 10 concurrent S3 requests

For each entry in DataFrame:
    entry.content_markdown = content_map[entry.s3_path]

Total time for 100 entries: ~1-2 seconds (10x faster!)
```

---

## Error Handling Flow

```
User: dm.get_entries_df(fetch_content=True)
  │
  ├─► Check S3 credentials
  │     │
  │     ├─► If missing:
  │     │     └─► Log warning: "S3 credentials not configured"
  │     │         └─► Set content_markdown = None
  │     │             └─► Continue (graceful degradation)
  │     │
  │     └─► If present:
  │           └─► Proceed to S3 fetch
  │
  ├─► S3ContentClient.fetch_content_batch()
  │     │
  │     ├─► For each S3 path:
  │     │     │
  │     │     ├─► Try fetch from S3
  │     │     │     │
  │     │     │     ├─► Success → Cache + Return content
  │     │     │     │
  │     │     │     └─► Error:
  │     │     │           │
  │     │     │           ├─► Transient (500, timeout):
  │     │     │           │     └─► Retry with exponential backoff
  │     │     │           │           └─► Max 3 retries
  │     │     │           │
  │     │     │           └─► Permanent (404, 403):
  │     │     │                 └─► Log warning
  │     │     │                     └─► Return None (don't retry)
  │     │     │
  │     │     └─► Add to content_map: {s3_path: content or None}
  │     │
  │     └─► Return content_map
  │
  ├─► Map content to DataFrame
  │     │
  │     └─► Some entries may have content_markdown = None (fetch failed)
  │
  └─► Return DataFrame (partial success is OK)
```

---

## Backward Compatibility

### v0.1.x Code (Still Works in v0.2.0)

```python
# User code (no changes needed)
from carver_feeds import create_data_manager

dm = create_data_manager()
entries = dm.get_entries_df()  # fetch_content=False by default

# DataFrame columns:
# - id, title, link ✓ (unchanged)
# - content_markdown ✓ (now None, previously had content)
# - published_at, created_at, is_active ✓ (unchanged)

# Code doesn't break, but content_markdown is None
# User sees warning: "Content no longer in API, use fetch_content=True"
```

### v0.2.0 Code (New Features)

```python
# New usage with content
from carver_feeds import create_data_manager

dm = create_data_manager()
entries = dm.get_entries_df(fetch_content=True)  # NEW parameter

# DataFrame columns:
# - id, title, link ✓
# - content_markdown ✓ (fetched from S3)
# - feed_id ✓ (NEW: from extracted_metadata)
# - topic_id ✓ (NEW: from extracted_metadata)
# - content_status ✓ (NEW: extraction status)
# - content_timestamp ✓ (NEW: last fetch time)
# - s3_content_md_path ✓ (NEW: S3 path)
# - published_at, created_at, is_active ✓
```

---

## Future Architecture (v0.3.0)

### Potential Enhancements

1. **Async S3 Fetching**
   ```
   AsyncS3ContentClient with asyncio
   → Even faster parallel fetching
   → Better resource utilization
   ```

2. **Persistent Cache (Redis/Disk)**
   ```
   S3ContentClient(cache_backend='redis')
   → Content persists across sessions
   → Reduced S3 costs
   ```

3. **Content Version Tracking**
   ```
   Track content changes using timestamp field
   → Detect when entries are re-crawled
   → Historical content analysis
   ```

4. **HTML Content Support**
   ```
   dm.get_entries_df(fetch_content=True, content_format='html')
   → Fetch from s3_content_html_path
   → Support HTML-based analysis
   ```

5. **Smart Prefetching**
   ```
   Predict which entries user will access next
   → Prefetch content in background
   → Instant access when needed
   ```
