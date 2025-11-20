# Implementation Plan: S3-Based Content Fetching with extracted_metadata

## Executive Summary

The Carver Feeds API has been updated to include a new `extracted_metadata` field in all entry responses. This field contains S3 paths for content storage and additional metadata (feed_id, topic_id, timestamp). **Critically, the API no longer returns `content_markdown` directly** - it must now be fetched from S3 using the paths in `extracted_metadata`.

This implementation plan outlines the changes needed to:
1. Integrate boto3 for S3 content fetching
2. Update the data model to support the new `extracted_metadata` structure
3. Maintain backward compatibility for existing SDK users
4. Optimize performance with lazy loading and caching
5. Improve hierarchical mapping using embedded feed_id/topic_id

---

## 1. Current State Analysis

### 1.1 API Changes Confirmed

All three entry endpoints now return `extracted_metadata`:
- `GET /api/v1/feeds/entries/list` ✓
- `GET /api/v1/feeds/{feed_id}/entries` ✓
- `GET /api/v1/feeds/topics/{topic_id}/entries` ✓

**Critical Finding**: The `content_markdown` field is **NO LONGER** returned in API responses. Content must be fetched from S3.

### 1.2 extracted_metadata Structure

```json
{
  "url": "https://...",
  "title": "...",
  "assets": [],
  "status": "done",
  "feed_id": "d63dee54-68c2-430f-a0d7-2b7ed40d940d",
  "s3_path": "s3://...",
  "topic_id": "033afddc-b52a-4aa9-991d-5e7ac7e750e6",
  "source_id": "ceda2cb7-b27a-487a-9936-de9d159b3c9f",
  "timestamp": "2025-11-16T18:21:25.300928+00:00",
  "worker_id": "pid-1661",
  "server_name": "cf05d593be32",
  "source_type": "rss",
  "root_log_file": "/tmp/...",
  "s3_content_md_path": "s3://.../content.md",
  "s3_content_html_path": "s3://.../content.html",
  "s3_execution_log_path": "s3://...",
  "s3_aggregated_content_md_path": "s3://.../aggregate_content.md"
}
```

### 1.3 Key Fields for SDK

| Field | Purpose | Priority |
|-------|---------|----------|
| `s3_content_md_path` | Primary content source (replaces `content_markdown`) | **HIGH** |
| `s3_aggregated_content_md_path` | Alternative aggregated content | MEDIUM |
| `feed_id` | Improves hierarchical mapping (previously missing) | **HIGH** |
| `topic_id` | Improves hierarchical mapping (previously missing) | **HIGH** |
| `timestamp` | Last content fetch time (vs `published_date` = original publish) | MEDIUM |
| `status` | Content extraction status ("done", "pending", etc.) | MEDIUM |
| `s3_content_html_path` | HTML version of content | LOW |

### 1.4 Current SDK Architecture

**Three-layer design:**
1. **CarverFeedsAPIClient** (`carver_api.py`) - HTTP client, returns raw dicts
2. **FeedsDataManager** (`data_manager.py`) - Converts to DataFrames
3. **EntryQueryEngine** (`query_engine.py`) - Query interface with filtering

**Current content flow:**
- API returns `content_markdown` field → SDK passes it through → Users access via DataFrame
- **This is now broken** - no `content_markdown` in API response

---

## 2. Implementation Strategy

### 2.1 Design Principles

1. **Backward Compatibility First**: Existing code should continue to work with minimal changes
2. **Lazy Loading**: Don't fetch S3 content unless explicitly requested
3. **Opt-In Migration**: Users opt into S3 content fetching via parameter flags
4. **Graceful Degradation**: Handle missing S3 credentials or failed S3 fetches
5. **Performance Conscious**: Cache S3 content, batch requests where possible
6. **Clear Migration Path**: Document breaking changes and migration steps

### 2.2 Phased Rollout

**Phase 1: Foundation (Version 0.2.0)**
- Add boto3 as optional dependency
- Add S3 client module with credential management
- Update data models to include `extracted_metadata` fields
- Add utility functions for S3 path parsing

**Phase 2: Content Fetching (Version 0.2.0)**
- Add `fetch_content` parameter to data manager methods
- Implement S3 content fetching with caching
- Update DataFrame schema to include new fields
- Maintain backward compatibility by keeping `content_markdown` column

**Phase 3: Enhanced Features (Version 0.3.0)**
- Use `feed_id`/`topic_id` from metadata for better hierarchical mapping
- Add batch S3 fetching for performance
- Implement async S3 fetching (optional)
- Add content version tracking with `timestamp` field

---

## 3. Detailed Changes by Module

### 3.1 New Module: `s3_client.py`

**Purpose**: Centralized S3 operations with credential management and caching.

**Location**: `src/carver_feeds/s3_client.py`

**Key Features**:
- S3 credential management using AWS profiles (from env or explicit parameters)
- S3 path parsing (`s3://bucket/key` → bucket, key)
- Content fetching with error handling
- Batch fetching support
- Graceful fallback when S3 unavailable

