# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-01-15

### Added
- **Comprehensive Technical Documentation** (`docs/technical-details.md`)
  - Complete developer guide covering setup, architecture, testing, and workflows
  - Performance optimization strategies and guidelines
  - Error handling patterns and retry logic documentation
  - Code style guidelines and conventions
  - Package structure and organization details
  - Publishing workflow and release checklist
  - Common gotchas and solutions with examples
  - Dependency management guidelines
  - 800+ lines of detailed technical reference

- **Documentation Index** (`docs/README.md`)
  - Structured documentation organization by audience (developers, users, troubleshooting)
  - Cross-references to all documentation resources
  - Clear navigation paths for different use cases
  - Contributing guidelines for documentation updates

- **Development Tooling** (`.claude/`)
  - Session tracking for development progress visibility
  - Custom agent configurations for specialized Python assistance
  - Historical session files for context preservation

- **FLUX Framework Integration**
  - Added reference to FLUX framework compatibility in CLAUDE.md
  - Indicates project designed for FLUX workflow integration

### Changed
- **CLAUDE.md Restructured**
  - Reduced from 280+ lines to ~150 lines of focused quick-reference content
  - Now serves as pointer to comprehensive documentation files
  - Maintains only essential quick-reference information for Claude Code
  - All technical details moved to proper documentation locations

- **Documentation Organization**
  - Consolidated redundant S3 documentation files into unified technical reference
  - Removed `docs/s3-content/ARCHITECTURE_DIAGRAM.md` (1,396 lines)
  - Removed `docs/s3-content/IMPLEMENTATION_PLAN.md` (429 lines)
  - Removed `docs/s3-content/QUICK_REFERENCE.md` (465 lines)
  - Content consolidated into `docs/technical-details.md` and existing API reference

- **.gitignore Updates**
  - Now tracks CLAUDE.md, docs/README.md, docs/LESSONS.md
  - Only ignores `.claude/settings.local.json` (not entire .claude/ directory)
  - Enables version control of documentation and development workflow files

- **Bumpversion Configuration**
  - Removed reference to non-existent `docs/examples.md`
  - Fixed version string synchronization across files

### Documentation
- **Enhanced Developer Experience**
  - Single source of truth for technical details in version-controlled documentation
  - Improved discoverability with clear documentation structure
  - Better organized by audience and use case
  - Easier maintenance with consolidated content

- **Updated Cross-References**
  - All documentation files now properly reference technical-details.md
  - Performance optimization guidance centralized
  - Troubleshooting paths clearly documented

### Notes
This release focuses on documentation improvements and developer experience enhancements. No SDK code changes or API modifications. All functionality from v0.2.0 remains unchanged.

## [0.2.0] - 2025-11-19

### Added
- **S3 Content Fetching**: Entry content is now fetched from AWS S3
  - New `S3ContentClient` class for AWS S3 integration with profile-based authentication
  - Support for `fetch_content` parameter in `get_entries_df()` and `get_hierarchical_view()`
  - New `fetch_content()` method in `EntryQueryEngine` for lazy loading content
  - Batch fetching with parallel requests (10 concurrent workers) for performance
  - Graceful error handling with retry logic and exponential backoff

- **New Metadata Fields**: All entries now include `extracted_metadata` fields
  - `feed_id`: Feed ID extracted from metadata (improves hierarchical mapping)
  - `topic_id`: Topic ID extracted from metadata
  - `content_status`: Content extraction status (e.g., "done", "pending")
  - `content_timestamp`: When content was last fetched/updated
  - `s3_content_md_path`: S3 path to markdown content
  - `s3_content_html_path`: S3 path to HTML content
  - `s3_aggregated_content_md_path`: S3 path to aggregated content

- **Factory Functions**: Updated to support S3 content fetching
  - `create_query_engine(fetch_content=False, s3_client=None)`: Opt-in content fetching
  - `get_s3_client(load_from_env=True)`: Create S3 client from environment config

### Changed
- **BREAKING (API Change)**: Content is no longer returned directly by the Carver API
  - `content_markdown` field must be fetched from S3 using `fetch_content=True`
  - Without `fetch_content=True`, `content_markdown` will be `None`
  - This is backward compatible for code that doesn't use content

- **AWS Configuration Required**: For content fetching, configure AWS credentials using one of two methods:
  - **Method 1 (Recommended)**: AWS Profile - uses `~/.aws/credentials` profile
  - **Method 2**: Direct Credentials - uses access key ID and secret key
  - Profile takes precedence if both are configured
  - See updated `.env.example` for detailed setup instructions

- **Dependencies**: Added `boto3>=1.34.0,<2.0.0` as required dependency

### Migration Guide
For users who need entry content, configure AWS credentials using one of these methods:

#### Method 1: AWS Profile (Recommended for Local Development)

1. Configure AWS profile in `~/.aws/credentials`:
   ```ini
   [carver-prod]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

2. Add profile name to `.env`:
   ```bash
   AWS_PROFILE_NAME=carver-prod
   AWS_REGION=us-east-1  # optional
   ```

#### Method 2: Direct Credentials (Recommended for CI/CD)

Add credentials directly to `.env`:
```bash
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
AWS_REGION=us-east-1  # optional
```

**Note:** If both methods are configured, the AWS profile takes priority.

#### Using Content Fetching in Code

Update your code to fetch content:

```python
# Before (v0.1.x)
entries = dm.get_entries_df()

# After (v0.2.0)
entries = dm.get_entries_df(fetch_content=True)
```

For better performance, use lazy loading:
   ```python
   qe = create_query_engine()
   results = qe.filter_by_topic(topic_name="Banking") \
       .fetch_content() \
       .to_dataframe()
   ```

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

[0.3.0]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.3.0
[0.2.0]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.2.0
[0.1.2]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.1.2
[0.1.1]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.1.1
[0.1.0]: https://github.com/carveragents/carver-feeds-sdk/releases/tag/v0.1.0
