# Carver Feeds Skill

A Claude skill and a set of python scripts that enables fetching, analyzing, and querying regulatory feed data from the Carver platform.

## Overview

The carver-feeds-skill provides comprehensive capabilities for working with regulatory feed data:

- **Data Fetching**: Retrieve topics, feeds, and entries from the Carver API
- **Hierarchical Views**: Construct pandas DataFrames showing topic → feed → entry relationships
- **Advanced Querying**: Search and filter entries with method chaining and lazy loading
- **Multiple Export Formats**: Export results to DataFrame, CSV, JSON, or dictionary formats
- **Optimized Performance**: Smart endpoint selection and caching for efficient data access

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
# OR just ask Claude to execute a task and it will automatically install the dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API key
# CARVER_API_KEY=your_actual_api_key_here
# CARVER_BASE_API_URL=carver_base_api_url_here
```

**Important**: Obtain your API key from your Carver account settings. Never commit `.env` to version control.

## Usage Examples

### Python scripts

#### Example 1: Get All Topics, Feeds, and Entries

```python
from scripts.data_manager import create_data_manager

dm = create_data_manager()

# Get all topics
topics_df = dm.get_topics_df()
print(f"Total topics: {len(topics_df)}")
print(topics_df[['id', 'name', 'is_active']].head())

# Get all feeds
feeds_df = dm.get_feeds_df()
print(f"\nTotal feeds: {len(feeds_df)}")
print(feeds_df[['id', 'name', 'topic_name', 'is_active']].head())

# Get all entries (warning: this may be slow and fetch a lot of data)
# For production use, always filter by topic_id or feed_id first
entries_df = dm.get_entries_df(fetch_all=True)
print(f"\nTotal entries: {len(entries_df)}")
print(entries_df[['id', 'title', 'published_at']].head())
```

#### Example 2: List Topics, Feeds, and Entries for a Topic

```python
from scripts.data_manager import create_data_manager

dm = create_data_manager()

# Get all topics
topics_df = dm.get_topics_df()
print(f"Available topics: {len(topics_df)}")
print(topics_df[['id', 'name', 'is_active']].head())

# Get feeds for a specific topic
selected_topic_id = topics_df['id'].iloc[0]
selected_topic_name = topics_df['name'].iloc[0]
topic_feeds = dm.get_feeds_df(topic_id=selected_topic_id)
print(f"\nFeeds in topic '{selected_topic_name}' (id {selected_topic_id}): {len(topic_feeds)}")
print(topic_feeds[['id', 'name', 'is_active']].head())

# Get entries for one of the feeds
if len(topic_feeds) > 0:
    selected_feed_id = topic_feeds['id'].iloc[0]
    selected_feed_name = topic_feeds['name'].iloc[0]
    feed_entries = dm.get_entries_df(feed_id=selected_feed_id)
    print(f"\nEntries in feed '{selected_feed_name}' (id {selected_feed_id}): {len(feed_entries)}")
    print(feed_entries[['id', 'title', 'published_at']].head())
```

#### Example 3: Complex Multi-Filter Query

```python
from scripts.query_engine import create_query_engine
from datetime import datetime

qe = create_query_engine()

# Find entries with multiple filters
results = qe \
    .filter_by_topic(topic_name="Ireland") \
    .filter_by_feed(feed_name="news") \
    .filter_by_active(is_active=True) \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries(["regulation", "compliance"], match_all=False) \
    .to_dataframe()

print(f"Found {len(results)} entries matching all criteria")

# Export to CSV
csv_path = qe.to_csv("ireland_news_2024.csv")
print(f"Exported to {csv_path}")
```

### Claude Skill

If using as a Claude skill, place the skill in the `skills` directory of your `.claude` directory. It will automatically install the dependencies and set up the environment when needed.

#### Example 1: Single query

```bash
claude> List all topics available in the Carver platform.
```

#### Example 2: Follow up queries

```bash
claude> Get me all feed names that have the word News in the title from any Ireland related topics
...
...
...
claude> OK, now get me all the entries from this feed
```

**See [SKILL.md](SKILL.md) for complete usage instructions and [examples.md](examples.md) for 9 comprehensive usage examples.**

## Documentation

- **[SKILL.md](SKILL.md)**: Main skill entry point - when to use, core operations, quick examples
- **[reference.md](reference.md)**: Complete API reference - endpoints, schemas, module documentation
- **[examples.md](examples.md)**: Comprehensive usage examples - 9 detailed examples covering common workflows

## Project Structure

```
carver-feeds-skill/
├── SKILL.md                  # Main skill entry point
├── reference.md              # API reference documentation
├── examples.md               # Usage examples
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore rules
└── scripts/
    ├── __init__.py           # Package initialization
    ├── carver_api.py         # API client module
    ├── data_manager.py       # DataFrame construction
    ├── query_engine.py       # Search & filtering
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

We welcome contributions! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
4. **Update documentation** as needed
5. **Submit a pull request** with a clear description

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues or questions:
- Review documentation: [SKILL.md](SKILL.md), [reference.md](reference.md), [examples.md](examples.md)
