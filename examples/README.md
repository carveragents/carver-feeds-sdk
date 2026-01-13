# Carver Feeds SDK Examples

This directory contains example scripts demonstrating various features of the Carver Feeds SDK.

## Prerequisites

1. Install the SDK:
   ```bash
   pip install carver-feeds-sdk
   ```

2. Create a `.env` file in your working directory:
   ```bash
   CARVER_API_KEY=your_api_key_here
   CARVER_BASE_URL=https://app.carveragents.ai  # optional

   # NEW in v0.2.0: S3 Content Fetching (optional)
   AWS_PROFILE_NAME=your-aws-profile  # optional, for S3 content
   AWS_REGION=us-east-1  # optional, defaults to us-east-1
   ```

3. (Optional) For S3 content fetching, configure AWS credentials:
   ```bash
   # Create/edit ~/.aws/credentials
   [your-aws-profile]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

## Running Examples

### Basic Usage

Demonstrates fundamental SDK operations:

```bash
python basic_usage.py
```

Features:
- Direct API client usage
- DataFrame operations
- Fetching topics and entries
- **NEW in v0.2.0**: S3 content fetching

### Advanced Queries

Shows advanced querying capabilities:

```bash
python advanced_queries.py
```

Features:
- Method chaining
- Multi-filter queries
- Keyword search
- Date range filtering
- Export to CSV/JSON
- **NEW in v0.2.0**: Lazy loading with S3 content

### S3 Content Fetching (v0.2.0+)

Demonstrates S3 content fetching capabilities:

```bash
python s3_content_fetching.py
```

Features:
- **NEW in v0.2.0**: S3 client configuration and setup
- **NEW in v0.2.0**: Eager loading (fetch content immediately)
- **NEW in v0.2.0**: Lazy loading (filter first, fetch later)
- **NEW in v0.2.0**: Direct S3 client usage
- **NEW in v0.2.0**: Batch fetching with parallel workers
- **NEW in v0.2.0**: Working with extracted_metadata fields

**Note:** Requires AWS credentials configured. See prerequisites above.

## Additional Examples

For more comprehensive examples, see the [main examples documentation](../docs/examples.md).

## Getting Help

- **Main Documentation**: [../README.md](../README.md)
- **API Reference**: [../docs/api-reference.md](../docs/api-reference.md)
- **Usage Examples**: [../docs/examples.md](../docs/examples.md)
- **Issues**: [GitHub Issues](https://github.com/carveragents/carver-feeds-sdk/issues)
