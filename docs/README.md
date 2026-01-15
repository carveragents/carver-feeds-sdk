# Documentation Index

This directory contains comprehensive documentation for the Carver Feeds SDK.

## Quick Reference

- **[Technical Details](technical-details.md)** - Complete developer guide with setup, architecture, testing, and workflows
- **[API Reference](api-reference.md)** - Complete API endpoint documentation, data schemas, module reference, and common patterns
- **[Lessons Learned](LESSONS.md)** - Development lessons and best practices from SDK evolution

## Documentation Overview

### Technical Details (`technical-details.md`)
Comprehensive developer guide covering:
- Development setup and environment configuration
- Complete architecture explanation (three-layer design, data models, S3 integration)
- Common development commands (testing, quality checks, version management, publishing)
- Performance optimization strategies and guidelines
- Testing strategy and best practices
- Error handling patterns and retry logic
- Code style guidelines and conventions
- Package structure and organization
- Publishing workflow and checklist
- Common gotchas and solutions
- Dependency management

### API Reference (`api-reference.md`)
Complete technical reference including:
- API endpoints and authentication
- All data schemas (Topic, Feed, Entry)
- Module API reference (CarverFeedsAPIClient, FeedsDataManager, EntryQueryEngine, S3ContentClient)
- Common patterns and workflows
- Error handling guide
- Performance considerations

### Lessons Learned (`LESSONS.md`)
Development insights and best practices:
- Architecture decisions and trade-offs
- Problems encountered and solutions
- Tips for future developers
- Cross-project applicable lessons

## Related Documentation

- **[Main README](../README.md)** - Project overview, quick start, and usage guide
- **[CHANGELOG](../CHANGELOG.md)** - Version history and release notes

## For Different Audiences

### For Developers Working on the SDK
1. Start: [Technical Details](technical-details.md) - Complete developer guide
2. Check: [Lessons Learned](LESSONS.md) - Prior decisions and gotchas
3. Review: [API Reference](api-reference.md) - Module APIs and patterns

### For Getting Started
1. Read: [Main README - Quick Start](../README.md#-quick-start)
2. Read: [API Reference - API Information](api-reference.md#api-information)
3. Browse: [Examples README](../examples/README.md)

### For API Integration
1. Read: [API Reference - Endpoint Documentation](api-reference.md#endpoint-documentation)
2. Reference: [API Reference - Module API Reference](api-reference.md#module-api-reference)
3. Check: [API Reference - Error Handling](api-reference.md#error-handling)

### For Performance Optimization
1. Start: [Technical Details - Performance Optimization](technical-details.md#performance-optimization)
2. Read: [Main README - Performance Optimization](../README.md#-performance-optimization)
3. Reference: [API Reference - Performance Considerations](api-reference.md#performance-considerations)

### For Troubleshooting
1. Check: [Technical Details - Common Gotchas](technical-details.md#common-gotchas)
2. Read: [API Reference - Error Handling](api-reference.md#error-handling)
3. See: [Technical Details - Error Handling](technical-details.md#error-handling)
4. Review: [Main README - Error Handling](../README.md#-error-handling)

## Key Concepts

### Three-Layer SDK Architecture
1. **CarverFeedsAPIClient** - Low-level HTTP client with authentication and pagination
2. **FeedsDataManager** - DataFrame conversion and hierarchical data views
3. **EntryQueryEngine** - High-level fluent query interface with method chaining

### Data Model
```
Topic (regulatory body)
  └─ Entry (individual article)
```

### Content Fetching
- Entry content stored in blob storage instead of API response
- Two authentication methods: AWS Profile (recommended) or Direct Credentials
- Lazy loading: Filter first, fetch content later (more efficient)
- Eager loading: Fetch all content immediately

## Contributing Updates

When updating documentation:
1. Keep [Technical Details](technical-details.md) as single source of truth for development/architecture details
2. Keep [API Reference](api-reference.md) as single source of truth for API specifications
3. Update [Main README](../README.md) for user-facing guidance and quick start
4. Add examples to [Examples directory](../examples/) for common workflows
5. Update [Lessons Learned](LESSONS.md) with insights from development
6. Keep this index synchronized with documentation changes

---

**Last Updated**: 2026-01-15
**SDK Version**: 0.2.0+ (v0.3.0 planned)
**Status**: Production Ready