**Public API**:
```python
class S3ContentClient:
    def __init__(
        self,
        profile_name: Optional[str] = None,
        region_name: Optional[str] = None
    )

    def fetch_content(self, s3_path: str) -> Optional[str]:
        """Fetch content from S3."""

    def fetch_content_batch(self, s3_paths: List[str]) -> Dict[str, Optional[str]]:
        """Fetch multiple contents in batch (parallel requests)."""

    @staticmethod
    def parse_s3_path(s3_path: str) -> Tuple[str, str]:
        """Parse S3 path into (bucket, key)."""

def get_s3_client(load_from_env: bool = True) -> Optional[S3ContentClient]:
    """Factory function to create S3 client from environment."""
```

**Environment Variables**:
```bash
AWS_PROFILE_NAME=carver-prod   # Required: AWS profile name from ~/.aws/credentials
AWS_REGION=us-east-1           # Optional: AWS region (default: us-east-1)
```

**AWS Profile Setup**:
Users need to configure their AWS credentials file (`~/.aws/credentials`):
```ini
[carver-prod]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

And optionally `~/.aws/config`:
```ini
[profile carver-prod]
region = us-east-1
```

**Error Handling**:
- Return `None` if AWS profile not configured (graceful degradation)
- Return `None` if S3 fetch fails (log warning, don't crash)
- Retry logic for transient S3 errors (with exponential backoff)
- Helpful error messages for profile-related authentication failures

---

### 3.2 Module: `carver_api.py`

**Changes**: Minimal - API client just returns raw responses.

**Updates**:
1. Update docstrings to mention `extracted_metadata` field
2. Update example responses in docstrings
3. No code changes needed (already returns dict as-is)

**Example Docstring Update**:
```python
def list_entries(...) -> List[Dict]:
    """
    Fetch entries from /api/v1/feeds/entries/list with pagination.

    Note: As of API v1.1, entries include an 'extracted_metadata' field
    containing S3 paths for content. The 'content_markdown' field is no
    longer returned directly. Use FeedsDataManager with fetch_content=True
    to automatically fetch content from S3.

    Returns:
        List of entry dictionaries with extracted_metadata
    """
```

---

### 3.3 Module: `data_manager.py`

**Changes**: Major - Add S3 content fetching and new field mapping.

**New Parameters**:
All entry-fetching methods get new parameters:
```python
def get_entries_df(
    self,
    feed_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    fetch_all: bool = True,
    fetch_content: bool = False,  # NEW
    s3_client: Optional[S3ContentClient] = None,  # NEW
) -> pd.DataFrame:
```

**Behavior**:
- `fetch_content=False` (default):
  - `content_markdown` column set to `None` (backward compatible)
  - All `extracted_metadata.*` fields extracted to DataFrame columns

- `fetch_content=True`:
  - Fetch content from S3 using `s3_content_md_path`
  - Populate `content_markdown` column with fetched content
  - If S3 fetch fails, `content_markdown` is `None` (with warning logged)
  - Requires S3 credentials (auto-loaded or passed via `s3_client`)

**New DataFrame Columns**:
```python
# Existing columns (unchanged)
'id', 'title', 'link', 'published_at', 'created_at', 'is_active'

# Modified column
'content_markdown'  # Now fetched from S3 (if fetch_content=True), else None

# New columns from extracted_metadata
'feed_id'  # Now ALWAYS present (from metadata, not API)
'topic_id'  # Now present (from metadata)
'content_status'  # extracted_metadata.status
'content_timestamp'  # extracted_metadata.timestamp (when content was fetched)
's3_content_md_path'  # S3 path to markdown content
's3_content_html_path'  # S3 path to HTML content
's3_aggregated_content_md_path'  # S3 path to aggregated content
# ... other metadata fields as needed
```

**Field Extraction Logic**:
```python
def _extract_metadata_fields(self, entry: Dict) -> Dict:
    """Extract fields from extracted_metadata to top level."""
    if 'extracted_metadata' not in entry:
        return entry

    meta = entry['extracted_metadata']
    entry_copy = entry.copy()

    # Extract key metadata fields to top level
    entry_copy['feed_id'] = meta.get('feed_id')
    entry_copy['topic_id'] = meta.get('topic_id')
    entry_copy['content_status'] = meta.get('status')
    entry_copy['content_timestamp'] = meta.get('timestamp')
    entry_copy['s3_content_md_path'] = meta.get('s3_content_md_path')
    entry_copy['s3_content_html_path'] = meta.get('s3_content_html_path')
    entry_copy['s3_aggregated_content_md_path'] = meta.get('s3_aggregated_content_md_path')

    # Keep full metadata as well (for advanced users)
    entry_copy['extracted_metadata_full'] = meta

    return entry_copy
