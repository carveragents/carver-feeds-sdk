# Carver Feeds SDK

![PyPI - Version](https://img.shields.io/pypi/v/carver-feeds-sdk)
[![Python Support](https://img.shields.io/pypi/pyversions/carver-feeds-sdk.svg)](https://pypi.org/project/carver-feeds-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python SDK for the Carver Feeds API, enabling seamless access to regulatory feed data with querying, filtering, and data analysis capabilities.

## 🎯 Features

- **Comprehensive API Client**: Full support for public Carver Feeds API endpoints with authentication, retry logic, and error handling
- **DataFrame Integration**: Convert API responses to pandas DataFrames for easy data analysis
- **Advanced Query Engine**: Fluent API with method chaining for building complex queries
- **Optimized Performance**: Smart endpoint selection and caching for efficient data access
- **Type Safety**: Full type hints throughout the codebase for better IDE support
- **Production Ready**: Comprehensive error handling, logging, and extensive documentation

## 🏢 About The SDK

This SDK provides programmatic access to [Carver Feeds API](https://app.carveragents.ai/api-docs/), a real-time regulatory intelligence platform. The SDK helps compliance, risk, and legal teams monitor global regulatory developments, track sanctions and mandates, and receive actionable alerts—transforming regulatory monitoring from reactive dashboard checking into proactive intelligence delivery.

## 👥 Who Is This For?

**Compliance teams, risk analysts, and developers** building monitoring tools, compliance dashboards, or automated alert systems for regulatory risk management.

## 💡 Use Cases

- **Regulatory Intelligence**: Track regulatory changes across multiple jurisdictions in real-time
- **Risk Assessment**: Analyze regulatory trends and emerging requirements affecting your business
- **Automated Alerting**: Build systems that notify stakeholders when relevant regulations are published
- **Research & Analysis**: Query historical regulatory data for trend analysis and reporting

## 📦 Installation

```bash
pip install carver-feeds-sdk
```

## 🚀 Quick Start

### 1. Configuration

Create a `.env` file in your project directory:

```bash
# Required: Carver API Key
CARVER_API_KEY=your_api_key_here
CARVER_BASE_URL=https://app.carveragents.ai  # optional

# Optional: AWS Configuration for S3 Content Fetching (v0.2.0+)
# Content is stored in S3 and requires AWS credentials to fetch.
# Choose one authentication method:

# Method 1: AWS Profile (recommended for local development)
AWS_PROFILE_NAME=your-aws-profile

# Method 2: Direct Credentials (for CI/CD environments)
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key

AWS_REGION=us-east-1  # optional, defaults to us-east-1
```

**Note:** As of v0.2.0, entry content is no longer returned directly by the API. Content is now stored in S3 and must be fetched separately. To access content, configure AWS credentials using one of the methods above. The SDK works without AWS credentials, but `content_markdown` will be `None` for all entries.

### 2. Basic Usage

```python

from dotenv import load_dotenv
from carver_feeds import get_client

load_dotenv()

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
from dotenv import load_dotenv
from carver_feeds import create_data_manager

load_dotenv()

# Create data manager
dm = create_data_manager()

# Get topics as DataFrame
topics_df = dm.get_topics_df()
print(topics_df[['id', 'name', 'is_active']].head())

# Get entries for a specific feed (without content)
entries_df = dm.get_entries_df(feed_id="feed-123")
print(f"Found {len(entries_df)} entries")

# Get entries with content from S3 (requires AWS credentials)
entries_with_content = dm.get_entries_df(feed_id="feed-123", fetch_content=True)
print(f"Fetched content for {len(entries_with_content)} entries")
```

### 4. Advanced Querying

```python
from dotenv import load_dotenv
from carver_feeds import create_query_engine
from datetime import datetime

load_dotenv()

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

## 🏗️ Core Components

### API Client (`CarverFeedsAPIClient`)

Low-level API client with comprehensive error handling:

- X-API-Key authentication
- Automatic pagination (handles ~10,000+ entries)
- Exponential backoff retry logic for rate limits
- Support for all API endpoints

### Data Manager (`FeedsDataManager`)

Converts API responses to pandas DataFrames:

- JSON to DataFrame conversion with schema validation
- Hierarchical data views (topic → feed → entry)
- Smart endpoint selection for performance
- Handles topics, feeds, entries
- S3 content fetching capability (v0.2.0+: content not returned by API by default)

### Query Engine (`EntryQueryEngine`)

High-level query interface with fluent API:

- Method chaining for complex queries
- Filter by topic, feed, date range, and status
- Keyword search with AND/OR logic across multiple fields
- Multiple export formats (DataFrame, CSV, JSON, dict)
- Lazy loading with automatic endpoint optimization

## 📊 Data Model

The SDK works with three main entities in a hierarchical structure:

```
Topic (regulatory bodies like SEC, SEBI, RBI, etc.)
  ↓ 1:N
Feed (RSS feeds for each topic)
  ↓ 1:N
Entry (individual articles/entries)
```

**Key Fields**:
- **Topic**: `id`, `name`, `description`, `is_active`, timestamps
- **Feed**: `id`, `name`, `url`, `topic_id`, `topic_name`, `is_active`, timestamps
- **Entry**: `id`, `title`, `link`, `content_markdown` (requires S3 fetch in v0.2.0+), `description`, `published_at`, `feed_id`, `topic_id`, `content_status`, `s3_content_md_path`, `s3_content_html_path`, `is_active`, timestamps

## ⚡ Advanced Features

### Keyword Search

```python
# Single keyword (case-insensitive by default)
qe.search_entries("regulation").to_dataframe()

# Multiple keywords with OR logic (matches ANY)
qe.search_entries(["regulation", "compliance", "enforcement"], match_all=False)

# Multiple keywords with AND logic (matches ALL)
qe.search_entries(["banking", "regulation"], match_all=True)

# Case-sensitive search
qe.search_entries("SEC", case_sensitive=True)

# Search specific fields
qe.search_entries("fintech", search_fields=['entry_title', 'entry_description'])
```

**Available Search Fields**:
- `entry_content_markdown` (default, full article content - requires `fetch_content=True` in v0.2.0+)
- `entry_title` (headline)
- `entry_description` (brief summary)
- `entry_link` (URL)

### Hierarchical Views

Build denormalized DataFrames combining topic, feed, and entry data:

```python
from carver_feeds import create_data_manager

dm = create_data_manager()

# Topic + Feed hierarchy (fast, no entries)
hierarchy = dm.get_hierarchical_view(include_entries=False)

# Full hierarchy for a specific feed
full = dm.get_hierarchical_view(include_entries=True, feed_id="feed-456")

# Full hierarchy for a topic (all feeds + entries)
topic_data = dm.get_hierarchical_view(include_entries=True, topic_id="topic-123")
```

## 📚 Documentation

- **[API Reference](https://github.com/carveragents/carver-feeds-sdk/blob/master/docs/api-reference.md)**: Detailed API endpoint and module reference
- **[Usage Examples](https://github.com/carveragents/carver-feeds-sdk/blob/master/docs/examples.md)**: A collection of comprehensive examples covering common workflows

## 📋 Requirements

- Python 3.10 or higher
- pandas >= 2.0.0
- requests >= 2.31.0
- boto3 >= 1.26.0 (optional, required for S3 content fetching in v0.2.0+)
- See [pyproject.toml](pyproject.toml) for complete dependency list

## 🔧 Development

### Install for Development

```bash
# Clone repository
git clone https://github.com/carveragents/carver-feeds-sdk.git
cd carver-feeds-sdk

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

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

### 🚢 Publishing to PyPI

```bash
# Install packaging tools
python -m pip install --upgrade build twine

# Clean old artifacts
rm -rf dist build *.egg-info

# Build source and wheel distributions
python -m build

# Upload to PyPI (use PYPI_API_TOKEN or .pypirc for credentials)
python -m twine upload dist/*
```

### Version Management

We use [`bumpversion`](https://github.com/c4urself/bumpversion) to keep every version reference in sync.

```bash
# Install once (included in dev extras)
python -m pip install bumpversion

# Bump patch/minor/major as needed
bumpversion patch   # or minor / major

# Inspect the changes, update CHANGELOG.md, then build + upload
git status
```

The `.bumpversion.cfg` file updates `pyproject.toml`, `src/carver_feeds/__version__.py`, and the SDK version strings in the docs in one command. After bumping, add a new changelog entry with the chosen version before publishing.

### Project Structure

```
carver-feeds-sdk/
├── src/carver_feeds/        # Main package source
│   ├── __init__.py          # Public package exports
│   ├── __version__.py       # Version metadata
│   ├── carver_api.py        # API client
│   ├── data_manager.py      # DataFrame construction helpers
│   ├── query_engine.py      # Query interface
│   └── py.typed             # PEP 561 marker for type checking
├── tests/                   # Test suite
├── docs/                    # Documentation
├── examples/                # Example scripts
├── CHANGELOG.md             # Release notes
├── MANIFEST.in              # Source distribution manifest
└── pyproject.toml           # Package configuration
```

## 📈 Performance Optimization

### 1. Filter Before Loading

The query engine automatically uses optimized endpoints when you filter before loading data:

```python
# Optimal: Query engine uses get_topic_entries() endpoint
qe = create_query_engine()
results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Optimal: Query engine uses get_feed_entries() endpoint
results = qe.filter_by_feed(feed_name="SEC News").to_dataframe()

# Less optimal: Loads all ~10,000 entries, then filters
results = qe.to_dataframe()  # Loads everything first
filtered = results[results['topic_name'].str.contains("Banking")]
```

### 2. Chain Filters Efficiently

Apply filters in order of specificity (narrowest first):

```python
# Good: Narrow by topic first, then apply other filters
results = qe \
    .filter_by_topic(topic_name="Banking") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries("regulation") \
    .to_dataframe()
```

### 3. Reuse Query Engine

Data is cached after the first load:

```python
qe = create_query_engine()

# First query: loads data from API (~30-60 seconds for all entries)
results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()

# Subsequent queries: use cached data (instant)
results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
```

### 4. Use Data Manager for Simple Queries

For simple filtering without complex logic, use the Data Manager directly:

```python
# Faster for simple use cases
dm = create_data_manager()
entries = dm.get_entries_df(feed_id='feed-456')  # Direct endpoint call
```

## ⚠️ Error Handling

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

## ✅ Best Practices

1. **Use factory functions** for automatic environment configuration:
   ```python
   from carver_feeds import get_client, create_data_manager, create_query_engine

   client = get_client()  # Automatically loads from .env
   dm = create_data_manager()
   qe = create_query_engine()
   ```

2. **Choose the right component** for your use case:
   - **API Client**: Raw API responses, specific control over requests
   - **Data Manager**: Simple DataFrame operations without complex filtering
   - **Query Engine**: Complex queries with multiple filters and chaining

3. **Handle errors gracefully**:
   ```python
   from carver_feeds import create_query_engine, CarverAPIError

   try:
       qe = create_query_engine()
       results = qe.filter_by_topic(topic_name="Banking").to_dataframe()

       if len(results) == 0:
           print("No results found. Try broadening search criteria.")
   except CarverAPIError as e:
       print(f"API error: {e}")
   ```

4. **Export large result sets** to CSV for external processing:
   ```python
   # For large datasets, export rather than keeping in memory
   results = qe.filter_by_topic(topic_name="Banking")
   results.to_csv("banking_entries.csv")  # Saves ~50-100 MB to disk
   ```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite and type checking
5. Submit a pull request

## 💬 Support

For issues, questions, or feature requests:

- **API Reference**: [docs/api-reference.md](https://github.com/carveragents/carver-feeds-sdk/blob/master/docs/api-reference.md)
- **Examples**: [docs/examples.md](https://github.com/carveragents/carver-feeds-sdk/blob/master/docs/examples.md)
- **Issues**: [GitHub Issues](https://github.com/carveragents/carver-feeds-sdk/issues)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

**Note**: This SDK requires a valid Carver API key. Visit [Carver Agents](https://carveragents.ai) to obtain your API key.
