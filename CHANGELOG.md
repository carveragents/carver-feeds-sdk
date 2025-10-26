# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/carveragents/carver-feeds-skill/releases/tag/v0.1.0
