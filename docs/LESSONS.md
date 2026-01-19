# Development Lessons

Lessons learned during SDK development, documented for future enhancement and cross-project application.

## SESSIONS

- `2025-11-18-1855-feat-feed-new-field` - S3 content fetching implementation (v0.2.0)
- `2026-01-12-1224-feat-s3-endpoints` - User topic subscriptions & S3 pre-signed URL architecture
- `2026-01-13-1207-feat-new-get-endpoint` - Annotations endpoint implementation with API structure discovery
- `2026-01-19-1011-docs-annotations-update` - Update documentation to include annotations details

## LESSONS

### 1. Breaking API Changes Require Clear Migration Paths

**Problem Encountered**:
When the Carver API changed to store entry content in S3 instead of returning it directly, existing SDK code became broken for users who relied on content_markdown.

**Mitigation**:
- Implemented graceful degradation: SDK works without AWS credentials, content_markdown is None instead of error
- Created opt-in feature with `fetch_content=True` parameter
- Provided comprehensive migration guide in CHANGELOG with before/after code examples
- Documented breaking change clearly in release notes

**Lesson Learned**:
When APIs change externally, always provide escape hatches for existing code. Users need a smooth upgrade path—not just a "here's what broke" message. Graceful degradation (feature works but limited without new config) is better than hard failure.

**Applicable To**: Any library integrating external APIs or services

### 2. User-Reported Issues Often Indicate Real Problems Worth Investigating

**Problem Encountered**:
User reported: "No matter what limit value I pass, I always get back 100 entries." Initial assumption: user error.

**Mitigation**:
- Created debug script to verify behavior across multiple limit values (3, 10, 50, 100, 200, 500, 1000)
- Script proved API server hard-limits at 100 entries per page
- Fixed DEFAULT_PAGE_LIMIT constant to match reality (1000 → 100)
- Updated all endpoint docstrings to document the server-side limit

**Lesson Learned**:
Don't dismiss user reports as "user error" without investigation. Sometimes what looks like a bug report is actually discovering a constraint the documentation missed. Create simple test scripts to verify behavior before assuming the code is correct.

**Applicable To**: Any library or service with external dependencies or constraints

### 3. Test Environment Isolation Requires Understanding Tool Behavior Beyond Primary Purpose

**Problem Encountered**:
Test failure: Factory function `get_s3_client()` loaded from `.env` file even when environment dict was mocked to be empty.

**Mitigation**:
- Added `load_from_env` parameter to factory function
- Test calls now explicitly use `load_from_env=False` to prevent side effects
- Tests properly isolated from actual environment files

**Lesson Learned**:
Mocking frameworks work at the parameter level, but functions have side effects. When a function calls `load_dotenv()` internally, mocking the environment dict doesn't stop it from reading the file. Read implementation details of functions you mock to understand all their side effects.

**Applicable To**: Any testing involving environment configuration or external state

### 4. Understand Domain Semantics When Designing Examples

**Problem Encountered**:
Used "Banking" as a topic filter in examples, but Carver's "topics" represent regulatory bodies (Abu Dhabi DFSA, RBI, SEC), not industry sectors. This caused confusion about what data users would query.

**Mitigation**:
- Changed all examples to use actual regulatory body names (Abu Dhabi, Healthcare regulators, etc.)
- Updated documentation to clarify: "topics = regulatory bodies, not industries"
- Systematically replaced 27 instances of Banking references across README files

**Lesson Learned**:
When creating examples, understand the semantic meaning of entities in the domain model. Don't just pick convenient placeholder names—use real-world examples that match actual data. This prevents user confusion and makes documentation more valuable.

**Applicable To**: Any SDK/library documentation, especially with domain-specific concepts

### 5. Documentation Audits: Stale References Are Maintenance Debt

**Problem Encountered**:
`examples/README.md` referenced `s3_content_fetching.py` script that didn't exist, creating broken documentation and user confusion about available resources.

**Mitigation**:
- Removed entire section referencing missing file
- Added audit step to documentation creation process: verify all referenced files exist
- Plan to add CI check: verify all docs reference existing files

**Lesson Learned**:
Documentation references to non-existent code are worse than no documentation—they erode user trust. Treat documentation synchronization as essential maintenance, not optional cleanup. Consider automated checks.

**Applicable To**: Any documentation system; especially good candidates for CI validation

### 6. Validate Against Real APIs Early to Avoid Incorrect Assumptions

**Problem Encountered**:
During implementation of the annotations endpoint, assumed API response would have simple float scores and a `summary` field. Testing against real API revealed complex nested structure: scores are objects with `{label, score, confidence}`, and rich metadata includes `impact_summary`, `impacted_business`, `critical_dates`.

**Mitigation**:
- Added debug output when first testing to inspect actual API response structure
- Immediately updated code, documentation, and test fixtures to match reality
- Created comprehensive documentation showing actual nested structure
- All examples tested against real API before finalizing

**Lesson Learned**:
Never assume external API response structure based on documentation or spec alone. Test integration code against real APIs early (even during development, not just at the end). Real APIs often return richer data structures than anticipated, and tests using simplified fixtures will hide these differences until production.

**Applicable To**: Any SDK or library integrating external APIs; critical for integration testing strategy

---

**Document Version**: 1.3
**Last Updated**: 2026-01-19
