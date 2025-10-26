# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based API client library for the Carver Feeds platform, which provides regulatory feed data. The project is packaged as a PyPI-installable package (`carver-feeds-sdk`) and can also be used as a Claude skill.

## Environment Setup

```bash
# Install in development mode
pip install -e .

# Or install from PyPI (once published)
pip install carver-feeds-sdk

# Configuration
cp .env.example .env
# Edit .env and add CARVER_API_KEY and CARVER_BASE_URL
```

**Configuration**: Create a `.env` file in your working directory or set environment variables `CARVER_API_KEY` and `CARVER_BASE_URL`. The library will automatically load these when using factory functions.

## Key Architecture Patterns

### 1. Three-Layer Module Design

The codebase follows a clear separation of concerns:

- **`carver_feeds.carver_api`**: Low-level API client
  - Handles authentication (X-API-Key header)
  - Implements retry logic with exponential backoff
  - Manages pagination (limit/offset pattern)
  - 5 endpoints: list_topics(), list_feeds(), list_entries(), get_feed_entries(feed_id), get_topic_entries(topic_id)

- **`carver_feeds.data_manager`**: DataFrame construction layer
  - Converts API JSON responses to pandas DataFrames
  - Builds hierarchical views (topic → feed → entry)
  - Handles schema validation and missing fields
  - **Critical optimization**: Uses endpoint selection to minimize data fetching

- **`carver_feeds.query_engine`**: High-level query interface
  - Fluent API with method chaining
  - Lazy loading (no API calls until needed)
  - **Smart endpoint routing**: Automatically uses optimized endpoints (get_feed_entries, get_topic_entries) when filtering by feed/topic
  - Multiple export formats (DataFrame, CSV, JSON, dict)

### 2. Optimized Data Fetching Strategy

The query engine implements an important optimization pattern:

```python
# BEFORE optimization: Fetch all entries, then filter
qe = create_query_engine()
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()
# Would load ALL entries into memory, then filter

# AFTER optimization: Use topic-specific endpoint
# The query engine detects no data is loaded yet
# Resolves "Banking" to topic_id
# Calls get_topic_entries(topic_id) directly
# Only fetches entries for that topic
```

**When implementing filters**: Check `self._initial_data_loaded` flag. If False, use optimized endpoints before loading all data.

### 3. Hierarchical Data Model

The data model has three levels with specific relationships:

```
Topic (id, name, description, is_active)
  ↓ 1:N
Feed (id, name, url, topic_id, topic_name, is_active)
  ↓ 1:N
Entry (id, title, link, content_markdown, feed_id, published_at, is_active)
```

**Column naming convention in hierarchical views**:
- Prefix with entity name: `topic_*`, `feed_*`, `entry_*`
- Example: `topic_name`, `feed_name`, `entry_title`, `entry_published_at`

**Key implementation detail**: The `/api/v1/feeds/` endpoint returns feed objects with nested topic data like `{"topic": {"id": "...", "name": "..."}}`. The data_manager flattens this to `topic_id` and `topic_name` columns.

### 4. API Endpoint Selection Logic

Understanding which endpoint to use is critical for performance:

| Scenario | Endpoint | Returns feed_id? |
|----------|----------|------------------|
| Get all entries | `/api/v1/feeds/entries/list` | ❌ No |
| Get entries for specific feed | `/api/v1/feeds/{feed_id}/entries` | ❌ No (must add manually) |
| Get entries for specific topic | `/api/v1/feeds/topics/{topic_id}/entries` | ✅ Yes |
| Filter by topic then feed | Use topic endpoint, then filter client-side | ✅ Yes |

**Important**: When using `get_feed_entries()`, you must manually inject `feed_id` into each entry dict, as the API doesn't include it (see data_manager.py:254).

## Common Development Tasks

### Using the Package

```python
# Example 1: List all topics
from carver_feeds import create_data_manager
dm = create_data_manager()
topics = dm.get_topics_df()
print(topics[['id', 'name', 'is_active']].head())

# Example 2: Query entries with filters
from carver_feeds import create_query_engine
from datetime import datetime

qe = create_query_engine()
results = qe \
    .filter_by_topic(topic_name="Ireland") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries("regulation") \
    .to_dataframe()
```

### Testing Considerations

When testing:
1. **Mock API responses**: Use `unittest.mock` to patch `CarverFeedsAPIClient` methods
2. **Test data fixtures**: The API returns lists of dicts with specific schemas (see reference.md)
3. **Date handling**: Always use `pd.to_datetime(..., errors='coerce')` for robust parsing
4. **Timezone awareness**: The date filtering code handles timezone-aware vs naive datetime comparison (query_engine.py:507-516)

## Important Implementation Details

