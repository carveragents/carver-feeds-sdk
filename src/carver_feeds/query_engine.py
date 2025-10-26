"""
Query Engine Module

This module provides search and filtering capabilities for feed entries.
Implements a fluent interface pattern for method chaining.

Example:
    >>> from carver_feeds import create_query_engine
    >>> from datetime import datetime
    >>> qe = create_query_engine()
    >>> results = qe.filter_by_topic(topic_name="Banking") \\
    ...     .filter_by_date(start_date=datetime(2024, 1, 1)) \\
    ...     .search_entries(["regulation", "compliance"]) \\
    ...     .to_dataframe()
"""

from typing import List, Optional, Union
from datetime import datetime
import logging
import pandas as pd
from carver_feeds.data_manager import FeedsDataManager, create_data_manager


# Configure module logger (library should not configure logging)
logger = logging.getLogger(__name__)


# Query Engine Configuration Constants
DEFAULT_SEARCH_FIELD = "entry_content_markdown"


class EntryQueryEngine:
    """
    Engine for querying and filtering feed entries.

    This class provides a fluent interface for searching and filtering
    entries from the Carver Feeds API. Methods can be chained together
    to build complex queries.

    Features:
    - Keyword search across multiple fields (title, description, content_markdown)
    - Filter by topic (id or name)
    - Filter by feed (id or name)
    - Filter by date range
    - Filter by active status
    - Method chaining for complex queries
    - Multiple export formats (DataFrame, dict, JSON, CSV)

    Args:
        data_manager: FeedsDataManager instance for data fetching

    Example:
        >>> from carver_feeds import create_query_engine
        >>> from datetime import datetime
        >>> qe = create_query_engine()
        >>> results = qe \\
        ...     .filter_by_topic(topic_name="Banking") \\
        ...     .filter_by_date(start_date=datetime(2024, 1, 1)) \\
        ...     .search_entries(["regulation", "compliance"]) \\
        ...     .to_dataframe()
    """

    def __init__(self, data_manager: FeedsDataManager):
        """
        Initialize query engine with data manager.

        Args:
            data_manager: FeedsDataManager instance for fetching data

        Raises:
            TypeError: If data_manager is not a FeedsDataManager instance
        """
        if not isinstance(data_manager, FeedsDataManager):
            raise TypeError(
                "data_manager must be an instance of FeedsDataManager"
            )
        self.data_manager = data_manager
        self._results = None
        self._initial_data_loaded = False
        logger.info("EntryQueryEngine initialized")

    def _ensure_data_loaded(self):
        """
        Ensure data is loaded before applying filters.

        This lazy-loads the hierarchical view on first use to avoid
        unnecessary API calls during initialization.
        """
        if not self._initial_data_loaded:
            logger.info("Loading hierarchical data for query engine...")
            self._results = self.data_manager.get_hierarchical_view(include_entries=True)
            self._initial_data_loaded = True
            logger.info(f"Loaded {len(self._results)} entries for querying")

    def chain(self) -> 'EntryQueryEngine':
        """
        Reset query to start fresh with all data.

        This method allows you to start a new query chain while
        reusing the same query engine instance.

        Returns:
            EntryQueryEngine: Self for method chaining

        Example:
            >>> qe = create_query_engine()
            >>> # First query
            >>> results1 = qe.filter_by_topic(topic_name="Banking").to_dataframe()
            >>> # Reset and start new query
            >>> results2 = qe.chain().filter_by_feed(feed_name="SEC").to_dataframe()
        """
        logger.info("Resetting query chain to full dataset")
        self._initial_data_loaded = False
        self._results = None
        return self

    def search_entries(
        self,
        keywords: Union[str, List[str]],
        search_fields: Optional[List[str]] = None,
        case_sensitive: bool = False,
        match_all: bool = False
    ) -> 'EntryQueryEngine':
        """
        Search entries by keywords across specified fields.

        This method searches for keywords in the specified fields and returns
        matching entries. Supports both AND and OR logic for multiple keywords.

        Priority field (as per implementation-plan.md): DEFAULT_SEARCH_FIELD

        Args:
            keywords: Single keyword string or list of keywords to search for
            search_fields: List of field names to search in. Defaults to [DEFAULT_SEARCH_FIELD].
                          Can include: 'entry_title', 'entry_content_markdown', 'entry_link'
            case_sensitive: If True, perform case-sensitive search. Default: False
            match_all: If True, all keywords must match (AND logic).
                      If False, any keyword can match (OR logic). Default: False

        Returns:
            EntryQueryEngine: Self for method chaining

        Example:
            >>> qe = create_query_engine()
            >>> # Search for entries containing "regulation" OR "compliance"
            >>> results = qe.search_entries(
            ...     ["regulation", "compliance"],
            ...     match_all=False
            ... ).to_dataframe()
            >>> # Search for entries containing both "banking" AND "regulation"
            >>> results = qe.search_entries(
            ...     ["banking", "regulation"],
            ...     match_all=True
            ... ).to_dataframe()
        """
        self._ensure_data_loaded()

        # Use default search field if not provided
        if search_fields is None:
            search_fields = [DEFAULT_SEARCH_FIELD]

        # Convert single keyword to list
        if isinstance(keywords, str):
            keywords = [keywords]

        if not keywords:
            logger.warning("No keywords provided for search")
            return self

        logger.info(
            f"Searching for keywords: {keywords} "
            f"(match_all={match_all}, case_sensitive={case_sensitive})"
        )

        # Map user-friendly field names to actual column names in hierarchical view
        # The hierarchical view prefixes entry columns with 'entry_'
        field_mapping = {
            'title': 'entry_title',
            'content_markdown': 'entry_content_markdown',
            'link': 'entry_link',
            'description': 'entry_description',
            # Also support direct column names
            'entry_title': 'entry_title',
            'entry_content_markdown': 'entry_content_markdown',
            'entry_link': 'entry_link',
            'entry_description': 'entry_description',
        }

        # Map search fields to actual column names
        actual_fields = []
        for field in search_fields:
            if field in field_mapping:
                actual_fields.append(field_mapping[field])
            else:
                logger.warning(f"Unknown search field: {field}, skipping")

        if not actual_fields:
            logger.error("No valid search fields specified")
            return self

        # Build search mask
        if match_all:
            # AND logic: all keywords must match in at least one field
            combined_mask = pd.Series([True] * len(self._results), index=self._results.index)
            for keyword in keywords:
                keyword_mask = pd.Series([False] * len(self._results), index=self._results.index)
                for field in actual_fields:
                    if field in self._results.columns:
                        field_mask = self._results[field].fillna('').str.contains(
                            keyword,
                            case=case_sensitive,
                            na=False,
                            regex=True
                        )
                        keyword_mask = keyword_mask | field_mask
                combined_mask = combined_mask & keyword_mask
        else:
            # OR logic: any keyword can match in any field
            combined_mask = pd.Series([False] * len(self._results), index=self._results.index)
            for keyword in keywords:
                for field in actual_fields:
                    if field in self._results.columns:
                        field_mask = self._results[field].fillna('').str.contains(
                            keyword,
                            case=case_sensitive,
                            na=False,
                            regex=True
                        )
                        combined_mask = combined_mask | field_mask

        # Apply filter
        self._results = self._results[combined_mask]
        logger.info(f"Search returned {len(self._results)} entries")

        return self

    def filter_by_topic(
        self,
        topic_id: Optional[str] = None,
        topic_name: Optional[str] = None
    ) -> 'EntryQueryEngine':
        """
        Filter entries by topic (id or name).

        At least one of topic_id or topic_name must be provided.
        If both are provided, topic_id takes precedence.

        OPTIMIZED: When topic_id OR topic_name is provided and no data is loaded yet,
        this method uses the topic-specific endpoint to fetch only that topic's entries,
        avoiding the need to download all entries. For topic_name, it first resolves
        the name to topic_id(s) then fetches entries efficiently.

        Args:
            topic_id: Topic ID to filter by
            topic_name: Topic name to filter by (case-insensitive partial match)

        Returns:
            EntryQueryEngine: Self for method chaining

        Example:
            >>> qe = create_query_engine()
            >>> # Filter by topic ID (optimized - only fetches this topic's entries)
            >>> results = qe.filter_by_topic(topic_id="topic-123").to_dataframe()
            >>> # Filter by topic name (optimized - resolves name to ID first)
            >>> results = qe.filter_by_topic(topic_name="Banking").to_dataframe()
        """
        if not topic_id and not topic_name:
            logger.warning("Neither topic_id nor topic_name provided, no filtering applied")
            return self

        # OPTIMIZATION: If data not yet loaded, use topic-specific endpoint
        if not self._initial_data_loaded:
            if topic_id:
                # Direct topic_id lookup
                logger.info(f"Optimized filter: Loading only topic {topic_id} entries")
                self._results = self.data_manager.get_hierarchical_view(
                    include_entries=True,
                    topic_id=topic_id
                )
                self._initial_data_loaded = True
                logger.info(f"Loaded {len(self._results)} entries for topic {topic_id}")
                return self
            elif topic_name:
                # Resolve topic_name to topic_id(s) first, then fetch entries
                logger.info(f"Optimized filter: Looking up topic_id for topic_name '{topic_name}'")
                topics_df = self.data_manager.get_topics_df()

                # Find matching topics (case-insensitive partial match)
                mask = topics_df['name'].fillna('').str.contains(
                    topic_name,
                    case=False,
                    na=False
                )
                matching_topics = topics_df[mask]

                if len(matching_topics) == 0:
                    logger.warning(f"No topics found matching '{topic_name}'")
                    self._results = pd.DataFrame()
                    self._initial_data_loaded = True
                    return self

                # If single match, use optimized endpoint
                if len(matching_topics) == 1:
                    resolved_topic_id = matching_topics.iloc[0]['id']
                    topic_display_name = matching_topics.iloc[0]['name']
                    logger.info(f"Found single matching topic '{topic_display_name}' ({resolved_topic_id})")
                    self._results = self.data_manager.get_hierarchical_view(
                        include_entries=True,
                        topic_id=resolved_topic_id
                    )
                    self._initial_data_loaded = True
                    logger.info(f"Loaded {len(self._results)} entries for topic {resolved_topic_id}")
                    return self
                else:
                    # Multiple matches - fetch entries for each topic and combine
                    logger.info(f"Found {len(matching_topics)} matching topics, fetching entries for all")
                    all_entries = []
                    for _, topic in matching_topics.iterrows():
                        topic_entries = self.data_manager.get_hierarchical_view(
                            include_entries=True,
                            topic_id=topic['id']
                        )
                        all_entries.append(topic_entries)

                    if all_entries:
                        self._results = pd.concat(all_entries, ignore_index=True)
                    else:
                        self._results = pd.DataFrame()

                    self._initial_data_loaded = True
                    logger.info(f"Loaded {len(self._results)} entries across {len(matching_topics)} topics")
                    return self

        # Standard path: filter from already-loaded data
        self._ensure_data_loaded()

        if topic_id:
            logger.info(f"Filtering by topic_id: {topic_id}")
            self._results = self._results[self._results['topic_id'] == topic_id]
        elif topic_name:
            logger.info(f"Filtering by topic_name: {topic_name}")
            if 'topic_name' in self._results.columns:
                mask = self._results['topic_name'].fillna('').str.contains(
                    topic_name,
                    case=False,
                    na=False
                )
                self._results = self._results[mask]
            else:
                logger.warning("topic_name column not found in data")

        logger.info(f"Filter returned {len(self._results)} entries")
        return self

    def filter_by_feed(
        self,
        feed_id: Optional[str] = None,
        feed_name: Optional[str] = None
    ) -> 'EntryQueryEngine':
        """
        Filter entries by feed (id or name).

        At least one of feed_id or feed_name must be provided.
        If both are provided, feed_id takes precedence.

        OPTIMIZED: When feed_id OR feed_name is provided and no data is loaded yet,
        this method uses the feed-specific endpoint to fetch only that feed's entries,
        avoiding the need to download all entries. For feed_name, it first resolves
        the name to feed_id(s) then fetches entries efficiently.

        Args:
            feed_id: Feed ID to filter by
            feed_name: Feed name to filter by (case-insensitive partial match)

        Returns:
            EntryQueryEngine: Self for method chaining

        Example:
            >>> qe = create_query_engine()
            >>> # Filter by feed ID (optimized - only fetches this feed's entries)
            >>> results = qe.filter_by_feed(feed_id="feed-456").to_dataframe()
            >>> # Filter by feed name (optimized - resolves name to ID first)
            >>> results = qe.filter_by_feed(feed_name="SEC News").to_dataframe()
        """
        if not feed_id and not feed_name:
            logger.warning("Neither feed_id nor feed_name provided, no filtering applied")
            return self

        # OPTIMIZATION: If data not yet loaded, use feed-specific endpoint
        if not self._initial_data_loaded:
            if feed_id:
                # Direct feed_id lookup
                logger.info(f"Optimized filter: Loading only feed {feed_id} entries")
                self._results = self.data_manager.get_hierarchical_view(
                    include_entries=True,
                    feed_id=feed_id
                )
                self._initial_data_loaded = True
                logger.info(f"Loaded {len(self._results)} entries for feed {feed_id}")
                return self
            elif feed_name:
                # Resolve feed_name to feed_id(s) first, then fetch entries
                logger.info(f"Optimized filter: Looking up feed_id for feed_name '{feed_name}'")
                feeds_df = self.data_manager.get_feeds_df()

                # Find matching feeds (case-insensitive partial match)
                mask = feeds_df['name'].fillna('').str.contains(
                    feed_name,
                    case=False,
                    na=False
                )
                matching_feeds = feeds_df[mask]

                if len(matching_feeds) == 0:
                    logger.warning(f"No feeds found matching '{feed_name}'")
                    self._results = pd.DataFrame()
                    self._initial_data_loaded = True
                    return self

                # If single match, use optimized endpoint
                if len(matching_feeds) == 1:
                    resolved_feed_id = matching_feeds.iloc[0]['id']
                    feed_display_name = matching_feeds.iloc[0]['name']
                    logger.info(f"Found single matching feed '{feed_display_name}' ({resolved_feed_id})")
                    self._results = self.data_manager.get_hierarchical_view(
                        include_entries=True,
                        feed_id=resolved_feed_id
                    )
                    self._initial_data_loaded = True
                    logger.info(f"Loaded {len(self._results)} entries for feed {resolved_feed_id}")
                    return self
                else:
                    # Multiple matches - fetch entries for each feed and combine
                    logger.info(f"Found {len(matching_feeds)} matching feeds, fetching entries for all")
                    all_entries = []
                    for _, feed in matching_feeds.iterrows():
                        feed_entries = self.data_manager.get_hierarchical_view(
                            include_entries=True,
                            feed_id=feed['id']
                        )
                        all_entries.append(feed_entries)

                    if all_entries:
                        self._results = pd.concat(all_entries, ignore_index=True)
                    else:
                        self._results = pd.DataFrame()

                    self._initial_data_loaded = True
                    logger.info(f"Loaded {len(self._results)} entries across {len(matching_feeds)} feeds")
                    return self

        # Standard path: filter from already-loaded data
        self._ensure_data_loaded()

        if feed_id:
            logger.info(f"Filtering by feed_id: {feed_id}")
            self._results = self._results[self._results['feed_id'] == feed_id]
        elif feed_name:
            logger.info(f"Filtering by feed_name: {feed_name}")
            if 'feed_name' in self._results.columns:
                mask = self._results['feed_name'].fillna('').str.contains(
                    feed_name,
                    case=False,
                    na=False
                )
                self._results = self._results[mask]
            else:
                logger.warning("feed_name column not found in data")

        logger.info(f"Filter returned {len(self._results)} entries")
        return self

    def filter_by_date(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> 'EntryQueryEngine':
        """
        Filter entries by date range.

        Filters based on the entry's published_at timestamp. At least one of
        start_date or end_date should be provided.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            EntryQueryEngine: Self for method chaining

        Example:
            >>> from datetime import datetime
            >>> qe = create_query_engine()
            >>> # Filter entries from 2024 onwards
            >>> results = qe.filter_by_date(
            ...     start_date=datetime(2024, 1, 1)
            ... ).to_dataframe()
            >>> # Filter entries from a specific range
            >>> results = qe.filter_by_date(
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 12, 31)
            ... ).to_dataframe()
        """
        self._ensure_data_loaded()

        if not start_date and not end_date:
            logger.warning("Neither start_date nor end_date provided, no filtering applied")
            return self

        date_field = 'entry_published_at'
        if date_field not in self._results.columns:
            logger.warning(f"{date_field} column not found in data")
            return self

        # Ensure date column is datetime type
        if not pd.api.types.is_datetime64_any_dtype(self._results[date_field]):
            logger.info(f"Converting {date_field} to datetime")
            self._results[date_field] = pd.to_datetime(
                self._results[date_field],
                errors='coerce'
            )

        # Handle timezone awareness to avoid comparison errors
        # If the date column is timezone-aware and user dates are not, make user dates timezone-aware
        date_column = self._results[date_field]
        if hasattr(date_column.dtype, 'tz') and date_column.dtype.tz is not None:
            # Column is timezone-aware
            if start_date and start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=date_column.dtype.tz)
                logger.debug(f"Converted start_date to timezone-aware: {start_date}")
            if end_date and end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=date_column.dtype.tz)
                logger.debug(f"Converted end_date to timezone-aware: {end_date}")

        if start_date:
            logger.info(f"Filtering by start_date: {start_date}")
            self._results = self._results[self._results[date_field] >= start_date]

        if end_date:
            logger.info(f"Filtering by end_date: {end_date}")
            self._results = self._results[self._results[date_field] <= end_date]

        logger.info(f"Date filter returned {len(self._results)} entries")
        return self

    def filter_by_active(self, is_active: bool = True) -> 'EntryQueryEngine':
        """
        Filter entries by active status.

        Args:
            is_active: If True, return only active entries.
                      If False, return only inactive entries.

        Returns:
            EntryQueryEngine: Self for method chaining

        Example:
            >>> qe = create_query_engine()
            >>> # Get only active entries
            >>> results = qe.filter_by_active(is_active=True).to_dataframe()
            >>> # Get only inactive entries
            >>> results = qe.filter_by_active(is_active=False).to_dataframe()
        """
        self._ensure_data_loaded()

        logger.info(f"Filtering by is_active: {is_active}")

        active_field = 'entry_is_active'
        if active_field not in self._results.columns:
            logger.warning(f"{active_field} column not found in data")
            return self

        self._results = self._results[self._results[active_field] == is_active]
        logger.info(f"Active filter returned {len(self._results)} entries")

        return self

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return current results as DataFrame.

        Returns a copy of the results to prevent unintended modifications.

        Returns:
            pd.DataFrame: Current query results

        Example:
            >>> qe = create_query_engine()
            >>> df = qe.filter_by_topic(topic_name="Banking").to_dataframe()
            >>> print(df[['topic_name', 'feed_name', 'entry_title']].head())
        """
        self._ensure_data_loaded()
        logger.info(f"Returning {len(self._results)} entries as DataFrame")
        return self._results.copy()

    def to_dict(self) -> List[dict]:
        """
        Return current results as list of dictionaries.

        Each row in the DataFrame is converted to a dictionary.

        Returns:
            List[dict]: List of entry dictionaries

        Example:
            >>> qe = create_query_engine()
            >>> results = qe.filter_by_topic(topic_name="Banking").to_dict()
            >>> print(f"Found {len(results)} entries")
            >>> print(results[0].keys())  # Show available fields
        """
        self._ensure_data_loaded()
        logger.info(f"Returning {len(self._results)} entries as list of dicts")
        return self._results.to_dict('records')

    def to_json(self, indent: int = 2) -> str:
        """
        Return current results as JSON string.

        Args:
            indent: Number of spaces for JSON indentation (default: 2)

        Returns:
            str: JSON string representation of results

        Example:
            >>> qe = create_query_engine()
            >>> json_str = qe.filter_by_topic(topic_name="Banking").to_json()
            >>> print(json_str[:200])  # Print first 200 chars
        """
        self._ensure_data_loaded()
        logger.info(f"Returning {len(self._results)} entries as JSON")
        return self._results.to_json(orient='records', indent=indent, date_format='iso')

    def to_csv(self, filepath: str, index: bool = False) -> str:
        """
        Export current results to CSV file.

        Args:
            filepath: Path to output CSV file
            index: If True, include DataFrame index in CSV (default: False)

        Returns:
            str: Path to the created CSV file

        Example:
            >>> qe = create_query_engine()
            >>> filepath = qe.filter_by_topic(topic_name="Banking").to_csv("banking_entries.csv")
            >>> print(f"Exported to {filepath}")
        """
        self._ensure_data_loaded()
        logger.info(f"Exporting {len(self._results)} entries to CSV: {filepath}")
        self._results.to_csv(filepath, index=index)
        logger.info(f"Successfully exported to {filepath}")
        return filepath


def create_query_engine() -> EntryQueryEngine:
    """
    Factory function to create query engine with default data manager.

    This is a convenience function that creates a query engine with
    a data manager configured from environment variables.

    Environment Variables:
        CARVER_API_KEY: API key for authentication (required)
        CARVER_BASE_URL: Base URL for API (optional, defaults to production)

    Returns:
        EntryQueryEngine: Configured query engine instance

    Raises:
        AuthenticationError: If CARVER_API_KEY is not set

    Example:
        >>> from carver_feeds import create_query_engine
        >>> qe = create_query_engine()
        >>> results = qe.filter_by_topic(topic_name="Banking").to_dataframe()
    """
    data_manager = create_data_manager()
    return EntryQueryEngine(data_manager)
