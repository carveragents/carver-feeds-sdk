"""
Data Manager Module

This module handles converting API responses to pandas DataFrames
and building hierarchical views of the data.

Example:
    >>> from carver_feeds import create_data_manager
    >>> dm = create_data_manager()
    >>> topics_df = dm.get_topics_df()
    >>> entries_df = dm.get_entries_df(fetch_all=True)
"""

import logging

import pandas as pd

from carver_feeds.carver_api import CarverAPIError, CarverFeedsAPIClient, get_client
from carver_feeds.s3_client import S3ContentClient, get_s3_client

# Configure module logger (library should not configure logging)
logger = logging.getLogger(__name__)


# Data Manager Configuration Constants
DEFAULT_FETCH_LIMIT = 1000


class FeedsDataManager:
    """
    Manager for processing and organizing feed data.

    This class handles fetching data from the Carver API and converting
    it to structured pandas DataFrames. It provides methods to fetch
    topics, feeds, and entries, and construct hierarchical views.

    Features:
    - JSON to DataFrame conversion with schema validation
    - Automatic pagination for entries
    - Graceful handling of missing/null fields
    - Comprehensive error handling and logging

    Args:
        api_client: CarverFeedsAPIClient instance for API interactions

    Example:
        >>> from carver_feeds import create_data_manager
        >>> dm = create_data_manager()
        >>> topics_df = dm.get_topics_df()
        >>> entries_df = dm.get_entries_df(fetch_all=True)
    """

    def __init__(self, api_client: CarverFeedsAPIClient):
        """Initialize with API client."""
        if not isinstance(api_client, CarverFeedsAPIClient):
            raise TypeError("api_client must be an instance of CarverFeedsAPIClient")
        self.api_client = api_client
        logger.info("FeedsDataManager initialized")

    def get_topics_df(self) -> pd.DataFrame:
        """
        Fetch topics and return as DataFrame.

        Returns a DataFrame with the following columns:
        - id: Topic ID
        - name: Topic name
        - description: Topic description
        - created_at: Creation timestamp
        - updated_at: Last update timestamp
        - is_active: Active status

        Returns:
            pd.DataFrame: Topics with standardized schema

        Raises:
            CarverAPIError: If API request fails

        Example:
            >>> dm = create_data_manager()
            >>> topics = dm.get_topics_df()
            >>> print(f"Found {len(topics)} topics")
            >>> print(topics[['id', 'name', 'is_active']].head())
        """
        logger.info("Fetching topics as DataFrame...")

        try:
            # Fetch data from API
            topics_data = self.api_client.list_topics()

            # Convert to DataFrame
            expected_columns = [
                "id",
                "name",
                "description",
                "created_at",
                "updated_at",
                "is_active",
            ]
            df = self._json_to_dataframe(topics_data, expected_columns)

            # Convert date columns to datetime
            date_columns = ["created_at", "updated_at"]
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            # Ensure is_active is boolean
            if "is_active" in df.columns:
                df["is_active"] = df["is_active"].fillna(True).astype(bool)

            logger.info(f"Successfully converted {len(df)} topics to DataFrame")
            return df

        except CarverAPIError as e:
            logger.error(f"Failed to fetch topics: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting topics to DataFrame: {e}")
            raise CarverAPIError(f"Data conversion failed: {e}") from e

    def get_user_topic_subscriptions_df(self, user_id: str) -> pd.DataFrame:
        """
        Fetch user topic subscriptions and return as DataFrame.

        Returns a DataFrame with the following columns:
        - id: Topic ID
        - name: Topic name
        - description: Topic description
        - base_domain: Base domain (may be null)

        Note: The API response includes a total_count field which is not included
        in the DataFrame. Access the raw API response if you need this value.

        Args:
            user_id: User identifier (required)

        Returns:
            pd.DataFrame: User's topic subscriptions with standardized schema

        Raises:
            ValueError: If user_id is not provided
            CarverAPIError: If API request fails

        Example:
            >>> dm = create_data_manager()
            >>> subscriptions = dm.get_user_topic_subscriptions_df("user-123")
            >>> print(f"User has {len(subscriptions)} subscriptions")
            >>> print(subscriptions[['id', 'name']].head())
        """
        if not user_id:
            raise ValueError("user_id is required")

        logger.info(f"Fetching topic subscriptions for user {user_id} as DataFrame...")

        try:
            # Fetch data from API
            response = self.api_client.get_user_topic_subscriptions(user_id)

            # Extract subscriptions list from response
            subscriptions_data = response.get("subscriptions", [])

            if not subscriptions_data:
                logger.info(f"User {user_id} has no topic subscriptions")
                # Return empty DataFrame with expected columns
                return pd.DataFrame(columns=["id", "name", "description", "base_domain"])

            # Convert to DataFrame
            expected_columns = [
                "id",
                "name",
                "description",
                "base_domain",
            ]
            df = self._json_to_dataframe(subscriptions_data, expected_columns)

            logger.info(
                f"Successfully converted {len(df)} topic subscriptions to DataFrame "
                f"(total_count: {response.get('total_count', 'unknown')})"
            )
            return df

        except CarverAPIError as e:
            logger.error(f"Failed to fetch topic subscriptions: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting topic subscriptions to DataFrame: {e}")
            raise CarverAPIError(f"Data conversion failed: {e}") from e

    def get_topic_entries_df(
        self,
        topic_id: str,
        fetch_content: bool = False,
        s3_client: S3ContentClient | None = None,
    ) -> pd.DataFrame:
        """
        Fetch entries for a specific topic and return as DataFrame.

        New in v0.2.0: Content is no longer returned directly by the API.
        Use fetch_content=True to automatically fetch content from S3.

        Returns a DataFrame with the following columns:
        - id: Entry ID
        - title: Entry title
        - link: Entry URL/link
        - content_markdown: Full content in markdown (fetched from S3 if fetch_content=True, else None)
        - feed_id: Associated feed ID (from extracted_metadata)
        - topic_id: Associated topic ID (from extracted_metadata)
        - content_status: Content extraction status (from extracted_metadata)
        - content_timestamp: When content was last fetched (from extracted_metadata)
        - s3_content_md_path: S3 path to markdown content (from extracted_metadata)
        - s3_content_html_path: S3 path to HTML content (from extracted_metadata)
        - s3_aggregated_content_md_path: S3 path to aggregated content (from extracted_metadata)
        - published_at: Publication timestamp (uses published_date from API)
        - created_at: Creation timestamp
        - is_active: Active status

        Args:
            topic_id: Topic ID to fetch entries for (required)
            fetch_content: If True, fetch content from S3 (requires S3 credentials)
            s3_client: Optional S3ContentClient instance. If None and fetch_content=True,
                       creates client from environment variables.

        Returns:
            pd.DataFrame: Entries with standardized schema

        Raises:
            CarverAPIError: If API request fails
            ValueError: If topic_id is not provided

        Example:
            >>> dm = create_data_manager()
            >>> # Get entries without content (fast)
            >>> entries = dm.get_topic_entries_df(topic_id="topic-123")
            >>> print(entries[['title', 'feed_id', 'topic_id']])

            >>> # Get entries with content from S3
            >>> entries_with_content = dm.get_topic_entries_df(
            ...     topic_id="topic-123",
            ...     fetch_content=True
            ... )
            >>> print(entries_with_content[['title', 'content_markdown']])
        """
        if not topic_id:
            raise ValueError("topic_id is required")

        logger.info(
            f"Fetching entries as DataFrame "
            f"(topic_id={topic_id}, fetch_content={fetch_content})..."
        )

        try:
            # Use get_topic_entries which returns entries for specific topic
            entries_data = self.api_client.get_topic_entries(
                topic_id=topic_id,
                limit=DEFAULT_FETCH_LIMIT,  # Large limit to get all entries for one topic
            )

            # Extract metadata fields from extracted_metadata
            entries_data = [self._extract_metadata_fields(entry) for entry in entries_data]

            # Convert to DataFrame
            # Note: API returns 'published_date', we'll map it to 'published_at' after
            expected_columns = [
                "id",
                "title",
                "link",
                "content_markdown",
                "feed_id",
                "topic_id",
                "content_status",
                "content_timestamp",
                "s3_content_md_path",
                "s3_content_html_path",
                "s3_aggregated_content_md_path",
                "published_date",
                "created_at",
                "is_active",
            ]
            df = self._json_to_dataframe(entries_data, expected_columns)

            # Standardize column names - rename to use entry_ prefix
            # This ensures consistency with hierarchical views
            if "content_markdown" in df.columns:
                df = df.rename(columns={"content_markdown": "entry_content_markdown"})

            # Map published_date to published_at for consistency
            if "published_date" in df.columns:
                df["published_at"] = df["published_date"]
            else:
                # If no published_date, create empty published_at column for consistency
                logger.warning(
                    "No published_date field in API response, creating empty published_at"
                )
                df["published_at"] = pd.NaT

            # Convert date columns to datetime
            date_columns = ["published_at", "created_at", "content_timestamp"]
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            # Ensure is_active is boolean
            if "is_active" in df.columns:
                df["is_active"] = df["is_active"].fillna(True).astype(bool)

            # Fetch content from S3 if requested
            df = self._handle_s3_fetch(df, s3_client, fetch_content)

            logger.info(f"Successfully converted {len(df)} entries to DataFrame")
            return df

        except CarverAPIError as e:
            logger.error(f"Failed to fetch entries: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting entries to DataFrame: {e}")
            raise CarverAPIError(f"Data conversion failed: {e}") from e

    def get_hierarchical_view(
        self,
        topic_id: str,
        include_entries: bool = True,
        fetch_content: bool = False,
        s3_client: S3ContentClient | None = None,
    ) -> pd.DataFrame:
        """
        Construct denormalized hierarchical view: Topic → Entry.

        New in v0.2.0: Supports S3 content fetching with fetch_content parameter.

        Returns a single DataFrame with topic and entry relationships merged. This provides
        a flat view of the hierarchy where each row represents an entry (if
        include_entries=True) or just the topic (if include_entries=False), with all
        parent information included.

        Column naming convention:
        - topic_*: Columns from topics (topic_id, topic_name, topic_description)
        - entry_*: Columns from entries (entry_id, entry_title, entry_link, etc.)

        Args:
            topic_id: Topic ID to fetch data for (required)
            include_entries: If True, include entry data; if False, only topic metadata
            fetch_content: If True, fetch content from S3 (requires S3 credentials)
            s3_client: Optional S3ContentClient instance

        Returns:
            pd.DataFrame: Denormalized hierarchical view

        Raises:
            CarverAPIError: If API requests fail
            ValueError: If topic_id is not provided

        Example:
            >>> dm = create_data_manager()
            >>> # Get hierarchy for topic including entries (without content)
            >>> hierarchy = dm.get_hierarchical_view(topic_id="topic-123", include_entries=True)
            >>> # Get entries for topic with content
            >>> topic_hierarchy = dm.get_hierarchical_view(
            ...     topic_id="topic-123",
            ...     include_entries=True,
            ...     fetch_content=True
            ... )
        """
        if not topic_id:
            raise ValueError("topic_id is required")

        logger.info(
            f"Building hierarchical view "
            f"(topic_id={topic_id}, include_entries={include_entries})..."
        )

        try:
            # Fetch topic data
            topics_df = self.get_topics_df()

            # Filter to requested topic
            topics_df = topics_df[topics_df["id"] == topic_id]

            if len(topics_df) == 0:
                logger.warning(f"Topic {topic_id} not found")
                return pd.DataFrame()

            # Rename columns to avoid conflicts
            topics_df = topics_df.rename(
                columns={
                    "id": "topic_id",
                    "name": "topic_name",
                    "description": "topic_description",
                    "created_at": "topic_created_at",
                    "updated_at": "topic_updated_at",
                    "is_active": "topic_is_active",
                }
            )

            # If entries should be included, fetch and merge them
            if include_entries:
                # Fetch entries for the topic
                entries_df = self.get_topic_entries_df(
                    topic_id=topic_id,
                    fetch_content=fetch_content,
                    s3_client=s3_client
                )

                if len(entries_df) == 0:
                    logger.info(f"No entries found for topic {topic_id}")
                    return pd.DataFrame()

                # Rename entry columns (only rename if column exists)
                # Note: entry_content_markdown is already renamed in get_topic_entries_df
                rename_map = {}
                if "id" in entries_df.columns:
                    rename_map["id"] = "entry_id"
                if "title" in entries_df.columns:
                    rename_map["title"] = "entry_title"
                if "link" in entries_df.columns:
                    rename_map["link"] = "entry_link"
                if "published_at" in entries_df.columns:
                    rename_map["published_at"] = "entry_published_at"
                if "created_at" in entries_df.columns:
                    rename_map["created_at"] = "entry_created_at"
                if "is_active" in entries_df.columns:
                    rename_map["is_active"] = "entry_is_active"

                entries_df = entries_df.rename(columns=rename_map)

                # Merge topic info with entries
                hierarchy = pd.merge(topics_df, entries_df, on="topic_id", how="inner")

                logger.info(f"Built complete hierarchy with {len(hierarchy)} entries")
            else:
                # Just return topic metadata
                hierarchy = topics_df
                logger.info(f"Built topic-only hierarchy")

            logger.info(f"Successfully built hierarchical view with {len(hierarchy)} rows")
            return hierarchy

        except CarverAPIError as e:
            logger.error(f"Failed to build hierarchical view: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error building hierarchical view: {e}")
            raise CarverAPIError(f"Hierarchical view construction failed: {e}") from e

    def _handle_s3_fetch(
        self, df: pd.DataFrame, s3_client: S3ContentClient | None, fetch_content: bool
    ) -> pd.DataFrame:
        """
        Handle S3 content fetching logic with proper error handling.

        Args:
            df: DataFrame with s3_content_md_path column
            s3_client: Optional S3ContentClient instance
            fetch_content: Whether to fetch content

        Returns:
            DataFrame with entry_content_markdown populated or None
        """
        if not fetch_content:
            df["entry_content_markdown"] = None
            return df

        # Get or create S3 client
        if s3_client is None:
            s3_client = get_s3_client()
            if s3_client is None:
                logger.warning(
                    "Cannot fetch content: S3 credentials not configured. "
                    "Set AWS_PROFILE_NAME in .env. Content will be None."
                )
                df["entry_content_markdown"] = None
                return df

        # Fetch content from S3
        return self.fetch_contents_from_s3(df, s3_client)

    def _extract_metadata_fields(self, entry: dict) -> dict:
        """
        Extract fields from extracted_metadata to top level.

        Args:
            entry: Entry dictionary from API

        Returns:
            Entry dictionary with extracted metadata fields at top level
        """
        if "extracted_metadata" not in entry or entry["extracted_metadata"] is None:
            return entry

        meta = entry["extracted_metadata"]
        entry_copy = entry.copy()

        # Extract key metadata fields to top level
        # Use get() to handle missing fields gracefully
        entry_copy["feed_id"] = meta.get("feed_id", entry.get("feed_id"))
        entry_copy["topic_id"] = meta.get("topic_id")
        entry_copy["content_status"] = meta.get("status")
        entry_copy["content_timestamp"] = meta.get("timestamp")
        entry_copy["s3_content_md_path"] = meta.get("s3_content_md_path")
        entry_copy["s3_content_html_path"] = meta.get("s3_content_html_path")
        entry_copy["s3_aggregated_content_md_path"] = meta.get("s3_aggregated_content_md_path")

        # Keep full metadata as well (for advanced users)
        entry_copy["extracted_metadata_full"] = meta

        return entry_copy

    def fetch_contents_from_s3(self, df: pd.DataFrame, s3_client: S3ContentClient) -> pd.DataFrame:
        """
        Fetch content from S3 for all entries in DataFrame.

        This is a public method that can be used to fetch content from S3
        for entries in a DataFrame.

        Args:
            df: DataFrame with s3_content_md_path column
            s3_client: S3ContentClient instance

        Returns:
            DataFrame with entry_content_markdown column populated
        """
        if "s3_content_md_path" not in df.columns:
            logger.warning("No s3_content_md_path column found, cannot fetch content")
            df["entry_content_markdown"] = None
            return df

        # Get all S3 paths (filter out NaN)
        s3_paths = df["s3_content_md_path"].dropna().unique().tolist()

        if not s3_paths:
            logger.warning("No S3 paths found to fetch")
            df["entry_content_markdown"] = None
            return df

        logger.info(f"Fetching content for {len(s3_paths)} unique S3 paths...")

        # Batch fetch from S3 (parallel requests)
        content_map = s3_client.fetch_content_batch(s3_paths)

        # Map content back to DataFrame using standard column name
        df["entry_content_markdown"] = df["s3_content_md_path"].map(content_map)

        # Log fetch stats
        fetched_count = df["entry_content_markdown"].notna().sum()
        logger.info(f"Successfully fetched {fetched_count}/{len(df)} contents")

        return df

    def _json_to_dataframe(
        self, data: list[dict], expected_columns: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Convert API JSON response to pandas DataFrame with validation.

        This method handles:
        - Empty data lists (returns empty DataFrame with expected columns)
        - Missing fields (fills with None)
        - Extra fields (logs warning but keeps them)
        - Schema validation

        Args:
            data: List of dictionaries from API response
            expected_columns: Optional list of expected column names for validation

        Returns:
            pd.DataFrame: Converted data with validated schema

        Raises:
            ValueError: If data is not a list

        Example:
            >>> data = [{'id': '1', 'name': 'Test'}, {'id': '2', 'name': 'Test2'}]
            >>> df = manager._json_to_dataframe(data, expected_columns=['id', 'name'])
        """
        # Validate input
        if not isinstance(data, list):
            raise ValueError(f"Expected list of dictionaries, got {type(data).__name__}")

        # Handle empty data
        if len(data) == 0:
            logger.debug("Received empty data list")
            if expected_columns:
                return pd.DataFrame(columns=expected_columns)
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Log actual columns
        logger.debug(f"DataFrame columns: {list(df.columns)}")

        # Validate schema if expected columns provided
        if expected_columns:
            missing_columns = set(expected_columns) - set(df.columns)
            extra_columns = set(df.columns) - set(expected_columns)

            # Add missing columns with None values
            for col in missing_columns:
                logger.debug(f"Adding missing column: {col}")
                df[col] = None

            # Log extra columns (but keep them - they might be useful)
            if extra_columns:
                logger.info(f"Found extra columns (keeping them): {extra_columns}")

            # Reorder columns to match expected order (with extras at the end)
            ordered_cols = [col for col in expected_columns if col in df.columns]
            extra_cols = [col for col in df.columns if col not in expected_columns]
            df = df[ordered_cols + extra_cols]

        return df


def create_data_manager() -> FeedsDataManager:
    """
    Factory function to create FeedsDataManager with default API client.

    This is a convenience function that creates a data manager with
    an API client configured from environment variables.

    Environment Variables:
        CARVER_API_KEY: API key for authentication (required)
        CARVER_BASE_URL: Base URL for API (optional, defaults to production)

    Returns:
        FeedsDataManager: Configured data manager instance

    Raises:
        AuthenticationError: If CARVER_API_KEY is not set

    Example:
        >>> from carver_feeds import create_data_manager
        >>> dm = create_data_manager()
        >>> topics = dm.get_topics_df()
        >>> print(f"Found {len(topics)} topics")
    """
    api_client = get_client()
    return FeedsDataManager(api_client)