### Search Field Priority
Default search field is `entry_content_markdown` (full article content). Other searchable fields:
- `entry_title`: Entry headline
- `entry_description`: Brief summary
- `entry_link`: Entry URL

### Pagination Pattern
All list endpoints support `limit` and `offset` parameters:
- Default limit: 1000 records per page
- The `_paginate()` method automatically handles multiple pages
- Set `fetch_all=False` for single-page requests (faster for exploration)

### Error Handling Strategy
- **429 (Rate Limit)**: Automatic retry with exponential backoff (max 3 retries)
- **5xx (Server Error)**: Automatic retry with exponential backoff (max 3 retries)
- **401 (Auth Error)**: Immediate failure with helpful message about .env
- **Connection/Timeout**: Immediate failure with network diagnostic message

### Date Field Mapping
The API returns `published_date` but the DataFrame uses `published_at`. The data_manager maps this automatically (data_manager.py:278-280).

## File Organization

```
carver-feeds-skill/
├── src/carver_feeds/               # Package source code
│   ├── __init__.py                 # Public API exports
│   ├── __version__.py              # Version information
│   ├── carver_api.py               # API client
│   ├── data_manager.py             # DataFrame builder
│   ├── query_engine.py             # Query interface
│   └── py.typed                    # Type hints marker
├── docs/                           # Documentation
│   ├── README.md                   # User guide
│   ├── api-reference.md            # API reference
│   └── examples.md                 # Usage examples
├── tests/                          # Test suite
│   ├── conftest.py                 # Pytest fixtures
│   └── test_*.py                   # Test files
├── examples/                       # Example scripts
│   ├── basic_usage.py
│   └── advanced_queries.py
├── .claude/                        # Claude skill configuration
│   └── skills/carver-api-skill/
├── pyproject.toml                  # Package configuration
├── MANIFEST.in                     # Distribution rules
├── CHANGELOG.md                    # Version history
├── .env                            # API credentials (gitignored)
├── .env.example                    # Configuration template
└── README.md                       # PyPI landing page
```

## Working with the Codebase

### Adding New Filter Methods
Follow the pattern in query_engine.py:
1. Accept filter parameters
2. Check if `self._initial_data_loaded` is False
3. If False, try to use optimized endpoint (get_feed_entries or get_topic_entries)
4. If True, filter the already-loaded `self._results` DataFrame
5. Return `self` for method chaining

### Adding New API Endpoints
Follow the pattern in carver_api.py:
1. Define method on `CarverFeedsAPIClient` class
2. Use `_make_request()` for single requests
3. Use `_paginate()` for list endpoints with pagination
4. Include comprehensive docstring with example
5. Add endpoint to data_manager if it returns structured data
6. Update package version in `__version__.py`

### Modifying Schema/Columns
When adding or changing columns:
1. Update `expected_columns` list in relevant data_manager method
2. Add column to hierarchical view if needed (update rename operations)
3. Update documentation in root `README.md` and `docs/api-reference.md` with new fields
4. Handle missing data gracefully (use `fillna()` or `errors='coerce'`)
5. Update package version if breaking changes

## Known Gotchas

1. **Feed endpoint doesn't filter by topic_id**: Despite what docs might suggest, `/api/v1/feeds/` doesn't accept topic_id parameter. Must filter client-side (data_manager.py:176-180).

2. **Entry endpoints don't include feed_id**: When calling `get_feed_entries()`, you must manually add feed_id to each entry dict.

3. **Topic object nesting**: Feeds API returns `topic` as nested object `{id, name}`, must flatten to `topic_id` and `topic_name`.

4. **Environment variables**: Factory functions (`get_client()`, `create_data_manager()`, `create_query_engine()`) load from environment variables by default. Can also pass credentials directly.

5. **Name-based filtering uses partial match**: `filter_by_topic(topic_name="Bank")` matches "Banking", "Bank of America", etc. This is intentional for user convenience.

6. **Multiple name matches**: If multiple topics/feeds match a name, the optimizer fetches entries for ALL of them and concatenates results (query_engine.py:298-315).

## Dependencies

Core dependencies from requirements.txt:
- `requests>=2.31.0` - HTTP client for API calls
- `pandas>=2.0.0` - DataFrame operations
- `numpy>=1.24.0,<2.0.0` - Pinned to 1.x for pyarrow compatibility
- `pyarrow>=12.0.0` - Parquet support
- `python-dotenv>=1.0.0` - Environment variable management
- `tqdm>=4.65.0` - Progress bars for long operations
- `tabulate>=0.9.0` - Pretty table formatting

## Additional Resources

For complete API schemas, endpoint details, and comprehensive examples, see:
- `README.md` - Main SDK documentation with user guide, data model, and quick examples
- `docs/api-reference.md` - Full API reference and schemas
- `docs/examples.md` - 9 detailed usage examples
- `examples/` - Working example scripts