```

**S3 Content Fetching Logic**:
```python
def _fetch_contents_from_s3(
    self,
    df: pd.DataFrame,
    s3_client: S3ContentClient
) -> pd.DataFrame:
    """Fetch content from S3 for all entries in DataFrame."""
    if 's3_content_md_path' not in df.columns:
        logger.warning("No s3_content_md_path column found")
        df['content_markdown'] = None
        return df

    # Get all S3 paths (filter out NaN)
    s3_paths = df['s3_content_md_path'].dropna().unique().tolist()

    if not s3_paths:
        logger.warning("No S3 paths found to fetch")
        df['content_markdown'] = None
        return df

    logger.info(f"Fetching content for {len(s3_paths)} unique S3 paths...")

    # Batch fetch from S3 (parallel requests, no caching in SDK)
    content_map = s3_client.fetch_content_batch(s3_paths)

    # Map content back to DataFrame
    df['content_markdown'] = df['s3_content_md_path'].map(content_map)

    # Log fetch stats
    fetched_count = df['content_markdown'].notna().sum()
    logger.info(f"Successfully fetched {fetched_count}/{len(df)} contents")

    return df
```

**Updated Method Signature Example**:
```python
def get_entries_df(
    self,
    feed_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    fetch_all: bool = True,
    fetch_content: bool = False,
    s3_client: Optional[S3ContentClient] = None,
) -> pd.DataFrame:
    """
    Fetch entries and return as DataFrame with automatic pagination.

    New in v0.2.0: Content is no longer returned directly by the API.
    Use fetch_content=True to automatically fetch content from S3.

    Args:
        ... (existing args)
        fetch_content: If True, fetch content from S3 (requires S3 credentials)
        s3_client: Optional S3ContentClient instance. If None and fetch_content=True,
                   creates client from environment variables.

    Returns:
        pd.DataFrame with columns:
        - id, title, link, published_at, created_at, is_active (existing)
        - content_markdown (fetched from S3 if fetch_content=True, else None)
        - feed_id, topic_id (from extracted_metadata)
        - content_status, content_timestamp (from extracted_metadata)
        - s3_content_md_path, s3_content_html_path, etc.

    Example:
        # Without content (fast)
        >>> dm = create_data_manager()
        >>> entries = dm.get_entries_df()
        >>> print(entries[['title', 'feed_id', 'topic_id']])

        # With content (fetches from S3)
        >>> entries = dm.get_entries_df(fetch_content=True)
        >>> print(entries[['title', 'content_markdown']])
    """
```

**Hierarchical View Updates**:
- **Major Improvement**: Use `feed_id` and `topic_id` from `extracted_metadata` instead of manual injection
- This eliminates the need to manually add feed/topic metadata in loops
- Entries now naturally have their parent IDs

---

### 3.4 Module: `query_engine.py`

**Changes**: Moderate - Pass through S3 parameters and update content handling.

**New Parameters**:
```python
class EntryQueryEngine:
    def __init__(
        self,
        data_manager: FeedsDataManager,
        fetch_content: bool = False,  # NEW
        s3_client: Optional[S3ContentClient] = None,  # NEW
    ):
        self.data_manager = data_manager
        self.fetch_content = fetch_content
        self.s3_client = s3_client
        # ... rest of init
```

**Updated `_ensure_data_loaded`**:
```python
def _ensure_data_loaded(self):
    """Ensure data is loaded before applying filters."""
    if not self._initial_data_loaded:
        logger.info("Loading hierarchical data for query engine...")
        self._results = self.data_manager.get_hierarchical_view(
            include_entries=True,
            fetch_content=self.fetch_content,  # NEW
            s3_client=self.s3_client,  # NEW
        )
        self._initial_data_loaded = True
        logger.info(f"Loaded {len(self._results)} entries for querying")
```

**New Method: Fetch Content on Demand**:
```python
def fetch_content(self, s3_client: Optional[S3ContentClient] = None) -> 'EntryQueryEngine':
    """
    Fetch content from S3 for current filtered results.

    This allows users to filter first (narrow down results), then fetch
    content only for matching entries (performance optimization).

    Args:
        s3_client: Optional S3ContentClient. If None, creates from env.

    Returns:
        Self for method chaining

    Example:
        >>> qe = create_query_engine()
        >>> results = qe.filter_by_topic(topic_name="Banking") \\
        ...     .filter_by_date(start_date=datetime(2024, 1, 1)) \\
        ...     .fetch_content() \\  # Only fetch content for filtered results
        ...     .to_dataframe()
    """
    self._ensure_data_loaded()

    if s3_client is None:
        s3_client = get_s3_client()
        if s3_client is None:
            logger.error("Cannot fetch content: S3 credentials not configured")
            return self

    logger.info(f"Fetching content for {len(self._results)} filtered entries...")
    self._results = self.data_manager._fetch_contents_from_s3(
        self._results,
        s3_client
    )

    return self
