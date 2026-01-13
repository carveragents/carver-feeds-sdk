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

import logging
import os
import random
import time
from typing import Any

import requests
from dotenv import load_dotenv

# Configure module logger (library should not configure logging)
logger = logging.getLogger(__name__)


# API Configuration Constants
DEFAULT_BASE_URL = "https://app.carveragents.ai"
DEFAULT_PAGE_LIMIT = 100  # API server enforces max 100 entries per page
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
        initial_retry_delay: float = 1.0,
    ):
        """Initialize client with base URL and API key."""
        if not base_url:
            raise ValueError("base_url is required")
        if not api_key:
            raise AuthenticationError(
                "API key is required. Please set CARVER_API_KEY environment variable "
                "or provide api_key parameter. See .env.example for configuration."
            )

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
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
                method=method, url=url, params=params, timeout=DEFAULT_TIMEOUT_SECONDS
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
                "Request timeout: The server took too long to respond. " "Please try again later."
            ) from e

        except requests.exceptions.RequestException as e:
            raise CarverAPIError(f"Request failed: {str(e)}") from e

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            retry_count: Current retry attempt number

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (RETRY_BACKOFF_FACTOR ^ retry_count)
        delay = self.initial_retry_delay * (RETRY_BACKOFF_FACTOR**retry_count)
        # Add jitter: random value between 0 and 25% of delay
        jitter = random.uniform(0, delay * 0.25)
        return delay + jitter

    def list_topics(self) -> list[dict]:
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
        return self._make_request("GET", "/api/v1/feeds/topics")

    def get_topic_entries(self, topic_id: str, limit: int = DEFAULT_PAGE_LIMIT) -> list[dict]:
        """
        Get entries for a specific topic.

        This endpoint fetches all entries across all feeds that belong to
        the specified topic.

        Note:
            The API server enforces a maximum page size of 100 entries.
            Requesting limit > 100 will return at most 100 entries.

        Args:
            topic_id: Topic identifier (required)
            limit: Maximum number of entries to return (default: 100, max: 100)

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
        params = {"limit": limit}
        response = self._make_request("GET", f"/api/v1/feeds/topics/{topic_id}/entries", params)

        # Extract items from response if it's a dict, otherwise return as-is
        if isinstance(response, dict):
            return response.get("items", [])
        return response

    def get_user_topic_subscriptions(self, user_id: str) -> dict[str, Any]:
        """
        Get topic subscriptions for a specific user.

        Fetches the list of topics that a user has subscribed to from
        /api/v1/core/users/{user_id}/topics/subscriptions.

        Args:
            user_id: User identifier (required)

        Returns:
            Dictionary with 'subscriptions' (list of topic dicts) and 'total_count' (int)

        Raises:
            ValueError: If user_id is not provided
            AuthenticationError: If authentication fails
            CarverAPIError: For other API errors

        Example:
            >>> from carver_feeds import get_client
            >>> client = get_client()
            >>> result = client.get_user_topic_subscriptions("user-123")
            >>> print(f"User has {result['total_count']} subscriptions")
            >>> for topic in result['subscriptions']:
            ...     print(f"- {topic['name']}")
        """
        if not user_id:
            raise ValueError("user_id is required")

        logger.info(f"Fetching topic subscriptions for user {user_id}...")
        endpoint = f"/api/v1/core/users/{user_id}/topics/subscriptions"
        response = self._make_request("GET", endpoint)

        # Validate response structure
        if not isinstance(response, dict):
            raise CarverAPIError(
                f"Unexpected response format. Expected dict, got {type(response).__name__}"
            )

        if "subscriptions" not in response:
            raise CarverAPIError(
                "Response missing 'subscriptions' field. " f"Response: {response}"
            )

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

    api_key = os.getenv("CARVER_API_KEY")
    base_url = os.getenv("CARVER_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        raise AuthenticationError(
            "CARVER_API_KEY environment variable is not set. "
            "Please create a .env file with your API key. "
            "See .env.example for reference."
        )

    logger.info(f"Initializing Carver API client with base URL: {base_url}")
    return CarverFeedsAPIClient(base_url=base_url, api_key=api_key)
