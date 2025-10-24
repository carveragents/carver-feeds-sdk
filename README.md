# Carver Feeds Skill

A Claude skill that enables fetching, analyzing, and querying regulatory feed data from the Carver Horizon platform.

## Overview

The carver-feeds-skill provides comprehensive capabilities for working with regulatory feed data:

- **Data Fetching**: Retrieve topics, feeds, and entries from the Carver API
- **Hierarchical Views**: Construct pandas DataFrames showing topic → feed → entry relationships
- **Advanced Querying**: Search and filter entries with method chaining and lazy loading
- **Multiple Export Formats**: Export results to DataFrame, CSV, JSON, or dictionary formats
- **Optimized Performance**: Smart endpoint selection and caching for efficient data access

**Project Status**: ✅ Production Ready - Phases 1-5 Complete

## Requirements

- Python 3.10 or higher
- Virtual environment (recommended)
- Carver API key

## Pre-requisites

### 1. Installation

```bash
# Navigate to project directory
cd /path/to/carver-feeds-skill

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API key
# CARVER_API_KEY=your_actual_api_key_here
```

**Important**: Obtain your API key from your Carver account settings. Never commit `.env` to version control.

## Usage Examples

### Example 1: Search for Recent Regulatory Updates

```python
from scripts.query_engine import create_query_engine
from datetime import datetime, timedelta

qe = create_query_engine()

# Find banking regulations from the last 30 days
thirty_days_ago = datetime.now() - timedelta(days=30)
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=thirty_days_ago) \
    .search_entries("regulation") \
    .to_dataframe()

print(f"Found {len(results)} recent banking regulations")
print(results[['feed_name', 'entry_title', 'entry_published_at']].head())
```

### Example 2: List Topics and Feeds

```python
from scripts.data_manager import create_data_manager

dm = create_data_manager()

# Get all topics
topics_df = dm.get_topics_df()
print(f"Available topics: {len(topics_df)}")
print(topics_df[['id', 'name', 'is_active']].head())

# Get feeds for a specific topic
banking_feeds = dm.get_feeds_df(topic_id=topics_df['id'].iloc[0])
print(f"Feeds in topic: {len(banking_feeds)}")
```

### Example 3: Complex Multi-Filter Query

```python
from scripts.query_engine import create_query_engine
from datetime import datetime

qe = create_query_engine()

# Find entries with multiple filters
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_feed(feed_name="SEC") \
    .filter_by_active(is_active=True) \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries(["regulation", "compliance"], match_all=True) \
    .to_dataframe()

print(f"Found {len(results)} entries matching all criteria")

# Export to CSV
csv_path = qe.to_csv("sec_regulations_2024.csv")
print(f"Exported to {csv_path}")
```

**See [SKILL.md](SKILL.md) for complete usage instructions and [examples.md](examples.md) for 9 comprehensive usage examples.**

## Documentation

- **[SKILL.md](SKILL.md)**: Main skill entry point - when to use, core operations, quick examples
- **[reference.md](reference.md)**: Complete API reference - endpoints, schemas, module documentation
- **[examples.md](examples.md)**: Comprehensive usage examples - 9 detailed examples covering common workflows
- **[docs/implementation-plan.md](docs/implementation-plan.md)**: Technical implementation specifications
- **[docs/LESSONS.md](docs/LESSONS.md)**: Lessons learned during implementation

## Project Structure

```
carver-feeds-skill/
├── SKILL.md                  # ✅ Main skill entry point
├── reference.md              # ✅ API reference documentation
├── examples.md               # ✅ Usage examples
├── README.md                 # ✅ This file
├── requirements.txt          # Python dependencies
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore rules
└── scripts/
    ├── __init__.py           # Package initialization
    ├── carver_api.py         # ✅ API client module (Phase 1)
    ├── data_manager.py       # ✅ DataFrame construction (Phase 2)
    ├── query_engine.py       # ✅ Search & filtering (Phase 3)
    └── utils.py              # Shared utilities
```

## Key Features

### 1. Comprehensive API Client
- Authentication via X-API-Key header
- Automatic pagination handling (limit/offset pattern)
- Exponential backoff retry logic for rate limits and errors
- Support for 5 API endpoints including optimized topic/feed-specific endpoints

### 2. DataFrame-Based Data Management
- Convert API responses to pandas DataFrames
- Build hierarchical views (topic → feed → entry relationships)
- Flexible schema handling (gracefully handles missing/extra columns)
- Optimized endpoint selection for better performance

### 3. Powerful Query Engine
- Method chaining for building complex queries
- Lazy loading (data fetched only when needed)
- Keyword search with AND/OR logic across multiple fields
- Filter by topic, feed, date range, and active status
- Export to multiple formats (DataFrame, CSV, JSON, dict)

### 4. Production-Ready Implementation
- Comprehensive error handling with helpful messages
- Extensive documentation (SKILL.md, reference.md, examples.md)
- Type hints throughout codebase
- Logging at appropriate levels

## API Endpoints

The skill supports 5 Carver API endpoints:

1. **GET /api/v1/feeds/topics** - List all regulatory topics (~114 topics)
2. **GET /api/v1/feeds/** - List all feeds, optionally filtered by topic (~827 feeds)
3. **GET /api/v1/feeds/entries/list** - List all entries with pagination (~10,000 entries)
4. **GET /api/v1/feeds/{feed_id}/entries** - Get entries for a specific feed (optimized)
5. **GET /api/v1/feeds/topics/{topic_id}/entries** - Get entries for a topic (optimized)

**Performance Tip**: Use endpoints 4 or 5 when filtering by feed/topic for faster queries.

## Module Reference

### scripts.carver_api
API client with authentication, pagination, and retry logic. See [reference.md](reference.md#scriptscarver_api) for details.

### scripts.data_manager
DataFrame construction and hierarchical views. See [reference.md](reference.md#scriptsdata_manager) for details.

### scripts.query_engine
Search and filtering with method chaining. See [reference.md](reference.md#scriptsquery_engine) for details.

## Performance Tips

1. **Filter by topic or feed first**: Use optimized endpoints when possible
   ```python
   # Slow: fetch all, then filter
   all_entries = dm.get_entries_df()
   filtered = all_entries[all_entries['feed_id'] == 'feed-456']

   # Fast: filter at API
   filtered = dm.get_entries_df(feed_id='feed-456')
   ```

2. **Reuse query engine**: Data is cached after first load
   ```python
   qe = create_query_engine()
   results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()
   results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
   ```

3. **Use lazy loading**: Query engine only fetches when needed
   ```python
   qe = create_query_engine()  # No API call yet
   results = qe.search_entries("regulation")  # API call happens here
   ```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate virtual environment: `source .venv/bin/activate` |
| `AuthenticationError` | Check `.env` file exists and `CARVER_API_KEY` is set |
| Empty results | Verify filters are correct, try broadening search |
| Slow queries | Filter by feed/topic first, use optimized endpoints |

**For detailed troubleshooting, see [SKILL.md](SKILL.md#common-issues-and-solutions).**

## Contributing

This project follows a phased implementation approach. See [docs/implementation-plan.md](docs/implementation-plan.md) for technical specifications and [docs/LESSONS.md](docs/LESSONS.md) for implementation insights.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues or questions:
- Review documentation: [SKILL.md](SKILL.md), [reference.md](reference.md), [examples.md](examples.md)
- Check implementation plan: [docs/implementation-plan.md](docs/implementation-plan.md)
- Review lessons learned: [docs/LESSONS.md](docs/LESSONS.md)