```

**Updated Factory Function**:
```python
def create_query_engine(
    fetch_content: bool = False,
    s3_client: Optional[S3ContentClient] = None
) -> EntryQueryEngine:
    """
    Factory function to create query engine.

    Args:
        fetch_content: If True, automatically fetch content from S3 for all queries
        s3_client: Optional S3ContentClient instance

    Example:
        # Without content (fast)
        >>> qe = create_query_engine()

        # With content (fetches from S3)
        >>> qe = create_query_engine(fetch_content=True)

        # Fetch content on demand (recommended)
        >>> qe = create_query_engine()
        >>> results = qe.filter_by_topic(...).fetch_content().to_dataframe()
    """
    data_manager = create_data_manager()
    return EntryQueryEngine(data_manager, fetch_content, s3_client)
```

---

### 3.5 Module: `__init__.py`

**Changes**: Export new S3 client classes and update version.

```python
# Existing exports
from carver_feeds.carver_api import (
    CarverFeedsAPIClient,
    get_client,
    CarverAPIError,
    AuthenticationError,
    RateLimitError,
)
from carver_feeds.data_manager import (
    FeedsDataManager,
    create_data_manager,
)
from carver_feeds.query_engine import (
    EntryQueryEngine,
    create_query_engine,
)

# NEW: S3 client exports
from carver_feeds.s3_client import (
    S3ContentClient,
    get_s3_client,
    S3Error,  # New exception type
)

__all__ = [
    # API client
    "CarverFeedsAPIClient",
    "get_client",
    "CarverAPIError",
    "AuthenticationError",
    "RateLimitError",
    # Data manager
    "FeedsDataManager",
    "create_data_manager",
    # Query engine
    "EntryQueryEngine",
    "create_query_engine",
    # S3 client (NEW)
    "S3ContentClient",
    "get_s3_client",
    "S3Error",
]
```

---

## 4. Dependencies

### 4.1 New Dependencies

**Required Dependencies** (add to `pyproject.toml`):
```toml
dependencies = [
    # ... existing dependencies
    "boto3>=1.34.0,<2.0.0",  # NEW: S3 client
]
```

**Why boto3 is required (not optional)**:
- The API no longer returns `content_markdown`
- Users MUST use S3 to get content
- Making it optional would break the core functionality
- Better to require it and provide graceful degradation when credentials missing

### 4.2 Version Bump

Using `bumpversion`:
```bash
bumpversion minor  # 0.1.2 → 0.2.0
```

This is a **minor version bump** (not major) because:
- Backward compatibility maintained (existing code won't break)
- New features added (S3 content fetching)
- API changes are additive (new parameters with defaults)

---

## 5. Backward Compatibility Strategy

### 5.1 Breaking Changes

**None** - This is a backward-compatible update.

### 5.2 Deprecated Behavior

**Deprecated** (but still supported):
- Expecting `content_markdown` to be populated without `fetch_content=True`

**Warning Message**:
```python
if 'content_markdown' in df.columns and df['content_markdown'].isna().all():
    logger.warning(
        "Content is no longer returned directly by the API. "
        "Use fetch_content=True to fetch content from S3. "
        "See migration guide: https://github.com/carveragents/carver-feeds-sdk#migration-v02"
    )
```

### 5.3 Migration Path for Users

**Scenario 1: Users who don't need content**
- **No changes needed** - code continues to work
- `content_markdown` column exists but is `None` (instead of actual content)

**Scenario 2: Users who need content**
- **Add S3 credentials** to `.env`:
  ```bash
  AWS_ACCESS_KEY_ID=...
  AWS_SECRET_ACCESS_KEY=...
  ```
- **Update code** to use `fetch_content=True`:
  ```python
  # Before
  entries = dm.get_entries_df()

  # After
  entries = dm.get_entries_df(fetch_content=True)
  ```

**Scenario 3: Advanced users (performance-conscious)**
- Use lazy content fetching:
  ```python
  # Filter first, fetch content only for matches
  qe = create_query_engine()
  results = qe \
      .filter_by_topic(topic_name="Banking") \
      .filter_by_date(start_date=datetime(2024, 1, 1)) \
      .fetch_content() \
      .to_dataframe()
  ```

---

## 6. Performance Optimization

### 6.1 Lazy Loading Strategy

**Default Behavior**: Don't fetch content unless explicitly requested
- Most users don't need full content for all entries
- Fetching content for 10,000+ entries is expensive (time + bandwidth)
- Let users fetch content only for filtered results

**Recommended Pattern**:
```python
# BAD: Fetch content for all entries, then filter
qe = create_query_engine(fetch_content=True)
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# GOOD: Filter first, then fetch content only for matches
qe = create_query_engine()
results = qe.filter_by_topic(topic_name="Banking") \
    .fetch_content() \
    .to_dataframe()
```

### 6.2 Caching Strategy

**No Built-In Caching**:
- The SDK does not implement caching for S3 content
- Users can implement their own caching layer if needed
- This keeps the SDK simple and lets users choose their caching strategy
- Examples: file-based cache, Redis, in-memory dict, etc.

**Why No Caching**:
- Different use cases need different caching strategies
- Memory constraints vary by environment
- Users may want persistent cache across sessions
- Simple SDK is easier to maintain and debug

### 6.3 Batch Fetching

**Parallel S3 Requests**:
- Use `ThreadPoolExecutor` for parallel S3 fetches
- Default: 10 concurrent requests (configurable)
- Significant speedup for large result sets

**Implementation**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_content_batch(
    self,
    s3_paths: List[str],
    max_workers: int = 10
) -> Dict[str, Optional[str]]:
    """Fetch multiple contents in parallel."""
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(self.fetch_content, path): path
            for path in s3_paths
        }

        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                results[path] = future.result()
            except Exception as e:
                logger.warning(f"Failed to fetch {path}: {e}")
                results[path] = None

    return results
```

