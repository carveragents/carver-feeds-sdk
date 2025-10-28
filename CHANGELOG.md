# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-10-28

### Fixed
- Python 3.12 compatibility issue with pyarrow dependency
  - Updated pyarrow version constraint from `>=12.0.0,<13.0.0` to `>=14.0.0,<19.0.0`
  - PyArrow 14.0.0+ includes pre-built wheels for Python 3.12, preventing build-from-source failures
  - Maintains backward compatibility with Python 3.10 and 3.11
  - All tests pass on Python 3.10.17, 3.11.12, and 3.12.10

## [0.1.1] - 2025-10-28

### Fixed
- Schema validation warning for `published_date` mapping
  - Fixed spurious "Adding missing column: published_at" warning
  - Adjusted expected_columns to match actual API response schema (published_date), then map it to published_at after validation
  - Applied in both `get_entries()` and `get_hierarchical_view()` methods
- Defensive checks for missing `published_date` field
  - Added fallback logic to handle edge cases where API response might be missing the published_date field
  - In `get_entries()`: Create empty published_at column (pd.NaT) if published_date is missing
  - In `get_hierarchical_view()`: Changed column renaming from static dict to dynamic dict that only renames columns that actually exist
  - Prevents 'entry_published_at column not found' errors in query engine

### Documentation
- Enhanced README with regulatory intelligence focus
  - Added "About The SDK" section linking to Carver RegWatch platform
  - Added "Who Is This For?" section targeting compliance/risk/developer audiences
  - Added "Use Cases" section with concrete regulatory monitoring scenarios
  - Added emoji headers to all major sections for improved visual hierarchy
  - Expanded pyproject.toml keywords with regulatory and compliance terms
- Minor README improvements
  - Clarified 'Topic' definition
  - Updated handling description to be more general
  - Added additional documentation content

## [0.1.0] - 2025-10-26

### Added
- Initial release of Carver Feeds SDK
- Core API client (`CarverFeedsAPIClient`) with authentication and retry logic
- Data management layer (`FeedsDataManager`) for DataFrame construction
- Query engine (`EntryQueryEngine`) with fluent API and method chaining
- Support for 5 API endpoints:
  - List topics
  - List feeds
  - List all entries
  - Get feed-specific entries
  - Get topic-specific entries
- Automatic pagination handling with limit/offset pattern
- Exponential backoff retry logic for rate limits and server errors
- Hierarchical data views (topic → feed → entry relationships)
- Multiple export formats (DataFrame, CSV, JSON, dict)
- Optimized endpoint selection for better performance
- Comprehensive documentation and examples
- Type hints throughout codebase
- PEP 561 compatibility (py.typed marker)

### Features
- **Authentication**: X-API-Key header authentication
- **Pagination**: Automatic handling of paginated responses
- **Error Handling**: Comprehensive error handling with helpful messages
- **Filtering**: Filter by topic, feed, date range, and active status
- **Search**: Keyword search with AND/OR logic across multiple fields
- **Lazy Loading**: Data fetched only when needed
- **Caching**: Query results cached for reuse

### Documentation
- Complete API reference
- Usage examples covering common workflows
- Quick start guide
- Troubleshooting tips

[0.1.2]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.1.2
[0.1.1]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.1.1
[0.1.0]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.1.0
