# Quick Reference - extracted_metadata Integration

## API Response Changes

### Before (v0.1.x)
```json
{
  "id": "entry-123",
  "title": "Banking Regulation Update",
  "link": "https://...",
  "content_markdown": "# Full article content here...",
  "published_date": "2024-11-15T10:00:00Z",
  "created_at": "2024-11-15T10:05:00Z",
  "is_active": true
}
```

### After (v0.2.0)
```json
{
  "id": "entry-123",
  "title": "Banking Regulation Update",
  "link": "https://...",
  "extracted_metadata": {
    "feed_id": "feed-456",
    "topic_id": "topic-789",
    "timestamp": "2025-11-16T18:21:25.300928+00:00",
    "status": "done",
    "s3_content_md_path": "s3://bucket/path/content.md",
    "s3_content_html_path": "s3://bucket/path/content.html",
    "s3_aggregated_content_md_path": "s3://bucket/path/aggregate_content.md"
  },
  "published_date": "2024-11-15T10:00:00Z",
  "created_at": "2024-11-15T10:05:00Z",
  "is_active": true
}
```

**Key Change**: `content_markdown` removed → fetch from S3 using `s3_content_md_path`

---

## DataFrame Schema Changes

### Before (v0.1.x)
```python
df.columns = [
    'id',
    'title',
    'link',
    'content_markdown',  # Populated from API
    'published_at',
    'created_at',
    'is_active'
]
```

### After (v0.2.0, fetch_content=False)
```python
df.columns = [
    'id',
    'title',
    'link',
    'content_markdown',  # None (not fetched)
    'feed_id',  # NEW: from extracted_metadata
    'topic_id',  # NEW: from extracted_metadata
    'content_status',  # NEW: extraction status
    'content_timestamp',  # NEW: when content fetched
    's3_content_md_path',  # NEW: S3 path
    's3_content_html_path',  # NEW: S3 path
    's3_aggregated_content_md_path',  # NEW: S3 path
    'published_at',
    'created_at',
    'is_active'
]
```

### After (v0.2.0, fetch_content=True)
```python
df.columns = [
    # Same as above, but:
    'content_markdown',  # Fetched from S3!
    # ...rest same
]
```

---

## Code Migration Examples

### Example 1: No Content Needed
```python
# v0.1.x
dm = create_data_manager()
entries = dm.get_entries_df()
print(entries[['title', 'published_at']])

# v0.2.0 - NO CHANGES NEEDED
dm = create_data_manager()
entries = dm.get_entries_df()
print(entries[['title', 'published_at']])
```

### Example 2: Content Needed (Eager)
```python
# v0.1.x
dm = create_data_manager()
entries = dm.get_entries_df()
content = entries['content_markdown']  # Had content

# v0.2.0 - Add fetch_content=True
dm = create_data_manager()
entries = dm.get_entries_df(fetch_content=True)  # NEW
content = entries['content_markdown']  # Now has content
```

### Example 3: Content Needed (Lazy, Recommended)
```python
# v0.2.0 - Filter first, then fetch content
qe = create_query_engine()
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .fetch_content() \  # NEW method
    .to_dataframe()

# Only fetches content for filtered results (fast!)
```

### Example 4: Using New Metadata Fields
```python
# v0.2.0 - Access new fields
dm = create_data_manager()
entries = dm.get_entries_df()

# Filter by content status
done_entries = entries[entries['content_status'] == 'done']

# Group by feed (now available at entry level!)
by_feed = entries.groupby('feed_id')['title'].count()

# Check content freshness
recent = entries[entries['content_timestamp'] > datetime(2024, 11, 1)]
```

---

## Environment Configuration

### .env File
```bash
# Existing (required)
CARVER_API_KEY=your_api_key_here

# NEW (required for content fetching)
AWS_PROFILE_NAME=carver-prod  # Name of AWS profile in ~/.aws/credentials
AWS_REGION=us-east-1          # Optional (default: us-east-1)
```

### AWS Credentials File (~/.aws/credentials)
```ini
[carver-prod]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

### AWS Config File (~/.aws/config) - Optional
```ini
[profile carver-prod]
region = us-east-1
```

---

## Key Design Decisions

### 1. Lazy Loading by Default
**Why**: Most users don't need content for all 10,000+ entries
```python
# Fast (no S3 calls)
entries = dm.get_entries_df()