### 6.4 Performance Metrics

**Estimated Fetch Times** (based on typical S3 latency, without caching):
- Single entry: ~100-200ms
- 100 entries (parallel): ~1-2s
- 1000 entries (parallel): ~10-20s
- 10,000 entries: ~100-200s (not recommended without filtering)

**Optimization Tips** (for documentation):
1. Filter first, fetch content later (minimize entries to fetch)
2. Only fetch content when needed for analysis
3. Use batch operations for large result sets (parallel fetching)
4. Implement your own caching if you need to query the same content repeatedly
5. Consider saving fetched content to disk for repeated analysis

---

## 7. Error Handling

### 7.1 S3 Credential Errors

**Scenario**: Missing AWS profile configuration

**Behavior**:
```python
# If fetch_content=True but no profile configured
dm = create_data_manager()
entries = dm.get_entries_df(fetch_content=True)

# Log warning
logger.warning(
    "AWS profile not configured. Content will not be fetched. "
    "Set AWS_PROFILE_NAME in .env and configure ~/.aws/credentials with the profile. "
    "See documentation: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html"
)

# Return DataFrame with content_markdown=None
```

**Scenario**: Invalid profile name

**Behavior**:
```python
# If profile doesn't exist in ~/.aws/credentials
logger.error(
    f"AWS profile '{profile_name}' not found in ~/.aws/credentials. "
    "Available profiles: [default, production, staging]. "
    "Configure the profile or update AWS_PROFILE_NAME."
)

# Return DataFrame with content_markdown=None
```

### 7.2 S3 Fetch Errors

**Scenario**: S3 path invalid or object not found

