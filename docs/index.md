---
layout: home
title: ""
---

## Carver Feeds

![PyPI - Version](https://img.shields.io/pypi/v/carver-feeds-sdk)
[![Python Support](https://img.shields.io/pypi/pyversions/carver-feeds-sdk.svg)](https://pypi.org/project/carver-feeds-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Carver Feeds is a real-time regulatory intelligence feed service from Carver Agents. It provides continuously updated regulatory entries (announcements, rules, consultations, enforcement actions, guidance, and more) organized by regulatory bodies, so teams can monitor changes, run analysis, and power downstream workflows.

If you’re looking for the SDK reference and code samples, start here:

➡️ **[Python SDK Documentation](sdk/)**

---

## What you can build with Carver Feeds

* **Regulatory monitoring** across jurisdictions and agencies
* **Automated alerting** for new or relevant publications
* **Research and trend analysis** over historical regulatory data
* **Internal dashboards** for compliance, risk, and legal stakeholders
* **Data pipelines** that transform regulatory updates into structured datasets

---

## How the data is structured

Carver Feeds data is organized into three core objects:

* **Topics**: sources or regulatory bodies (e.g., a regulator, authority, court)
* **Entries**: individual regulatory updates published by a source (contains title, link, basic metadata, optional full content)
* **Annotations**: Carver-enriched updates containing rich metadata, insights, scores
  
This hierarchy makes it easy to pull feed entries for specific topic(s), filter by various facets, and then run analytics over the resulting set.

---

## Quick Start (Python)

Install the SDK:

```bash
pip install carver-feeds-sdk
```

Set your API key (example using a `.env` file):

```bash
CARVER_API_KEY=your_api_key_here
CARVER_BASE_URL=https://app.carveragents.ai  # optional
```

Minimal usage:

```python
from dotenv import load_dotenv
from carver_feeds import get_client

load_dotenv()

client = get_client()
topics = client.list_topics()
print(f"Found {len(topics)} topics")
```

For full examples, advanced querying, DataFrame workflows, caching, and error handling:

➡️ **[Read the SDK documentation](sdk/)**

---

## Need access?

This SDK requires a valid Carver API key. Visit: [https://carveragents.ai](https://carveragents.ai)