# Slow (fetches all content from S3)
entries = dm.get_entries_df(fetch_content=True)

# Optimal (filter first, fetch only matches)
qe.filter_by_topic(...).fetch_content().to_dataframe()
```

### 2. Graceful Degradation
**Why**: Don't crash if S3 unavailable
```python
# If S3 credentials missing:
# - Log warning
# - Set content_markdown = None
# - Continue execution (don't crash)

# If S3 fetch fails:
# - Log warning for that entry
# - Set content_markdown = None for that entry
# - Continue fetching other entries
```

### 3. Backward Compatibility
**Why**: Existing code should continue to work
```python
# v0.1.x code
entries = dm.get_entries_df()

# Still works in v0.2.0, just:
# - content_markdown is None (instead of actual content)
# - New columns added (feed_id, topic_id, etc.)
# - No errors thrown
```

### 4. Batch Fetching
**Why**: Performance - parallel S3 requests
```python
# Bad: Sequential (10-20 seconds for 100 entries)
for entry in entries:
    content = s3.fetch_content(entry.s3_path)

# Good: Parallel (1-2 seconds for 100 entries)
content_map = s3.fetch_content_batch(s3_paths, max_workers=10)
```

### 5. User-Implemented Caching (Optional)
**Why**: SDK doesn't cache, but users can add caching if needed
```python
# SDK fetches fresh every time (no built-in cache)
entries1 = qe.filter_by_topic("Banking").fetch_content().to_dataframe()
entries2 = qe.chain().filter_by_topic("Banking").fetch_content().to_dataframe()

# Implement your own cache if needed (see Pattern 5 below)
```

---

## Common Patterns

### Pattern 1: Filter → Fetch → Export
```python
qe = create_query_engine()
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries(["regulation", "compliance"]) \
    .fetch_content() \
    .to_csv("results.csv")
```

### Pattern 2: Custom S3 Client with Specific Profile
```python
from carver_feeds import S3ContentClient, create_data_manager

# Use a different AWS profile (e.g., staging vs production)
s3 = S3ContentClient(
    profile_name='carver-staging',
    region_name='us-west-2'
)

dm = create_data_manager()
entries = dm.get_entries_df(fetch_content=True, s3_client=s3)
```

### Pattern 3: Implement Your Own Caching
```python
from functools import lru_cache

class CachedS3Client:
    def __init__(self, s3_client, maxsize=1000):
        self.s3_client = s3_client
        self._fetch = lru_cache(maxsize=maxsize)(self._fetch_impl)

    def _fetch_impl(self, s3_path):
        return self.s3_client.fetch_content(s3_path)

    def fetch_content(self, s3_path):
        return self._fetch(s3_path)

# Use the cached client
s3 = S3ContentClient(profile_name='carver-prod')
cached_s3 = CachedS3Client(s3, maxsize=5000)
```

### Pattern 4: Save to Disk for Repeated Analysis
```python
import json

# Fetch once and save
dm = create_data_manager()
entries = dm.get_entries_df(fetch_content=True)
entries.to_parquet('entries_with_content.parquet')

# Later: load from disk (no S3 fetch needed)
import pandas as pd
entries = pd.read_parquet('entries_with_content.parquet')
```

---

## Performance Guidelines

### Small Queries (<100 entries)
```python
# Eager loading is fine
entries = dm.get_entries_df(feed_id="feed-123", fetch_content=True)
# Time: ~1-2 seconds
```

### Medium Queries (100-1000 entries)
```python
# Use lazy loading
qe = create_query_engine()
results = qe.filter_by_topic(...).fetch_content().to_dataframe()
# Time: ~10-20 seconds
```

### Large Queries (1000+ entries)
```python
# Filter aggressively before fetching content
qe = create_query_engine()
results = qe \
    .filter_by_topic(...) \
    .filter_by_feed(...) \
    .filter_by_date(...) \
    .fetch_content() \  # Only after heavy filtering
    .to_dataframe()