**Behavior**:
- Log warning for each failed fetch
- Set `content_markdown` to `None` for that entry
- Continue fetching other entries (don't fail entire operation)

**Error Types**:
```python
class S3Error(CarverAPIError):
    """Base exception for S3 operations."""
    pass

class S3CredentialsError(S3Error):
    """Missing or invalid S3 credentials."""
    pass

class S3FetchError(S3Error):
    """Failed to fetch content from S3."""
    pass
```

### 7.3 Retry Logic

**Transient Errors**: Retry with exponential backoff
- ConnectionError
- ReadTimeout
- 500/503 from S3

**Permanent Errors**: Don't retry
- NoSuchKey (404)
- AccessDenied (403)
- Invalid credentials

**Retry Configuration**:
```python
class S3ContentClient:
    def __init__(
        self,
        profile_name: Optional[str] = None,
        region_name: Optional[str] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0
    ):
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**New Test Files**:
- `tests/test_s3_client.py` - S3 client functionality
- `tests/test_metadata_extraction.py` - Metadata field extraction

**Updated Test Files**:
- `tests/test_data_manager.py` - Add S3 content fetching tests
- `tests/test_query_engine.py` - Add `fetch_content()` method tests

**Mocking Strategy**:
```python
# Mock boto3 S3 client
@pytest.fixture
def mock_s3_client(mocker):
    mock_client = mocker.Mock()
    mock_client.get_object.return_value = {
        'Body': io.BytesIO(b'# Test Content\n\nThis is test content.')
    }
    return mock_client

# Mock S3ContentClient
@pytest.fixture
def mock_s3_content_client(mocker, mock_s3_client):
    mocker.patch('boto3.client', return_value=mock_s3_client)
    return S3ContentClient(
        access_key_id='test_key',
        secret_access_key='test_secret'
    )
```

**Test Cases**:
1. **S3 path parsing**: Valid/invalid paths
2. **Content fetching**: Success/failure scenarios
3. **Profile authentication**: Valid/invalid profile names
4. **Batch fetching**: Parallel requests, error handling
5. **Metadata extraction**: Field mapping, missing fields
6. **Backward compatibility**: `fetch_content=False` behavior
7. **Error handling**: Missing profile, invalid profile, fetch failures

### 8.2 Integration Tests

**Test with Real S3** (optional, requires credentials):
```python
@pytest.mark.skipif(
    not os.getenv('AWS_ACCESS_KEY_ID'),
    reason="S3 credentials not configured"
)
def test_real_s3_fetch():
    client = get_s3_client()
    content = client.fetch_content('s3://...')
    assert content is not None
```

### 8.3 Performance Tests

**Benchmark Tests**:
- Fetch 100 entries in parallel
- Batch fetch vs sequential fetch
- Network latency impact on fetch times

---

## 9. Documentation Updates

### 9.1 README.md

**Add Sections**:
1. **S3 Configuration** (in Setup section)
   ```markdown
   ## Setup

   ### 1. API Credentials
   ...

   ### 2. AWS Profile Configuration (for content fetching)

   To fetch entry content, you need to configure an AWS profile:

   **Step 1**: Create/update `~/.aws/credentials`:
   ```ini
   [carver-prod]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

   **Step 2**: Add to your `.env`:
   ```bash
   AWS_PROFILE_NAME=carver-prod
   AWS_REGION=us-east-1  # Optional
   ```

   Content is no longer returned directly by the API (as of v0.2.0).
   Use `fetch_content=True` to automatically fetch from S3.

   **Why AWS Profiles?**
   - More secure (credentials not in .env)
   - Follows AWS best practices
   - Supports role assumption and MFA
   - Easier credential rotation
   ```

2. **Migration Guide** (new section)
   ```markdown
   ## Migration Guide

   ### Upgrading from v0.1.x to v0.2.0

   #### Breaking Changes: None

   #### Important Changes:
   - Content is no longer returned directly by the API
   - New `extracted_metadata` field with S3 paths and metadata
   - Add S3 credentials to fetch content

   #### Migration Steps:

   1. Configure AWS profile in `~/.aws/credentials`:
      ```ini
      [carver-prod]
      aws_access_key_id = YOUR_ACCESS_KEY
      aws_secret_access_key = YOUR_SECRET_KEY
      ```

   2. Add profile name to `.env`:
      ```bash
      AWS_PROFILE_NAME=carver-prod
      ```

   3. Update code to fetch content:
      ```python
      # Before (v0.1.x)
      entries = dm.get_entries_df()
      content = entries['content_markdown']

      # After (v0.2.0)
      entries = dm.get_entries_df(fetch_content=True)
      content = entries['content_markdown']
      ```

   4. For better performance, use lazy loading:
      ```python
      qe = create_query_engine()
      results = qe.filter_by_topic(...).fetch_content().to_dataframe()
      ```
   ```

3. **Update Usage Examples**
   - Add `fetch_content=True` to examples that use content
   - Add note about performance implications

### 9.2 API Reference (docs/api-reference.md)

**Update Sections**:
1. **CarverFeedsAPIClient** - Mention `extracted_metadata` in responses
2. **FeedsDataManager** - Document new parameters and columns
3. **EntryQueryEngine** - Document `fetch_content()` method
4. **S3ContentClient** - Add new section with full API reference

**Example Entry**:
```markdown
### S3ContentClient

Client for fetching entry content from S3.

#### Constructor

```python
S3ContentClient(
    profile_name: Optional[str] = None,
    region_name: Optional[str] = None,
    max_retries: int = 3,
    initial_retry_delay: float = 1.0
)
```

**Parameters:**
- `profile_name`: AWS profile name from ~/.aws/credentials (reads from AWS_PROFILE_NAME env if None)
- `region_name`: AWS region (reads from AWS_REGION env if None, default: us-east-1)
- `max_retries`: Retry attempts for failed fetches (default: 3)
- `initial_retry_delay`: Initial retry delay in seconds (default: 1.0)

#### Methods

##### `fetch_content(s3_path: str) -> Optional[str]`

Fetch content from S3 path.

**Parameters:**
- `s3_path`: S3 URI (e.g., `s3://bucket/key`)

**Returns:**
- Content string, or `None` if fetch fails

##### `fetch_content_batch(s3_paths: List[str], max_workers: int = 10) -> Dict[str, Optional[str]]`

Fetch multiple contents in parallel.

**Parameters:**
- `s3_paths`: List of S3 URIs
- `max_workers`: Max parallel workers (default: 10)

**Returns:**
- Dict mapping S3 path → content (or None if failed)
```

### 9.3 Examples (docs/examples.md)

**Add Examples**:
1. **AWS Profile Setup**
   ```bash
   # Create ~/.aws/credentials
   cat >> ~/.aws/credentials << EOF
   [carver-prod]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   EOF

   # Add to .env
   echo "AWS_PROFILE_NAME=carver-prod" >> .env
   ```

2. **Basic content fetching**
   ```python
   from carver_feeds import create_data_manager

   dm = create_data_manager()
   entries = dm.get_entries_df(fetch_content=True)
   print(entries[['title', 'content_markdown']])
   ```

3. **Lazy content fetching (recommended)**
   ```python
   from carver_feeds import create_query_engine
   from datetime import datetime

   qe = create_query_engine()
   results = qe \
       .filter_by_topic(topic_name="Banking") \
       .filter_by_date(start_date=datetime(2024, 1, 1)) \
       .fetch_content() \
       .to_dataframe()
   ```

4. **Using metadata fields**
   ```python
   entries = dm.get_entries_df()
   print(entries[['title', 'feed_id', 'topic_id', 'content_status', 'content_timestamp']])
   ```

5. **Custom S3 client with specific profile**
   ```python
   from carver_feeds import create_data_manager, S3ContentClient

   # Use a different AWS profile
   s3 = S3ContentClient(
       profile_name='carver-staging',
       region_name='us-west-2'
   )

   dm = create_data_manager()
   entries = dm.get_entries_df(fetch_content=True, s3_client=s3)
   ```

### 9.4 CLAUDE.md

**Add Learnings**:
```markdown
## API Changes (November 2025)

### extracted_metadata Field

All entry endpoints now return `extracted_metadata` with:
- S3 paths for content (no more direct `content_markdown` in API)
- `feed_id` and `topic_id` (improves hierarchical mapping)
- `timestamp` (when content was last fetched)
- `status` (content extraction status)

### S3 Content Fetching

- Content MUST be fetched from S3 (no longer in API response)
- Uses AWS profile-based authentication (more secure than env keys)
- Use `fetch_content=True` parameter in data manager methods
- Lazy loading recommended: filter first, fetch content for matches only
- Batch fetching with parallel requests for performance
- No built-in caching (users can implement their own if needed)

### Hierarchical Mapping Improvements

- `feed_id` and `topic_id` now in `extracted_metadata` (previously missing)
- Eliminates need for manual metadata injection in loops
- Simplifies hierarchical view construction
```

---

## 10. Migration Guide for SDK Users

### 10.1 For Users Who Don't Use Content

**No changes needed** - code continues to work as-is.

**Note**: `content_markdown` column will be `None` (instead of actual content).

### 10.2 For Users Who Use Content

**Step 1**: Configure AWS profile in `~/.aws/credentials`:
```ini
[carver-prod]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

**Step 2**: Add profile name to `.env`:
```bash
AWS_PROFILE_NAME=carver-prod
```

**Step 3**: Update code to fetch content:
```python
# Before (v0.1.x)
dm = create_data_manager()
entries = dm.get_entries_df()
content = entries['content_markdown']

# After (v0.2.0)
dm = create_data_manager()
entries = dm.get_entries_df(fetch_content=True)
content = entries['content_markdown']
```

**Step 4** (Recommended): Use lazy loading for better performance:
```python
# Filter first, then fetch content
qe = create_query_engine()
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .fetch_content() \
    .to_dataframe()

# Now results has content only for filtered entries
```

### 10.3 For Advanced Users

**Custom S3 Configuration**:
```python
from carver_feeds import S3ContentClient, create_data_manager

# Use a specific AWS profile and region
s3 = S3ContentClient(
    profile_name='carver-staging',
    region_name='us-west-2'
)

dm = create_data_manager()
entries = dm.get_entries_df(fetch_content=True, s3_client=s3)
```

**Implementing Your Own Cache**:
```python
from functools import lru_cache

class CachedS3Client:
    def __init__(self, s3_client):
        self.s3_client = s3_client

    @lru_cache(maxsize=1000)
    def fetch_content(self, s3_path):
        return self.s3_client.fetch_content(s3_path)

# Use the cached client
s3 = S3ContentClient(profile_name='carver-prod')
cached_s3 = CachedS3Client(s3)
```

---

## 11. Release Checklist

### 11.1 Pre-Release

- [ ] Implement `s3_client.py` module
- [ ] Update `data_manager.py` with S3 fetching
- [ ] Update `query_engine.py` with `fetch_content()` method
- [ ] Update `__init__.py` exports
- [ ] Add boto3 dependency to `pyproject.toml`
- [ ] Write unit tests (target: >90% coverage)
- [ ] Update README.md with S3 configuration
- [ ] Update API reference documentation
- [ ] Update examples
- [ ] Update CLAUDE.md with learnings
- [ ] Write migration guide
- [ ] Run full test suite locally
- [ ] Run type checking with mypy
- [ ] Run code formatting with black
- [ ] Run linting with ruff

### 11.2 Version Bump

```bash
# Bump version
bumpversion minor  # 0.1.2 → 0.2.0

# Verify version updated in:
# - pyproject.toml
# - src/carver_feeds/__version__.py
```

### 11.3 Documentation

- [ ] Update CHANGELOG.md with v0.2.0 changes
- [ ] Review all docstrings for accuracy
- [ ] Test all code examples in documentation

### 11.4 Testing

- [ ] Run pytest with coverage: `pytest --cov=carver_feeds --cov-report=term-missing`
- [ ] Test with real API and S3 (integration test)
- [ ] Test backward compatibility (without fetch_content)
- [ ] Test new features (with fetch_content)
- [ ] Test error handling (missing credentials, failed fetches)

### 11.5 Build and Publish

```bash
# Clean old builds
rm -rf dist build *.egg-info

# Build distributions
python -m build

# Test installation in clean environment
python -m venv test_env
source test_env/bin/activate
pip install dist/carver_feeds_sdk-0.2.0-py3-none-any.whl
python -c "from carver_feeds import S3ContentClient; print('Success')"
deactivate
rm -rf test_env

# Publish to PyPI
python -m twine upload dist/*
```

### 11.6 Post-Release

- [ ] Tag release in Git: `git tag v0.2.0 && git push --tags`
- [ ] Create GitHub release with changelog
- [ ] Update GitHub README with new examples
- [ ] Notify users via changelog/announcement
- [ ] Monitor for issues in first week

---

## 12. Future Enhancements (v0.3.0)

### 12.1 Async S3 Fetching

**Motivation**: Further improve performance for large datasets

**Implementation**: Add async version of S3 client
```python
from carver_feeds import AsyncS3ContentClient

async def fetch_many():
    s3 = AsyncS3ContentClient()
    contents = await s3.fetch_content_batch_async(s3_paths)
```

### 12.2 Content Version Tracking

**Motivation**: Track when content changes over time

**Implementation**: Use `timestamp` field to detect content updates
```python
# Detect entries with recently updated content
recent_updates = entries[entries['content_timestamp'] > datetime(2024, 11, 1)]
```

### 12.3 Aggregated Content Support

**Motivation**: Some entries have aggregated content (multiple sources)

**Implementation**: Add parameter to choose content source
```python
entries = dm.get_entries_df(
    fetch_content=True,
    content_source='aggregated'  # vs 'regular' (default)
)
```

### 12.4 HTML Content Support

**Motivation**: Some users may prefer HTML over markdown

**Implementation**: Add parameter to fetch HTML instead
```python
entries = dm.get_entries_df(
    fetch_content=True,
    content_format='html'  # vs 'markdown' (default)
)
# Populates 'content_html' column instead of 'content_markdown'
```

### 12.5 Caching Examples and Patterns

**Motivation**: Provide reference implementations for common caching strategies

**Implementation**: Add example code for different caching approaches
```python
# Example 1: In-memory LRU cache wrapper
from functools import lru_cache

class LRUCachedS3Client:
    def __init__(self, s3_client, maxsize=1000):
        self.s3_client = s3_client
        self._fetch = lru_cache(maxsize=maxsize)(self._fetch_impl)

    def _fetch_impl(self, s3_path):
        return self.s3_client.fetch_content(s3_path)

    def fetch_content(self, s3_path):
        return self._fetch(s3_path)

# Example 2: Disk-based cache
import diskcache
cache = diskcache.Cache('./s3_cache')

# Example 3: Redis cache
import redis
r = redis.Redis(host='localhost', port=6379)
```

---

## 13. Risk Assessment

### 13.1 High Risk

**None identified** - Changes are additive and backward compatible.

### 13.2 Medium Risk

1. **S3 Fetch Performance**
   - **Risk**: Slow S3 fetches impact user experience
   - **Mitigation**: Lazy loading, caching, batch fetching, documentation on best practices

2. **S3 Credentials Management**
   - **Risk**: Users confused about S3 setup
   - **Mitigation**: Clear documentation, helpful error messages, automatic env loading

3. **Breaking User Expectations**
   - **Risk**: Users expect content to "just work" without S3 setup
   - **Mitigation**: Clear migration guide, warning messages when content is None

### 13.3 Low Risk

1. **boto3 Dependency Size**
   - **Risk**: Large dependency increases package size
   - **Mitigation**: Acceptable trade-off (boto3 is industry standard)

2. **S3 Costs**
   - **Risk**: S3 request costs for large queries
   - **Mitigation**: User's responsibility, caching helps reduce requests

---

## 14. Success Metrics

### 14.1 Technical Metrics

- [ ] Test coverage >90% for new code
- [ ] No breaking changes for existing users
- [ ] S3 fetch time <200ms per entry (single fetch)
- [ ] Batch fetch performance: <2s for 100 entries (parallel)

### 14.2 User Metrics

- [ ] Migration guide clear and concise (<5 steps)
- [ ] <5% increase in support questions
- [ ] Positive feedback on performance improvements

### 14.3 Code Quality Metrics

- [ ] All type hints pass mypy checks
- [ ] All code passes black formatting
- [ ] All code passes ruff linting
- [ ] Documentation complete for all public APIs

---

## 15. Summary

This implementation plan provides a comprehensive, backward-compatible approach to integrating S3-based content fetching into the Carver Feeds SDK. The key design decisions are:

1. **Backward Compatible**: Existing code continues to work without changes
2. **Opt-In**: Users opt into S3 fetching via `fetch_content=True` parameter
3. **Performance-First**: Lazy loading and caching minimize S3 requests
4. **Graceful Degradation**: Missing credentials or failed fetches don't crash the SDK
5. **Clear Migration**: Documentation and examples guide users through the transition

The plan is designed for a single release (v0.2.0) with clear rollout phases, comprehensive testing, and detailed documentation. Future enhancements (v0.3.0+) can build on this foundation to add async support, content versioning, and advanced caching strategies.

**Estimated Implementation Time**: 2-3 days for a single developer
- Day 1: Implement s3_client.py + basic integration
- Day 2: Update data_manager.py and query_engine.py
- Day 3: Testing, documentation, and polish

**Recommended Next Steps**:
1. Review and approve this plan
2. Begin implementation with s3_client.py module
3. Test integration with real S3 data
4. Update documentation in parallel
5. Release v0.2.0 with migration guide
