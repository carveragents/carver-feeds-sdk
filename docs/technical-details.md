# Technical Details & Developer Guide

This document provides comprehensive technical documentation for developers working on the Carver Feeds SDK.

## Table of Contents

- [Development Setup](#development-setup)
- [Common Commands](#common-commands)
- [Architecture](#architecture)
- [Performance Optimization](#performance-optimization)
- [Testing Strategy](#testing-strategy)
- [Error Handling](#error-handling)
- [Code Style](#code-style)
- [Environment Configuration](#environment-configuration)
- [Package Structure](#package-structure)
- [Publishing Workflow](#publishing-workflow)
- [API Endpoints](#api-endpoints)
- [Common Gotchas](#common-gotchas)
- [Dependencies](#dependencies)

---

## Development Setup

### Prerequisites
- Python 3.10 or higher
- pip and virtualenv

### Initial Setup

```bash
# Create and activate virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"

# Configure API credentials
cp .env.example .env
# Edit .env and add your CARVER_API_KEY
```

---

## Common Commands

### Testing

```bash
# Run full test suite
pytest

# Run with coverage report
pytest --cov=carver_feeds --cov-report=term-missing

# Run specific test file
pytest tests/test_carver_api.py

# Run specific test
pytest tests/test_carver_api.py::test_function_name
```

### Code Quality

```bash
# Format code (line length: 100)
black src/carver_feeds

# Lint with ruff
ruff check src/carver_feeds

# Type check with mypy
mypy src/carver_feeds
```

### Building and Publishing

```bash
# Clean old builds
rm -rf dist build *.egg-info

# Build distributions
python -m build

# Upload to PyPI (requires PYPI_API_TOKEN or .pypirc)
python -m twine upload dist/*
```

### Version Management

**IMPORTANT:** This project uses `bumpversion` to keep version strings synchronized across:
- `pyproject.toml`
- `src/carver_feeds/__version__.py`
- Documentation files

```bash
# Bump version (automatically updates all version references)
bumpversion patch   # 0.1.0 -> 0.1.1
bumpversion minor   # 0.1.0 -> 0.2.0
bumpversion major   # 0.1.0 -> 1.0.0

# After bumping, manually update CHANGELOG.md with release notes
# Then build and publish
```

Configuration is in `.bumpversion.cfg`. **Never manually edit version strings** - always use bumpversion.

---

## Architecture

### Three-Layer Design

The SDK provides three levels of abstraction, each building on the previous:

#### 1. CarverFeedsAPIClient (`carver_api.py`)
- **Purpose**: Low-level HTTP client for Carver API
- **Features**:
  - Authentication (X-API-Key header)
  - Automatic retries with exponential backoff
  - Rate limiting handling
  - Pagination support
- **Returns**: Raw Python dicts from API responses
- **Use when**: You need direct API control or raw responses

#### 2. FeedsDataManager (`data_manager.py`)
- **Purpose**: Convert API responses to pandas DataFrames
- **Features**:
  - DataFrame conversion
  - Hierarchical data views (topic → feed → entry)
  - Content fetching integration
  - Metadata extraction from `extracted_metadata` field
- **Returns**: pandas DataFrames
- **Use when**: You need simple DataFrame operations without complex filtering

#### 3. EntryQueryEngine (`query_engine.py`)
- **Purpose**: High-level fluent query interface
- **Features**:
  - Method chaining for building complex queries
  - Advanced filtering: by topic, feed, date, status, keywords
  - Keyword search with AND/OR logic across multiple fields
  - Multiple export formats (DataFrame, CSV, JSON, dict)
  - Lazy content loading (filter first, fetch content later)
  - Automatic caching
- **Returns**: Query results in multiple formats
- **Use when**: You need complex queries with multiple filters

### Data Model Hierarchy

```
Topic (regulatory body like "SEC")
  └─ Feed (RSS feed)
       └─ Entry (individual article/post)
```

**Key relationships:**
- Each Entry belongs to exactly one Feed (`entry.feed_id`)
- Each Feed belongs to exactly one Topic (`feed.topic_id`)
- Each Entry also has `topic_id` in `extracted_metadata` (denormalized for convenience)
- Hierarchical views denormalize this structure for easier querying

### Factory Pattern

The SDK uses factory functions that automatically load configuration from environment:

```python
from carver_feeds import get_client, create_data_manager, create_query_engine

client = get_client()              # Auto-loads .env
dm = create_data_manager()         # Creates client internally
qe = create_query_engine()         # Creates data_manager internally
```

Users can also instantiate classes directly with explicit config:

```python
from carver_feeds import CarverFeedsAPIClient, FeedsDataManager, S3ContentClient

# Explicit configuration
client = CarverFeedsAPIClient(api_key="your_key")
s3_client = S3ContentClient(profile_name="carver-prod")
dm = FeedsDataManager(api_client=client)
```

### S3 Content Architecture 

**Key components:**
1. **S3ContentClient** (`s3_client.py`): Handles S3 authentication and content fetching
2. **extracted_metadata field**: API responses include S3 paths and metadata
3. **Lazy loading**: Content fetching is opt-in via `fetch_content` parameter
4. **Batch fetching**: Parallel S3 requests for performance

**Authentication methods:**
- **AWS Profile** (recommended): Uses profile from `~/.aws/credentials`
- **Direct credentials**: Pass credentials explicitly (not recommended for production)

---

## Performance Optimization

### Critical Concepts

#### 1. Topic-Specific Endpoints
The query engine uses topic-specific endpoints for optimal performance:

- **Optimized path**: `filter_by_topic()` → uses `/topics/{id}/entries` (fetches entries for that topic only)
- **Unoptimized path**: Fetching all entries requires pagination through large datasets

**Best practice**: Always filter by topic first when possible.

#### 2. Lazy Content Loading
Content is fetched from S3 only when explicitly requested:

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

**Performance impact:**
- Small queries (<100 entries): ~1-2 seconds
- Medium queries (100-1000 entries): ~10-20 seconds
- Large queries (1000+ entries): ~100+ seconds

#### 3. Batch S3 Fetching
The SDK automatically uses parallel requests for S3 content fetching:
- Default: 10 concurrent requests
- Configurable via `max_workers` parameter
- Significant speedup vs sequential fetching

#### 4. Query Engine Caching
Once data is loaded, it's cached in `_results`:
- Use `chain()` to reset and start a new query with cached data
- Avoids redundant API calls for subsequent queries

### Performance Metrics

**API Scale:**
- API uses pagination (100 items per page max)
- Full data loads can take 30-60 seconds
- ~10,000+ total entries across all topics

### Optimization Guidelines

**When adding features that involve entry queries:**
1. Always use `topic_id` to narrow the dataset
2. Document that `topic_id` is required
3. Consider adding lazy loading patterns for large datasets
4. Use batch operations where possible
5. Implement caching strategies for repeated queries

---

## Testing Strategy

### Framework
Tests use `pytest` with `pytest-mock` for mocking API calls. The SDK is designed to be testable without real API access.

### Test Fixtures

Located in `tests/conftest.py`:
- `mock_api_response`: Returns sample API response data
- `mock_client`: Mocked CarverFeedsAPIClient
- `mock_data_manager`: Mocked FeedsDataManager
- `mock_s3_client`: Mocked S3ContentClient

### Testing Best Practices

**When writing tests:**
1. Mock API calls at the `requests` level or `CarverFeedsAPIClient` level
2. Test both success and error paths
3. Verify retry logic for rate limits (429) and server errors (500)
4. Check pagination handling for large datasets
5. Test S3 content fetching (with mocked S3 client)
6. Test graceful degradation when S3 credentials missing

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_carver_api.py       # API client tests
├── test_data_manager.py     # Data manager tests
├── test_query_engine.py     # Query engine tests
├── test_s3_client.py        # S3 client tests (v0.2.0+)
└── integration/             # Integration tests (optional)
```

### Running Tests

```bash
# Full suite
pytest

# With coverage
pytest --cov=carver_feeds --cov-report=term-missing

# Specific module
pytest tests/test_s3_client.py -v

# Integration tests (requires real credentials)
pytest tests/integration/ --real-api
```

---

## Error Handling

### Exception Hierarchy

```python
CarverAPIError (base)
├── AuthenticationError (401/403)
├── RateLimitError (429)
└── S3Error (v0.2.0+)
    ├── S3CredentialsError (missing/invalid credentials)
    └── S3FetchError (failed S3 fetch)
```

### Retry Logic

**Automatic retries** for transient errors:
- Rate limits (429)
- Server errors (500/503)
- Connection errors

**Configuration:**
- Default: 3 retries
- Exponential backoff with 2x factor
- Initial retry delay: 1 second
- Configurable via `max_retries` and `initial_retry_delay` parameters

**No retries** for permanent errors:
- Authentication errors (401/403)
- Not found errors (404)
- Client errors (4xx except 429)

### Error Handling Best Practices

**When adding new API calls:**
1. Use the existing retry wrapper in `_make_request()`
2. Return specific exception types, not generic exceptions
3. Log at appropriate levels:
   - INFO for normal flow
   - WARNING for retries
   - ERROR for failures
4. Provide helpful error messages with actionable guidance

**Graceful degradation:**
- Missing S3 credentials: Log warning, set `content_markdown=None`
- Failed S3 fetch: Log warning, continue with other entries
- API errors: Log error with details, raise specific exception

---

## Code Style

### General Guidelines
- **Line length:** 100 characters (enforced by black and ruff)
- **Python version:** 3.10+ (uses modern type hints)
- **Type hints:** Required on all public APIs
- **Docstrings:** Google style with examples
- **Imports:** Organized by ruff (stdlib → third-party → local)

### Type Hints

```python
from typing import Optional, List, Dict, Any
import pandas as pd

def get_entries(
    self,
    topic_id: Optional[str] = None,
    fetch_content: bool = False
) -> pd.DataFrame:
    """Get entries with optional content fetching."""
    pass
```

### Docstring Format (Google Style)

```python
def fetch_content(self, s3_path: str) -> Optional[str]:
    """
    Fetch content from S3 path.

    Args:
        s3_path: S3 URI in format s3://bucket/key

    Returns:
        Content string, or None if fetch fails

    Raises:
        S3CredentialsError: If AWS credentials not configured
        S3FetchError: If S3 fetch fails

    Example:
        >>> client = S3ContentClient(profile_name='carver-prod')
        >>> content = client.fetch_content('s3://bucket/file.md')
        >>> print(content)
    """
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log levels
logger.info("Normal operation")
logger.warning("Retrying request")
logger.error("Request failed", exc_info=True)
```

---

## Environment Configuration

### Required Variables

```bash
# API Configuration (required)
CARVER_API_KEY=your_api_key_here

# API Base URL (optional, has default)
CARVER_BASE_URL=https://app.carveragents.ai
```

### Loading Configuration

The SDK uses `python-dotenv` to auto-load `.env` files:

```python
# Automatic loading
from carver_feeds import get_client
client = get_client()  # Loads from .env

# Manual configuration
from carver_feeds import CarverFeedsAPIClient
client = CarverFeedsAPIClient(
    api_key="explicit_key",
    base_url="https://custom-url.com"
)
```

---

## Package Structure

```
carver-feeds-sdk/
├── src/carver_feeds/
│   ├── __init__.py          # Public API exports
│   ├── __version__.py       # Version metadata (managed by bumpversion)
│   ├── carver_api.py        # API client with retry/pagination
│   ├── data_manager.py      # DataFrame conversion and hierarchical views
│   ├── query_engine.py      # Fluent query interface
│   ├── s3_client.py         # S3 content fetching (v0.2.0+)
│   └── py.typed             # PEP 561 marker for type checking
│
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_carver_api.py   # API client tests
│   ├── test_data_manager.py # Data manager tests
│   ├── test_query_engine.py # Query engine tests
│   └── test_s3_client.py    # S3 client tests
│
├── docs/
│   ├── README.md            # Documentation index
│   ├── TECHNICAL_DETAILS.md # This file
│   ├── LESSONS.md           # Development lessons learned
│   ├── api-reference.md     # Complete API reference
│   └── s3-content/          # S3 implementation docs
│
├── examples/
│   ├── README.md
│   ├── basic_usage.py
│   ├── advanced_queries.py
│   ├── annotations.py
│   └── user_subscriptions.py
│
├── pyproject.toml           # Package configuration
├── .bumpversion.cfg         # Version management config
├── CHANGELOG.md             # Release history
├── CLAUDE.md                # Claude Code guidance (references this file)
└── README.md                # User-facing documentation
```

---

## Publishing Workflow

### Pre-Release Checklist

1. **Code quality checks:**
   ```bash
   black src/carver_feeds
   ruff check src/carver_feeds
   mypy src/carver_feeds
   ```

2. **Run tests:**
   ```bash
   pytest --cov=carver_feeds --cov-report=term-missing
   ```

3. **Update version:**
   ```bash
   bumpversion patch  # or minor, or major
   ```

4. **Update CHANGELOG.md:**
   - Add release notes for the new version
   - Document breaking changes
   - List new features and bug fixes

### Build and Publish

```bash
# Clean old builds
rm -rf dist build *.egg-info

# Build distributions
python -m build

# Test installation in clean environment (recommended)
python -m venv test_env
source test_env/bin/activate
pip install dist/carver_feeds_sdk-*.whl
python -c "from carver_feeds import create_query_engine; print('Success')"
deactivate
rm -rf test_env

# Publish to PyPI
python -m twine upload dist/*
```

### Post-Release

1. **Tag release in Git:**
   ```bash
   git tag v0.2.0
   git push --tags
   ```

2. **Create GitHub release:**
   - Go to GitHub releases
   - Create new release from tag
   - Copy changelog content
   - Publish release

3. **Update documentation:**
   - Ensure README.md reflects new features
   - Update examples if needed
   - Notify users via changelog

### Package Distribution

- **PyPI package name:** `carver-feeds-sdk`
- **Import name:** `carver_feeds`
- **Supported Python versions:** 3.10+
- **License:** See LICENSE file

---

## API Endpoints

The SDK interacts with these Carver API endpoints:

### Topics

```
GET /api/v1/feeds/topics
```
- List all regulatory topics
- Returns: List of topic objects
- Pagination: Not required (small dataset)

### Entries by Topic

```
GET /api/v1/feeds/topics/{topic_id}/entries
```
- Get entries for a specific topic
- Parameters:
  - `topic_id`: Topic UUID (required)
  - `limit`: Page size (max 100)
  - `offset`: Pagination offset
- Returns: List of entry objects with `extracted_metadata`
- Pagination: Automatic (SDK handles this)

### API Response Structure (v0.2.0+)

**Entry object:**
```json
{
  "id": "entry-uuid",
  "title": "Article Title",
  "link": "https://...",
  "published_date": "2024-11-15T10:00:00Z",
  "created_at": "2024-11-15T10:05:00Z",
  "is_active": true,
  "extracted_metadata": {
    "feed_id": "feed-uuid",
    "topic_id": "topic-uuid",
    "status": "done",
    "timestamp": "2025-11-16T18:21:25.300928+00:00",
    "s3_content_md_path": "s3://bucket/path/content.md",
    "s3_content_html_path": "s3://bucket/path/content.html",
    "s3_aggregated_content_md_path": "s3://bucket/path/aggregate.md"
  }
}
```

### API Server Limits

- **Max page size:** 100 entries per request
- **Rate limiting:** Handled automatically with retries
- **Authentication:** X-API-Key header (required)

---

## Common Gotchas

### 1. API Page Size Limit
**Issue:** The API server enforces a maximum of 100 entries per page.

**Solution:** The SDK automatically handles pagination to fetch all results in batches of 100. You don't need to worry about this unless implementing custom pagination.

### 2. Topic ID Required
**Issue:** All entry-fetching operations require a `topic_id`.

**Why:** This ensures efficient data loading and prevents unnecessary full table scans.

**Solution:** Always use `filter_by_topic()` first, or provide `topic_id` explicitly.

### 3. Query Engine Caching
**Issue:** Once data is loaded, it's cached in `_results`.

**Solution:** Use `chain()` to reset and start a new query with cached data:
```python
qe = create_query_engine()
results1 = qe.filter_by_topic("Banking").to_dataframe()
results2 = qe.chain().filter_by_topic("Healthcare").to_dataframe()
```

### 4. Hierarchical Views Require topic_id
**Issue:** `get_hierarchical_view(include_entries=True)` requires `topic_id`.

**Why:** Prevents loading all entries across all topics (expensive operation).

**Solution:** Always provide `topic_id`:
```python
df = dm.get_hierarchical_view(topic_id="topic-uuid", include_entries=True)
```

### 5. Date Filtering Happens In-Memory
**Issue:** Date filters apply after data is fetched, not at the API level.

**Impact:** All entries are fetched, then filtered.

**Solution:** Combine with topic filters for efficiency:
```python
# Good: Filter by topic first, then by date
qe.filter_by_topic("Banking").filter_by_date(start_date=datetime(2024, 1, 1))
```

### 6. Search is Case-Insensitive by Default
**Issue:** Keyword searches are case-insensitive.

**Solution:** Use `case_sensitive=True` parameter if needed:
```python
qe.search_entries(["Banking"], case_sensitive=True)
```

### 7. Factory Functions Use Environment Config
**Issue:** `get_client()`, `create_data_manager()`, and `create_query_engine()` all load from `.env` automatically.

**Solution:** Either configure `.env` or pass credentials explicitly:
```python
# Option 1: Use .env (recommended)
client = get_client()

# Option 2: Explicit credentials
client = CarverFeedsAPIClient(api_key="your_key")
```

### 8. S3 Content Not Fetched by Default (v0.2.0+)
**Issue:** `content_markdown` is `None` unless explicitly requested.

**Why:** Performance - fetching content from S3 is expensive.

**Solution:** Use `fetch_content=True` or call `.fetch_content()`:
```python
# Option 1: Fetch eagerly
entries = dm.get_entries_df(fetch_content=True)

# Option 2: Fetch lazily (recommended)
entries = qe.filter_by_topic("Banking").fetch_content().to_dataframe()
```

### 9. AWS Profile Required for S3 Content
**Issue:** Missing AWS profile causes S3 fetches to fail silently.

**Solution:** Configure AWS profile:
```bash
# ~/.aws/credentials
[carver-prod]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET

# .env
AWS_PROFILE_NAME=carver-prod
```

### 10. S3 Fetch Performance
**Issue:** Fetching content for many entries is slow.

**Solution:** Filter first, then fetch content only for matches:
```python
# BAD: Fetch all content, then filter
entries = dm.get_entries_df(fetch_content=True)
filtered = entries[entries['title'].str.contains("regulation")]

# GOOD: Filter first, then fetch content
entries = qe.filter_by_topic("Banking") \
    .search_entries(["regulation"]) \
    .fetch_content() \
    .to_dataframe()
```

---

## Dependencies

### Core Dependencies

See `pyproject.toml` for exact versions:

| Package | Purpose | Notes |
|---------|---------|-------|
| `requests` | HTTP client | API communication |
| `pandas` | DataFrame operations | Core data structure |
| `numpy` | Numerical operations | Pandas dependency |
| `pyarrow` | Fast serialization | DataFrame performance |
| `python-dotenv` | Environment loading | Auto-load .env files |
| `tqdm` | Progress bars | Pagination feedback |
| `tabulate` | Pretty printing | Example scripts |
| `boto3` | AWS S3 client | Content fetching (v0.2.0+) |

### Development Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-cov` | Coverage reporting |
| `pytest-mock` | Mocking utilities |
| `black` | Code formatting |
| `ruff` | Linting |
| `mypy` | Type checking |
| `build` | Package building |
| `twine` | PyPI publishing |
| `bumpversion` | Version management |

### Dependency Management

**Installing dependencies:**
```bash
# Production dependencies only
pip install carver-feeds-sdk

# Development dependencies (from source)
pip install -e ".[dev]"
```

**Updating dependencies:**
```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade boto3

# Update all (in development)
pip install --upgrade -e ".[dev]"
```

---

## Additional Resources

- **[API Reference](api-reference.md)** - Complete module and API documentation
- **[Lessons Learned](LESSONS.md)** - Development insights and best practices
- **[Main README](../README.md)** - User-facing documentation
- **[Examples](../examples/)** - Working code examples

---

**Last Updated:** 2026-01-15
**SDK Version:** 0.2.0+
**Status:** Production Ready
