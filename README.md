# Carver Feeds SDK

![PyPI - Version](https://img.shields.io/pypi/v/carver-feeds-sdk)
[![Python Support](https://img.shields.io/pypi/pyversions/carver-feeds-sdk.svg)](https://pypi.org/project/carver-feeds-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python SDK for the Carver Feeds API, enabling seamless access to regulatory feed data with querying, filtering, and data analysis capabilities.

## 🎯 Features

- **Comprehensive API Client**: Full support for public Carver Feeds API endpoints with authentication, retry logic, and error handling
- **AI-Powered Annotations**: Access AI-generated insights, classifications, relevance scores, and impact assessments for regulatory entries
- **Legal Statutes**: Search and filter legal statutes by jurisdiction, legal level, document type, language, and year; retrieve feed entries linked to a statute
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
- **Legal Statute Lookup**: Search and browse legal statutes, identify which feed entries reference a specific statute

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
```

### 2. Basic Usage

```python

from dotenv import load_dotenv
from carver_feeds import get_client

load_dotenv()

# Initialize client from environment variables
client = get_client()

# Fetch categories
categories = client.list_categories()
print(f"Found {len(categories)} categories")

# Fetch topics
topics = client.list_topics()
print(f"Found {len(topics)} topics")

# Fetch topics filtered by category
finance_topics = client.list_topics(category_id="category-uuid")
print(f"Found {len(finance_topics)} finance topics")

# Fetch topics with detailed information
detailed_topics = client.list_topics(details=True)
print(f"First topic acronym: {detailed_topics[0].get('acronym')}")

# Fetch entries for a specific topic
entries = client.get_topic_entries(topic_id="topic-123")
print(f"Found {len(entries)} entries")
```

### 3. Using DataFrames

```python
from dotenv import load_dotenv
from carver_feeds import create_data_manager

load_dotenv()

# Create data manager
dm = create_data_manager()

# Get categories as DataFrame
categories_df = dm.get_categories_df()
print(categories_df[['id', 'name', 'topic_count']].head())

# Get topics as DataFrame
topics_df = dm.get_topics_df()
print(topics_df[['id', 'name', 'is_active']].head())

# Get topics filtered by category
finance_topics_df = dm.get_topics_df(category_id="category-uuid")
print(f"Found {len(finance_topics_df)} finance topics")

# Get entries for a specific topic (without content)
entries_df = dm.get_topic_entries_df(topic_id="topic-123")
print(f"Found {len(entries_df)} entries")

# Get entries with content
entries_with_content = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=True)
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

# Filter by category to get all entries across a category's topics
results = qe \
    .filter_by_category(category_name="Finance") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries("regulation") \
    .to_dataframe()

print(f"Found {len(results)} matching entries")

# Or filter by specific topic within a category
results = qe.chain() \
    .filter_by_category(category_name="Finance") \
    .filter_by_topic(topic_name="Abu Dhabi") \
    .to_dataframe()

# Export results
qe.to_csv("results.csv")
qe.to_json("results.json")
```

## 🏗️ Core Components

### API Client (`CarverFeedsAPIClient`)

Low-level API client with comprehensive error handling:

- X-API-Key authentication
- Exponential backoff retry logic for rate limits
- Support for categories, topics, and topic-based entry retrieval
- AI-generated annotations retrieval with filtering by entries, topics, or users
- Legal statutes retrieval with filtering, single-statute lookup, and annotation linkage

### Data Manager (`FeedsDataManager`)

Converts API responses to pandas DataFrames:

- JSON to DataFrame conversion with schema validation
- Hierarchical data views (category → topic → entry)
- Handles categories, topics, and entries
- Content fetching capability

### Query Engine (`EntryQueryEngine`)

High-level query interface with fluent API:

- Method chaining for complex queries
- Filter by category, topic, date range, and status
- Keyword search with AND/OR logic across multiple fields
- Multiple export formats (DataFrame, CSV, JSON, dict)
- Lazy loading with automatic endpoint optimization

## 📊 Data Model

The SDK works with four main entities in a hierarchical structure:

```
Category (grouping of topics, e.g., "Finance", "Medical Devices")
  ↓ 1:N
Topic (regulatory bodies like SEC, SEBI, RBI, etc.)
  ↓ 1:N
Entry (individual articles/entries)
  ↓ 1:1
Annotation (AI-generated insights and classifications)
```

**Key Fields**:
- **Category**: `id`, `name`, `slug`, `description`, `color`, `is_active`, `topic_count`, timestamps
- **Topic**: `id`, `name`, `description`, `is_active`, timestamps (use `details=True` for extended fields: `acronym`, `jurisdiction_code`, `sectors`, `industries`, `functions`, and more)
- **Entry**: `id`, `title`, `link`, `entry_content_markdown`, `description`, `published_at`, `feed_id`, `topic_id`, `content_status`, `s3_content_md_path`, `s3_content_html_path`, `is_active`, timestamps
- **Annotation**: `scores` (impact, urgency, relevance), `classification` (update_type, regulatory_source), `metadata` (tags, impact_summary, impacted_business, critical_dates)

## ⚡ Advanced Features

### Keyword Search

```python
# Single keyword (case-insensitive by default, searches in title/description)
qe.filter_by_topic(topic_name="Abu Dhabi") \
    .search_entries("regulation", search_fields=['entry_title', 'entry_description']) \
    .to_dataframe()

# Multiple keywords with OR logic (matches ANY)
qe.filter_by_topic(topic_name="Abu Dhabi") \
    .search_entries(["regulation", "compliance", "enforcement"], match_all=False,
                   search_fields=['entry_title', 'entry_description'])

# Multiple keywords with AND logic (matches ALL)
qe.filter_by_topic(topic_name="Abu Dhabi") \
    .search_entries(["financial", "regulation"], match_all=True,
                   search_fields=['entry_title', 'entry_description'])

# Search in full content (requires fetch_content)
qe.filter_by_topic(topic_name="Abu Dhabi") \
    .fetch_content() \
    .search_entries("regulation")  # Searches in entry_content_markdown

# Case-sensitive search
qe.filter_by_topic(topic_name="Abu Dhabi") \
    .search_entries("SEC", case_sensitive=True, search_fields=['entry_title'])
```

**Available Search Fields**:
- `entry_content_markdown` (default, full article content - requires `fetch_content=True`)
- `entry_title` (headline)
- `entry_description` (brief summary)
- `entry_link` (URL)

### Annotations & AI Insights

Access AI-generated insights, classifications, and impact assessments for regulatory entries:

```python
from carver_feeds import get_client

client = get_client()

# Get annotations for specific entries
annotations = client.get_annotations(
    feed_entry_ids=["entry-uuid-1", "entry-uuid-2"]
)

# Get annotations for a topic
topic_annotations = client.get_annotations(topic_ids=["topic-uuid-1"])

# Get annotations for a user's subscriptions
user_annotations = client.get_annotations(user_ids=["user-uuid-1"])

# Process annotation insights
for ann in annotations:
    scores = ann['annotation']['scores']
    print(f"Entry: {ann['feed_entry_id']}")
    print(f"Impact: {scores['impact']['label']} (score: {scores['impact']['score']})")
    print(f"Urgency: {scores['urgency']['label']}")
    print(f"Relevance: {scores['relevance']['score']}")

    # Access rich metadata
    metadata = ann['annotation']['metadata']
    print(f"Tags: {metadata['tags']}")
    print(f"Impacted Industries: {metadata['impacted_business']['industry']}")

# Filter by high impact
high_impact = [
    a for a in annotations
    if a['annotation']['scores']['impact']['score'] > 5
]
print(f"Found {len(high_impact)} high-impact entries")
```

### Legal Statutes

Search and browse legal statutes, and find feed entries that reference a specific statute:

```python
from carver_feeds import get_client

client = get_client()

# Discover available filter values before querying
options = client.get_statute_filter_options()
print(f"Jurisdictions: {', '.join(options['jurisdictions'])}")
print(f"Legal levels:  {', '.join(options['legal_levels'])}")

# List statutes — filter by jurisdiction, year, full-text search, etc.
result = client.list_statutes(jurisdiction="US", legal_level="legislative", limit=10)
print(f"Found {result['total']} US legislative statutes")
for statute in result["statutes"]:
    print(f"  {statute['canonical_name']} ({statute.get('year', 'N/A')})")

# Fetch a single statute by ID
statute = client.get_statute("statute-uuid")
print(f"Name:     {statute['canonical_name']}")
print(f"Citation: {statute.get('code_citation')}")
print(f"Variants: {', '.join(statute.get('variants', []))}")

# Find all feed entries that reference a specific statute
result = client.get_statute_annotations("statute-uuid")
print(f"Referenced in {result['total']} feed entries")
for entry in result["feed_entries"]:
    print(f"  - {entry['title']}: {entry['link']}")
```

**Statute filter parameters** (all optional):
- `jurisdiction` — ISO country code (e.g., `"US"`, `"ES"`, `"AD"`)
- `legal_level` — e.g., `"legislative"`, `"executive / administrative"`
- `document_type` — e.g., `"law"`, `"regulation"`, `"circular"`
- `original_language` — ISO language code (e.g., `"en"`, `"es"`)
- `year` — four-digit calendar year
- `search` — full-text search on statute text
- `limit` / `offset` — pagination (default limit: 50)

Use `get_statute_filter_options()` to discover the exact values accepted by each filter.

### Hierarchical Views

Build denormalized DataFrames combining topic and entry data:

```python
from carver_feeds import create_data_manager

dm = create_data_manager()

# Topic metadata only (fast, no entries)
topic_only = dm.get_hierarchical_view(topic_id="topic-123", include_entries=False)

# Full hierarchy for a topic (topic + entries)
topic_data = dm.get_hierarchical_view(topic_id="topic-123", include_entries=True)

# With content fetching
topic_with_content = dm.get_hierarchical_view(
    topic_id="topic-123",
    include_entries=True,
    fetch_content=True
)
```

## 📚 Documentation

- **[API Reference](https://github.com/carveragents/carver-feeds-sdk/blob/master/docs/api-reference.md)**: Detailed API endpoint and module reference
- **[Usage Examples](https://github.com/carveragents/carver-feeds-sdk/blob/master/examples/README.md)**: A collection of comprehensive examples covering common workflows

## 📋 Requirements

- Python 3.10 or higher
- pandas >= 2.0.0
- requests >= 2.31.0
- boto3 >= 1.26.0 (optional, required for content fetching)
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
results = qe.filter_by_topic(topic_name="Abu Dhabi").to_dataframe()

# Filter by category first, then narrow by topic
results = qe.filter_by_category(category_name="Finance") \
    .filter_by_topic(topic_name="Abu Dhabi") \
    .to_dataframe()

# Required pattern: Always start with filter_by_category() or filter_by_topic()
results = qe.filter_by_topic(topic_name="Abu Dhabi") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .to_dataframe()
```

### 2. Chain Filters Efficiently

Apply filters in order of specificity (narrowest first):

```python
# Good: Narrow by topic first, then apply other filters
results = qe \
    .filter_by_topic(topic_name="Abu Dhabi") \
    .filter_by_date(start_date=datetime(2024, 1, 1)) \
    .search_entries("regulation") \
    .to_dataframe()
```

### 3. Reuse Query Engine

Data is cached after the first load:

```python
qe = create_query_engine()

# First query: loads data from API (~30-60 seconds for all entries)
results1 = qe.filter_by_topic(topic_name="Abu Dhabi").to_dataframe()

# Subsequent queries: use cached data (instant)
results2 = qe.chain().filter_by_topic(topic_name="Healthcare").to_dataframe()
```

### 4. Use Data Manager for Simple Queries

For simple filtering without complex logic, use the Data Manager directly:

```python
# Faster for simple use cases
dm = create_data_manager()
entries = dm.get_topic_entries_df(topic_id='topic-123')  # Direct endpoint call
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
       results = qe.filter_by_topic(topic_name="Abu Dhabi").to_dataframe()

       if len(results) == 0:
           print("No results found. Try broadening search criteria.")
   except CarverAPIError as e:
       print(f"API error: {e}")
   ```

4. **Export large result sets** to CSV for external processing:
   ```python
   # For large datasets, export rather than keeping in memory
   results = qe.filter_by_topic(topic_name="Abu Dhabi")
   results.to_csv("abu_dhabi_entries.csv")  # Saves ~50-100 MB to disk
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
- **Examples**: [examples/README.md](https://github.com/carveragents/carver-feeds-sdk/blob/master/examples/README.md)
- **Issues**: [GitHub Issues](https://github.com/carveragents/carver-feeds-sdk/issues)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

**Note**: This SDK requires a valid Carver API key. Visit [Carver Agents](https://carveragents.ai) to obtain your API key.
