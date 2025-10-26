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
- Fetching topics, feeds, and entries

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

## Additional Examples

For more comprehensive examples, see the [main examples documentation](../docs/examples.md).

## Getting Help

- **Documentation**: [../docs/README.md](../docs/README.md)
- **API Reference**: [../docs/api-reference.md](../docs/api-reference.md)
- **Issues**: [GitHub Issues](https://github.com/carveragents/carver-feeds-skill/issues)
