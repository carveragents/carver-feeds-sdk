"""
Carver Feeds SDK

A Python SDK for the Carver Feeds API that enables fetching, analyzing, and querying
regulatory feed data.

Basic Usage:
    >>> from carver_feeds import get_client, create_data_manager, create_query_engine
    >>> from datetime import datetime
    >>>
    >>> # Method 1: Using the API client directly
    >>> client = get_client()
    >>> topics = client.list_topics()
    >>>
    >>> # Method 2: Using the data manager for DataFrames
    >>> dm = create_data_manager()
    >>> topics_df = dm.get_topics_df()
    >>> entries_df = dm.get_entries_df(feed_id="feed-123")
    >>>
    >>> # Method 3: Using the query engine for advanced queries
    >>> qe = create_query_engine()
    >>> results = qe.filter_by_topic(topic_name="Banking") \\
    ...     .filter_by_date(start_date=datetime(2024, 1, 1)) \\
    ...     .search_entries("regulation") \\
    ...     .to_dataframe()

Environment Setup:
    Create a .env file with your credentials:

    CARVER_API_KEY=your_api_key_here
    CARVER_BASE_URL=https://app.carveragents.ai  # optional
"""

from carver_feeds.__version__ import __version__, __version_info__

# Import API client and factory
from carver_feeds.carver_api import (
    CarverFeedsAPIClient,
    get_client,
    CarverAPIError,
    AuthenticationError,
    RateLimitError,
)

# Import data manager and factory
from carver_feeds.data_manager import (
    FeedsDataManager,
    create_data_manager,
)

# Import query engine and factory
from carver_feeds.query_engine import (
    EntryQueryEngine,
    create_query_engine,
)

# Define public API
__all__ = [
    # Version info
    "__version__",
    "__version_info__",
    # API client
    "CarverFeedsAPIClient",
    "get_client",
    # Data manager
    "FeedsDataManager",
    "create_data_manager",
    # Query engine
    "EntryQueryEngine",
    "create_query_engine",
    # Exceptions
    "CarverAPIError",
    "AuthenticationError",
    "RateLimitError",
]
