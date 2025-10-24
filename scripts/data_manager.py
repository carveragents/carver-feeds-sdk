"""
Data Manager Module

This module handles converting API responses to pandas DataFrames
and building hierarchical views of the data.
"""

from typing import Dict, List, Optional, Any
import logging
import pandas as pd
from scripts.carver_api import CarverFeedsAPIClient, get_client, CarverAPIError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        >>> from scripts.data_manager import create_data_manager
        >>> dm = create_data_manager()
        >>> topics_df = dm.get_topics_df()
        >>> entries_df = dm.get_entries_df(fetch_all=True)
    """

    def __init__(self, api_client: CarverFeedsAPIClient):
        """Initialize with API client."""
        if not isinstance(api_client, CarverFeedsAPIClient):
            raise TypeError(
                "api_client must be an instance of CarverFeedsAPIClient"
            )
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
                'id', 'name', 'description',
                'created_at', 'updated_at', 'is_active'
            ]
            df = self._json_to_dataframe(topics_data, expected_columns)

            # Convert date columns to datetime
            date_columns = ['created_at', 'updated_at']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            # Ensure is_active is boolean
            if 'is_active' in df.columns:
                df['is_active'] = df['is_active'].fillna(True).astype(bool)

            logger.info(f"Successfully converted {len(df)} topics to DataFrame")
            return df

        except CarverAPIError as e:
            logger.error(f"Failed to fetch topics: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting topics to DataFrame: {e}")
            raise CarverAPIError(f"Data conversion failed: {e}") from e

    def get_feeds_df(self, topic_id: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch feeds and return as DataFrame.

        Returns a DataFrame with the following columns:
        - id: Feed ID
        - name: Feed name
        - url: Feed URL
        - topic_id: Associated topic ID (foreign key to topics.id) - extracted from topic object
        - topic_name: Associated topic name - extracted from topic object
        - description: Feed description
        - created_at: Creation timestamp
        - is_active: Active status

        Note: The API returns topic as a nested object {id, name}, which is flattened
        to topic_id and topic_name columns.

        Args:
            topic_id: Optional topic ID to filter feeds

        Returns:
            pd.DataFrame: Feeds with standardized schema

        Raises:
            CarverAPIError: If API request fails

        Example:
            >>> dm = create_data_manager()
            >>> # Get all feeds
            >>> feeds = dm.get_feeds_df()
            >>> # Get feeds for specific topic
            >>> banking_feeds = dm.get_feeds_df(topic_id="topic-123")
            >>> print(feeds[['id', 'name', 'topic_id', 'is_active']].head())
        """
        logger.info(
            f"Fetching feeds as DataFrame"
            f"{f' for topic {topic_id}' if topic_id else ''}..."
        )

        try:
            # Fetch data from API
            feeds_data = self.api_client.list_feeds(topic_id=topic_id)

            # Flatten topic object before conversion
            for feed in feeds_data:
                if 'topic' in feed and isinstance(feed['topic'], dict):
                    feed['topic_id'] = feed['topic'].get('id')
                    feed['topic_name'] = feed['topic'].get('name')

            # Convert to DataFrame
            expected_columns = [
                'id', 'name', 'url', 'topic_id', 'topic_name',
                'description', 'created_at', 'is_active'
            ]
            df = self._json_to_dataframe(feeds_data, expected_columns)

            # Convert date columns to datetime
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

            # Ensure is_active is boolean
            if 'is_active' in df.columns:
                df['is_active'] = df['is_active'].fillna(True).astype(bool)

            logger.info(f"Successfully converted {len(df)} feeds to DataFrame")
            return df

        except CarverAPIError as e:
            logger.error(f"Failed to fetch feeds: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting feeds to DataFrame: {e}")
            raise CarverAPIError(f"Data conversion failed: {e}") from e

    def get_entries_df(
        self,
        feed_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        fetch_all: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch entries and return as DataFrame with automatic pagination.

        Returns a DataFrame with the following columns:
        - id: Entry ID
        - title: Entry title
        - link: Entry URL/link
        - content_markdown: Full content in markdown format (primary search field)
        - feed_id: Associated feed ID (foreign key to feeds.id) - only when feed_id or topic_id is specified
        - published_at: Publication timestamp (uses published_date from API)
        - created_at: Creation timestamp
        - is_active: Active status

        Note: Supports three modes:
        1. feed_id specified: Uses /api/v1/feeds/{feed_id}/entries (fastest for single feed)
        2. topic_id specified: Uses /api/v1/feeds/topics/{topic_id}/entries (fast for single topic)
        3. Neither specified: Uses /api/v1/feeds/entries/list (fetches all entries)

        Args:
            feed_id: Optional feed ID to filter entries
            topic_id: Optional topic ID to filter entries (ignored if feed_id is specified)
            is_active: Optional filter for active status
            fetch_all: If True, fetch all pages; if False, fetch only first page

        Returns:
            pd.DataFrame: Entries with standardized schema

        Raises:
            CarverAPIError: If API request fails

        Example:
            >>> dm = create_data_manager()
            >>> # Get all entries (all pages, no feed_id in response)
            >>> all_entries = dm.get_entries_df(fetch_all=True)
            >>> # Get entries for a specific feed (includes feed_id)
            >>> feed_entries = dm.get_entries_df(feed_id="feed-123")
            >>> # Get entries for a specific topic (includes feed_id)
            >>> topic_entries = dm.get_entries_df(topic_id="topic-123")
        """
        logger.info(
            f"Fetching entries as DataFrame "
            f"(feed_id={feed_id}, topic_id={topic_id}, is_active={is_active}, fetch_all={fetch_all})..."
        )

        try:
            # Use different endpoint based on what's specified
            if feed_id:
                # Use get_feed_entries which returns entries for specific feed
                entries_data = self.api_client.get_feed_entries(
                    feed_id=feed_id,
                    limit=1000  # Large limit to get all entries for one feed
                )
                # Add feed_id to each entry since endpoint doesn't include it
                entries_data = [dict(entry, feed_id=feed_id) for entry in entries_data]
            elif topic_id:
                # Use get_topic_entries which returns entries for specific topic
                entries_data = self.api_client.get_topic_entries(
                    topic_id=topic_id,
                    limit=1000  # Large limit to get all entries for one topic
                )
                # Note: topic endpoint returns entries with feed_id already included
            else:
                # Use list_entries for all entries (does not include feed_id)
                entries_data = self.api_client.list_entries(
                    feed_id=None,
                    is_active=is_active,
                    fetch_all=fetch_all
                )

            # Convert to DataFrame
            expected_columns = [
                'id', 'title', 'link', 'content_markdown',
                'feed_id', 'published_at', 'created_at', 'is_active'
            ]
            df = self._json_to_dataframe(entries_data, expected_columns)

            # Map published_date to published_at if it exists
            if 'published_date' in df.columns:
                if 'published_at' not in df.columns or df['published_at'].isna().all():
                    df['published_at'] = df['published_date']

            # Convert date columns to datetime
            date_columns = ['published_at', 'created_at']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            # Ensure is_active is boolean
            if 'is_active' in df.columns:
                df['is_active'] = df['is_active'].fillna(True).astype(bool)

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
        include_entries: bool = True,
        feed_id: Optional[str] = None,
        topic_id: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Construct denormalized hierarchical view: Topic → Feed → Entry.

        Returns a single DataFrame with all relationships merged. This provides
        a flat view of the hierarchy where each row represents an entry (if
        include_entries=True) or a feed (if include_entries=False), with all
        parent information included.

        Column naming convention:
        - topic_*: Columns from topics (topic_id, topic_name, topic_description)
        - feed_*: Columns from feeds (feed_id, feed_name, feed_url)
        - entry_*: Columns from entries (entry_id, entry_title, entry_link, etc.)

        Args:
            include_entries: If True, include entry data; if False, only topics and feeds
            feed_id: Optional feed ID to filter results (most specific)
            topic_id: Optional topic ID to filter results (ignored if feed_id specified)

        Returns:
            pd.DataFrame: Denormalized hierarchical view

        Raises:
            CarverAPIError: If API requests fail

        Example:
            >>> dm = create_data_manager()
            >>> # Get full hierarchy including entries
            >>> hierarchy = dm.get_hierarchical_view(include_entries=True)
            >>> # Get entries for a specific feed
            >>> feed_hierarchy = dm.get_hierarchical_view(include_entries=True, feed_id="feed-123")
            >>> # Get entries for a specific topic
            >>> topic_hierarchy = dm.get_hierarchical_view(include_entries=True, topic_id="topic-123")
        """
        logger.info(
            f"Building hierarchical view "
            f"(include_entries={include_entries}, feed_id={feed_id}, topic_id={topic_id})..."
        )

        try:
            # Fetch all data
            topics_df = self.get_topics_df()
            feeds_df = self.get_feeds_df(topic_id=None)

            # Rename columns to avoid conflicts
            topics_df = topics_df.rename(columns={
                'id': 'topic_id',
                'name': 'topic_name',
                'description': 'topic_description',
                'created_at': 'topic_created_at',
                'updated_at': 'topic_updated_at',
                'is_active': 'topic_is_active'
            })

            feeds_df = feeds_df.rename(columns={
                'id': 'feed_id',
                'name': 'feed_name',
                'url': 'feed_url',
                'description': 'feed_description',
                'created_at': 'feed_created_at',
                'is_active': 'feed_is_active'
            })

            # Drop topic_name from feeds_df to avoid duplication (keep topic_id for join)
            # The topic_name from topics_df will be used after merge
            if 'topic_name' in feeds_df.columns:
                feeds_df = feeds_df.drop(columns=['topic_name'])

            # Merge topics and feeds
            hierarchy = pd.merge(
                topics_df,
                feeds_df,
                on='topic_id',
                how='inner'
            )

            # Apply feed_id or topic_id filter if specified
            if feed_id:
                hierarchy = hierarchy[hierarchy['feed_id'] == feed_id]
            elif topic_id:
                hierarchy = hierarchy[hierarchy['topic_id'] == topic_id]

            # If entries should be included, fetch and merge them
            if include_entries:
                entries_df = self.get_entries_df(
                    feed_id=feed_id,
                    topic_id=topic_id if not feed_id else None,  # Only use topic_id if feed_id not specified
                    fetch_all=True
                )

                entries_df = entries_df.rename(columns={
                    'id': 'entry_id',
                    'title': 'entry_title',
                    'link': 'entry_link',
                    'content_markdown': 'entry_content_markdown',
                    'published_at': 'entry_published_at',
                    'created_at': 'entry_created_at',
                    'is_active': 'entry_is_active'
                })

                # Merge strategy depends on whether we have feed_id in entries
                if 'feed_id' in entries_df.columns and not entries_df['feed_id'].isna().all():
                    # Standard case: merge on feed_id
                    hierarchy = pd.merge(
                        hierarchy,
                        entries_df,
                        on='feed_id',
                        how='inner'
                    )
                elif topic_id and not feed_id:
                    # Topic-only case: entries don't have feed_id
                    # Add topic information directly to entries (skip feeds)
                    logger.info("Topic entries don't have feed_id, creating simplified topic+entries view")

                    # Filter topics to just the one we want
                    topic_row = topics_df[topics_df['topic_id'] == topic_id]

                    if len(topic_row) > 0 and len(entries_df) > 0:
                        # Copy entries_df to avoid modifying the original
                        hierarchy = entries_df.copy()

                        # Get topic values
                        topic_dict = topic_row.iloc[0].to_dict()

                        # Add topic columns to each entry
                        # Handle list/array values specially to avoid length mismatch errors
                        for col, value in topic_dict.items():
                            # Convert lists/arrays to string representation for safety
                            if isinstance(value, (list, tuple)):
                                hierarchy[col] = str(value)
                            else:
                                hierarchy[col] = value

                        # Add placeholder feed columns (empty strings)
                        hierarchy['feed_id'] = ''
                        hierarchy['feed_name'] = ''
                        hierarchy['feed_url'] = ''
                    else:
                        # No topic found or no entries, return empty
                        hierarchy = pd.DataFrame()
                else:
                    # No feed_id and no specific topic_id filter
                    # This shouldn't happen, but handle gracefully
                    logger.warning("Entries have no feed_id and no topic_id filter specified")
                    hierarchy = pd.DataFrame()

            logger.info(
                f"Successfully built hierarchical view with {len(hierarchy)} rows"
            )
            return hierarchy

        except CarverAPIError as e:
            logger.error(f"Failed to build hierarchical view: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error building hierarchical view: {e}")
            raise CarverAPIError(f"Hierarchical view construction failed: {e}") from e

    def _json_to_dataframe(
        self,
        data: List[Dict],
        expected_columns: Optional[List[str]] = None
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
            raise ValueError(
                f"Expected list of dictionaries, got {type(data).__name__}"
            )

        # Handle empty data
        if len(data) == 0:
            logger.warning("Received empty data list")
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
                logger.warning(f"Adding missing column: {col}")
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
        >>> from scripts.data_manager import create_data_manager
        >>> dm = create_data_manager()
        >>> topics = dm.get_topics_df()
        >>> print(f"Found {len(topics)} topics")
    """
    api_client = get_client()
    return FeedsDataManager(api_client)
