# Carver Feeds SDK

[![PyPI version](https://badge.fury.io/py/carver-feeds-sdk.svg)](https://badge.fury.io/py/carver-feeds-sdk)
[![Python Support](https://img.shields.io/pypi/pyversions/carver-feeds-sdk.svg)](https://pypi.org/project/carver-feeds-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Python SDK for the Carver Feeds API, enabling seamless access to regulatory feed data with advanced querying, filtering, and data analysis capabilities.

## Features

- **Comprehensive API Client**: Full support for all Carver Feeds API endpoints with authentication, retry logic, and error handling
- **DataFrame Integration**: Convert API responses to pandas DataFrames for easy data analysis
- **Advanced Query Engine**: Fluent API with method chaining for building complex queries
- **Optimized Performance**: Smart endpoint selection and caching for efficient data access
- **Type Safety**: Full type hints throughout the codebase for better IDE support
- **Production Ready**: Comprehensive error handling, logging, and extensive documentation

## Installation

```bash
pip install carver-feeds-sdk
```

## Quick Start

### 1. Configuration

Create a `.env` file in your project directory:

```bash
CARVER_API_KEY=your_api_key_here
CARVER_BASE_URL=https://app.carveragents.ai  # optional
```

### 2. Basic Usage

```python
from carver_feeds import get_client

# Initialize client from environment variables
client = get_client()

# Fetch topics
topics = client.list_topics()
print(f"Found {len(topics)} topics")

# Fetch feeds
feeds = client.list_feeds()
print(f"Found {len(feeds)} feeds")
```

### 3. Using DataFrames

```python
from carver_feeds import create_data_manager

# Create data manager
dm = create_data_manager()

# Get topics as DataFrame
topics_df = dm.get_topics_df()
print(topics_df[['id', 'name', 'is_active']].head())

# Get entries for a specific feed
entries_df = dm.get_entries_df(feed_id="feed-123")
print(f"Found {len(entries_df)} entries")
```

### 4. Advanced Querying

```python
from carver_feeds import create_query_engine
from datetime import datetime

# Create query engine
qe = create_query_engine()

# Build complex query with method chaining
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries("regulation") \
    .to_dataframe()

print(f"Found {len(results)} matching entries")

# Export results
qe.to_csv("results.csv")
qe.to_json("results.json")
```

## Core Components

### API Client (`CarverFeedsAPIClient`)

Low-level API client with comprehensive error handling:

- X-API-Key authentication
- Automatic pagination
- Exponential backoff retry logic
- Support for all API endpoints

### Data Manager (`FeedsDataManager`)

Converts API responses to pandas DataFrames:

- JSON to DataFrame conversion
- Hierarchical data views (topic → feed → entry)
- Schema validation and missing field handling
- Optimized endpoint selection

### Query Engine (`EntryQueryEngine`)

High-level query interface with fluent API:

- Method chaining for complex queries
- Filter by topic, feed, date range, and status
- Keyword search across multiple fields
- Multiple export formats (DataFrame, CSV, JSON, dict)
- Lazy loading for better performance

## Documentation

- **[Complete Documentation](docs/README.md)**: Full SDK documentation
- **[API Reference](docs/api-reference.md)**: Detailed API endpoint and module reference
- **[Usage Examples](docs/examples.md)**: 9 comprehensive examples covering common workflows

## Requirements

- Python 3.10 or higher
- pandas >= 2.0.0
- requests >= 2.31.0
- See [pyproject.toml](pyproject.toml) for complete dependency list

## Development

### Install for Development

```bash
# Clone repository
git clone https://github.com/carveragents/carver-feeds-skill.git
cd carver-feeds-skill

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy src/carver_feeds

# Format code
black src/carver_feeds
ruff check src/carver_feeds
```

### Project Structure

```
carver-feeds-skill/
├── src/carver_feeds/        # Main package source
│   ├── __init__.py          # Package exports
│   ├── carver_api.py        # API client
│   ├── data_manager.py      # DataFrame construction
│   ├── query_engine.py      # Query interface
│   └── utils.py             # Utilities
├── tests/                   # Test suite
├── docs/                    # Documentation
├── examples/                # Example scripts
└── pyproject.toml           # Package configuration
```

## Performance Tips

1. **Use specific endpoints**: Filter by topic/feed ID when possible
   ```python
   # Slow: fetch all entries, then filter
   all_entries = dm.get_entries_df()
   filtered = all_entries[all_entries['feed_id'] == 'feed-456']

   # Fast: use optimized endpoint
   filtered = dm.get_entries_df(feed_id='feed-456')
   ```

2. **Reuse query engine**: Data is cached after first load
   ```python
   qe = create_query_engine()
   results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()
   results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
   ```

3. **Leverage lazy loading**: Query engine only fetches when needed
   ```python
   qe = create_query_engine()  # No API call yet
   results = qe.search_entries("regulation")  # API call happens here
   ```

## Error Handling

The SDK provides specific exception types for different error scenarios:

```python
from carver_feeds import get_client, CarverAPIError, AuthenticationError, RateLimitError

try:
    client = get_client()
    topics = client.list_topics()
except AuthenticationError:
    print("Invalid API key. Check your .env file.")
except RateLimitError:
    print("Rate limit exceeded. Please wait before retrying.")
except CarverAPIError as e:
    print(f"API error: {e}")
```

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite and type checking
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or feature requests:

- **Documentation**: [docs/README.md](docs/README.md)
- **API Reference**: [docs/api-reference.md](docs/api-reference.md)
- **Examples**: [docs/examples.md](docs/examples.md)
- **Issues**: [GitHub Issues](https://github.com/carveragents/carver-feeds-skill/issues)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

**Note**: This SDK requires a valid Carver API key. Visit [Carver Agents](https://carveragents.ai) to obtain your API key.
