"""
Carver Feeds API Client Module

This module provides a client for interacting with the Carver Feeds API.
Handles authentication, pagination, retry logic, and error handling.

Example:
    Basic usage with environment variables:

    >>> from carver_feeds import get_client
    >>> client = get_client()
    >>> topics = client.list_topics()

    Direct instantiation:

    >>> from carver_feeds import CarverFeedsAPIClient
    >>> client = CarverFeedsAPIClient(
    ...     base_url="https://app.carveragents.ai",
    ...     api_key="your-api-key"
    ... )
    >>> feeds = client.list_feeds()
"""

from typing import Dict, List, Optional, Any
import os
import time
import random
import logging
import requests
from dotenv import load_dotenv


# Configure module logger (library should not configure logging)
logger = logging.getLogger(__name__)


# API Configuration Constants
DEFAULT_BASE_URL = "https://app.carveragents.ai"
DEFAULT_PAGE_LIMIT = 1000
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30
RETRY_BACKOFF_FACTOR = 2


class CarverAPIError(Exception):
    """Base exception for Carver API errors."""
    pass


class AuthenticationError(CarverAPIError):
    """Raised when authentication fails."""
    pass


class RateLimitError(CarverAPIError):
    """Raised when rate limit is exceeded."""
    pass


class CarverFeedsAPIClient:
    """
    Client for interacting with the Carver Feeds API.

    Features:
    - Authentication via X-API-Key header
    - Automatic pagination handling
    - Exponential backoff retry logic for 429/500 errors
    - Comprehensive error handling

    Args:
        base_url: Base URL for the Carver API (e.g., DEFAULT_BASE_URL)
        api_key: API key for authentication
        max_retries: Maximum number of retries for failed requests (default: DEFAULT_MAX_RETRIES)
        initial_retry_delay: Initial delay in seconds for retry backoff
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_retry_delay: float = 1.0
    ):
        """Initialize client with base URL and API key."""
        if not base_url:
            raise ValueError("base_url is required")
        if not api_key:
            raise AuthenticationError(
                "API key is required. Please set CARVER_API_KEY environment variable "
                "or provide api_key parameter. See .env.example for configuration."
            )

        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            retry_count: Current retry attempt number

        Returns:
            JSON response as dictionary

        Raises:
            AuthenticationError: When authentication fails (401)
            RateLimitError: When rate limit exceeded after retries (429)
            CarverAPIError: For other API errors
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=DEFAULT_TIMEOUT_SECONDS
            )

            # Handle different status codes
            if response.status_code == 200:
                return response.json()

            elif response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Please check your API key. "
                    "Ensure CARVER_API_KEY is set correctly in your .env file."
                )

            elif response.status_code == 429:
                # Rate limit - retry with exponential backoff
                if retry_count < self.max_retries:
                    delay = self._calculate_backoff_delay(retry_count)
                    logger.warning(
                        f"Rate limit exceeded. Retrying in {delay:.2f}s "
                        f"(attempt {retry_count + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    return self._make_request(method, endpoint, params, retry_count + 1)
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {self.max_retries} retries. "
                        "Please wait before making more requests."
                    )

            elif response.status_code >= 500:
                # Server error - retry with exponential backoff
                if retry_count < self.max_retries:
                    delay = self._calculate_backoff_delay(retry_count)
                    logger.warning(
                        f"Server error ({response.status_code}). Retrying in {delay:.2f}s "
                        f"(attempt {retry_count + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    return self._make_request(method, endpoint, params, retry_count + 1)
                else:
                    raise CarverAPIError(
                        f"Server error ({response.status_code}) after {self.max_retries} retries. "
                        f"Response: {response.text}"
                    )

            else:
                # Other errors
                raise CarverAPIError(
                    f"API request failed with status {response.status_code}. "
                    f"Response: {response.text}"
                )

        except requests.exceptions.ConnectionError as e:
            raise CarverAPIError(
                f"Connection error: Could not connect to {url}. "
                "Please check your internet connection and verify the base URL."
            ) from e

        except requests.exceptions.Timeout as e:
            raise CarverAPIError(
                f"Request timeout: The server took too long to respond. "
                "Please try again later."
            ) from e

        except requests.exceptions.RequestException as e:
            raise CarverAPIError(
                f"Request failed: {str(e)}"
            ) from e

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            retry_count: Current retry attempt number

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (RETRY_BACKOFF_FACTOR ^ retry_count)
        delay = self.initial_retry_delay * (RETRY_BACKOFF_FACTOR ** retry_count)
        # Add jitter: random value between 0 and 25% of delay
        jitter = random.uniform(0, delay * 0.25)
        return delay + jitter

    def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = DEFAULT_PAGE_LIMIT,
        fetch_all: bool = True
    ) -> List[Dict]:
        """
        Handle pagination for list endpoints using limit/offset pattern.

        Args:
            endpoint: API endpoint path
            params: Base query parameters
            limit: Number of records per page
            fetch_all: If True, fetch all pages; if False, fetch only first page

        Returns:
            List of all records across pages
        """
        if params is None:
            params = {}

        all_results = []
        offset = 0

        while True:
            # Set pagination parameters
            page_params = {**params, 'limit': limit, 'offset': offset}

            # Fetch page
            response = self._make_request('GET', endpoint, page_params)

            # Extract results - handle different response formats
            if isinstance(response, list):
                results = response
            elif isinstance(response, dict):
                # Try common pagination result keys
                results = response.get('results', response.get('data', response.get('items', [])))
            else:
                results = []

            all_results.extend(results)

            # Check if we should continue
            if not fetch_all or len(results) < limit:
                break

            offset += limit
            logger.info(f"Fetched {len(all_results)} records so far...")

        logger.info(f"Total records fetched: {len(all_results)}")
        return all_results

    def list_topics(self) -> List[Dict]:
        """
        Fetch all topics from /api/v1/feeds/topics.

        Returns:
            List of topic dictionaries

        Example:
            >>> from carver_feeds import get_client
            >>> client = get_client()
            >>> topics = client.list_topics()
            >>> print(f"Found {len(topics)} topics")
        """
        logger.info("Fetching topics...")
        return self._make_request('GET', '/api/v1/feeds/topics')

    def list_feeds(self) -> List[Dict]:
        """
        Fetch all feeds from /api/v1/feeds/.

        Note: This endpoint does not support filtering by topic_id despite what
        the API documentation may suggest. Use client-side filtering instead.

        Returns:
            List of feed dictionaries

        Example:
            >>> from carver_feeds import get_client
            >>> client = get_client()
            >>> feeds = client.list_feeds()
            >>> # Filter client-side by topic_id
            >>> banking_feeds = [f for f in feeds if f.get('topic', {}).get('id') == 'topic-123']
        """
        logger.info("Fetching all feeds...")
        return self._make_request('GET', '/api/v1/feeds/')

    def list_entries(
        self,
        feed_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = DEFAULT_PAGE_LIMIT,
        fetch_all: bool = False
    ) -> List[Dict]:
        """
        Fetch entries from /api/v1/feeds/entries/list with pagination.

        Args:
            feed_id: Optional feed ID to filter entries
            is_active: Optional filter for active status
            limit: Number of records per page (default: 50)
            fetch_all: If True, fetch all pages; if False, fetch only first page

        Returns:
            List of entry dictionaries

        Example:
            >>> from carver_feeds import get_client
            >>> client = get_client()
            >>> # Fetch all entries (paginated)
            >>> all_entries = client.list_entries(fetch_all=True)
            >>> # Fetch only active entries for a specific feed
            >>> feed_entries = client.list_entries(
            ...     feed_id="feed-123",
            ...     is_active=True,
            ...     fetch_all=True
            ... )
        """
        params = {}
        if feed_id:
            params['feed_id'] = feed_id
        if is_active is not None:
            params['is_active'] = is_active

        logger.info(
            f"Fetching entries "
            f"(feed_id={feed_id}, is_active={is_active}, fetch_all={fetch_all})..."
        )
        return self._paginate('/api/v1/feeds/entries/list', params, limit, fetch_all)

    def get_feed_entries(self, feed_id: str, limit: int = DEFAULT_PAGE_LIMIT) -> List[Dict]:
        """
        Get entries for specific feed from /api/v1/feeds/{feed_id}/entries.

        Args:
            feed_id: Feed ID
            limit: Maximum number of entries to return

        Returns:
            List of entry dictionaries

        Example:
            >>> from carver_feeds import get_client
            >>> client = get_client()
            >>> entries = client.get_feed_entries("feed-123", limit=50)
        """
        if not feed_id:
            raise ValueError("feed_id is required")

        logger.info(f"Fetching entries for feed {feed_id}...")
        params = {'limit': limit}
        response = self._make_request('GET', f'/api/v1/feeds/{feed_id}/entries', params)

        # Extract items from response if it's a dict, otherwise return as-is
        if isinstance(response, dict):
            return response.get('items', [])
        return response

    def get_topic_entries(self, topic_id: str, limit: int = DEFAULT_PAGE_LIMIT) -> List[Dict]:
        """
        Get entries for a specific topic.

        This endpoint fetches all entries across all feeds that belong to
        the specified topic.

        Args:
            topic_id: Topic identifier (required)
            limit: Maximum number of entries to return (default: 100)

        Returns:
            List of entry dictionaries

        Raises:
            ValueError: If topic_id is not provided

        Example:
            >>> from carver_feeds import get_client
            >>> client = get_client()
            >>> entries = client.get_topic_entries("topic-123", limit=50)
        """
        if not topic_id:
            raise ValueError("topic_id is required")

        logger.info(f"Fetching entries for topic {topic_id}...")
        params = {'limit': limit}
        response = self._make_request('GET', f'/api/v1/feeds/topics/{topic_id}/entries', params)

        # Extract items from response if it's a dict, otherwise return as-is
        if isinstance(response, dict):
            return response.get('items', [])
        return response


def get_client(load_from_env: bool = True) -> CarverFeedsAPIClient:
    """
    Factory function to create API client from environment variables.

    Loads configuration from .env file and creates a CarverFeedsAPIClient instance.

    Args:
        load_from_env: If True, automatically load from .env file (default: True)

    Environment Variables:
        CARVER_API_KEY: API key for authentication (required)
        CARVER_BASE_URL: Base URL for API (optional, defaults to production)

    Returns:
        Configured CarverFeedsAPIClient instance

    Raises:
        AuthenticationError: If CARVER_API_KEY is not set

    Example:
        >>> # Create .env file with CARVER_API_KEY=your_key_here
        >>> from carver_feeds import get_client
        >>> client = get_client()
        >>> topics = client.list_topics()
    """
    # Load environment variables from .env file if requested
    if load_from_env:
        load_dotenv()

    api_key = os.getenv('CARVER_API_KEY')
    base_url = os.getenv('CARVER_BASE_URL', DEFAULT_BASE_URL)

    if not api_key:
        raise AuthenticationError(
            "CARVER_API_KEY environment variable is not set. "
            "Please create a .env file with your API key. "
            "See .env.example for reference."
        )

    logger.info(f"Initializing Carver API client with base URL: {base_url}")
    return CarverFeedsAPIClient(base_url=base_url, api_key=api_key)