# Time: depends on filtered size
```

### Very Large Queries (10,000+ entries)
```python
# DON'T fetch content for all entries
# Instead: batch processing
topics = dm.get_topics_df()
for topic in topics.itertuples():
    # Process one topic at a time
    entries = qe.chain() \
        .filter_by_topic(topic_id=topic.id) \
        .fetch_content() \
        .to_dataframe()
    process_and_save(entries)
```

---

## Field Mapping Reference

| API Field | DataFrame Column | Type | Notes |
|-----------|------------------|------|-------|
| `id` | `id` | str | Entry ID |
| `title` | `title` | str | Entry title |
| `link` | `link` | str | Entry URL |
| `published_date` | `published_at` | datetime | When author published |
| `created_at` | `created_at` | datetime | When added to Carver |
| `is_active` | `is_active` | bool | Active status |
| `extracted_metadata.feed_id` | `feed_id` | str | Parent feed ID |
| `extracted_metadata.topic_id` | `topic_id` | str | Parent topic ID |
| `extracted_metadata.status` | `content_status` | str | "done", "pending", etc. |
| `extracted_metadata.timestamp` | `content_timestamp` | datetime | When content fetched |
| `extracted_metadata.s3_content_md_path` | `s3_content_md_path` | str | S3 path (markdown) |
| `extracted_metadata.s3_content_html_path` | `s3_content_html_path` | str | S3 path (HTML) |
| `extracted_metadata.s3_aggregated_content_md_path` | `s3_aggregated_content_md_path` | str | S3 path (aggregated) |
| *fetched from S3* | `content_markdown` | str | Entry content |

---

## Error Messages

### Missing AWS Profile Configuration
```
WARNING: AWS profile not configured. Content will not be fetched.
Set AWS_PROFILE_NAME in .env and configure ~/.aws/credentials with the profile.
See documentation: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
```

### Invalid AWS Profile
```
ERROR: AWS profile 'carver-prod' not found in ~/.aws/credentials.
Available profiles: [default, production, staging].
Configure the profile or update AWS_PROFILE_NAME.
```

### S3 Fetch Failed
```
WARNING: Failed to fetch content from s3://bucket/path/content.md: NoSuchKey
Entry 'entry-123' will have content_markdown=None
```

### Deprecated Usage
```
WARNING: Content is no longer returned directly by the API.
Use fetch_content=True to fetch content from S3.
See migration guide: https://github.com/carveragents/carver-feeds-sdk#migration-v02
```

---

## Testing Checklist

### Before Release
- [ ] Test with fetch_content=False (backward compat)
- [ ] Test with fetch_content=True (new feature)
- [ ] Test with missing AWS profile (graceful degradation)
- [ ] Test with invalid AWS profile (error handling)
- [ ] Test with invalid S3 paths (error handling)
- [ ] Test batch fetching (parallel requests)
- [ ] Test lazy loading (filter → fetch)
- [ ] Test hierarchical view improvements (feed_id/topic_id)
- [ ] Test all export formats (CSV, JSON, DataFrame, dict)
- [ ] Test with real API and S3 (integration)
- [ ] Test profile-based authentication with different profiles

### After Release
- [ ] Monitor S3 fetch performance
- [ ] Monitor user feedback
- [ ] Monitor support questions
- [ ] Track migration adoption
- [ ] Gather feedback on authentication approach

---

## Rollback Plan

If v0.2.0 has critical issues:

1. **Rollback PyPI package**
   ```bash
   # Users can pin to v0.1.2
   pip install carver-feeds-sdk==0.1.2
   ```

2. **Hotfix Release** (v0.2.1)
   - Fix critical bug
   - Maintain backward compatibility
   - Publish fixed version

3. **Communication**
   - Update README with known issues
   - Post on GitHub issues
   - Notify users via changelog

---

## Support Resources

### Documentation
- Main README: Migration guide and examples
- API Reference: Detailed method signatures
- Examples: Real-world usage patterns
- CLAUDE.md: Implementation details and gotchas

### Code Examples
- `examples/` directory with working code
- Jupyter notebooks for interactive exploration
- Test files as reference implementations

### Troubleshooting
- Check AWS profile configuration in `~/.aws/credentials`
- Verify AWS_PROFILE_NAME in `.env`
- Verify S3 paths in `extracted_metadata`
- Check logs for warnings/errors
- Test with single entry first
- Ensure AWS profile has S3 read permissions
