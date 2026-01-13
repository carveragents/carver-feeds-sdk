"""
Tests for carver_api module.

This module tests the CarverFeedsAPIClient class and related functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from carver_feeds.carver_api import (
    CarverFeedsAPIClient,
    get_client,
    CarverAPIError,
    AuthenticationError,
    RateLimitError,
)


class TestCarverFeedsAPIClient:
    """Tests for CarverFeedsAPIClient class."""

    def test_initialization_requires_base_url(self):
        """Test that initialization requires base_url."""
        with pytest.raises(ValueError, match="base_url is required"):
            CarverFeedsAPIClient(base_url="", api_key="test-key")

    def test_initialization_requires_api_key(self):
        """Test that initialization requires api_key."""
        with pytest.raises(AuthenticationError, match="API key is required"):
            CarverFeedsAPIClient(base_url="https://test.com", api_key="")

    def test_successful_initialization(self):
        """Test successful client initialization."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        assert client.base_url == "https://test.com"
        assert client.api_key == "test-key"
        assert client.session.headers["X-API-Key"] == "test-key"

    def test_base_url_strips_trailing_slash(self):
        """Test that trailing slashes are removed from base_url."""
        client = CarverFeedsAPIClient(base_url="https://test.com/", api_key="test-key")
        assert client.base_url == "https://test.com"


class TestGetClient:
    """Tests for get_client factory function."""

    @patch("carver_feeds.carver_api.load_dotenv")
    @patch.dict("os.environ", {"CARVER_API_KEY": "test-key", "CARVER_BASE_URL": "https://test.com"})
    def test_get_client_from_environment(self, mock_load_dotenv):
        """Test creating client from environment variables."""
        client = get_client()
        assert isinstance(client, CarverFeedsAPIClient)
        assert client.api_key == "test-key"
        assert client.base_url == "https://test.com"
        mock_load_dotenv.assert_called_once()

    @patch("carver_feeds.carver_api.load_dotenv")
    @patch.dict("os.environ", {}, clear=True)
    def test_get_client_without_api_key_raises_error(self, mock_load_dotenv):
        """Test that get_client raises error when API key is not set."""
        with pytest.raises(AuthenticationError, match="CARVER_API_KEY"):
            get_client()

    @patch("carver_feeds.carver_api.load_dotenv")
    @patch.dict("os.environ", {"CARVER_API_KEY": "test-key"})
    def test_get_client_uses_default_base_url(self, mock_load_dotenv):
        """Test that get_client uses default base URL when not specified."""
        client = get_client()
        assert client.base_url == "https://app.carveragents.ai"

    @patch.dict("os.environ", {"CARVER_API_KEY": "test-key"})
    def test_get_client_skip_dotenv_loading(self):
        """Test that get_client can skip dotenv loading."""
        client = get_client(load_from_env=False)
        assert isinstance(client, CarverFeedsAPIClient)


class TestGetUserTopicSubscriptions:
    """Tests for get_user_topic_subscriptions method."""

    def test_get_user_topic_subscriptions_requires_user_id(self):
        """Test that get_user_topic_subscriptions requires user_id parameter."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="user_id is required"):
            client.get_user_topic_subscriptions(user_id="")

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_user_topic_subscriptions_success(self, mock_make_request, sample_user_subscriptions):
        """Test successful user topic subscriptions retrieval."""
        mock_make_request.return_value = sample_user_subscriptions

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_user_topic_subscriptions(user_id="user-123")

        assert isinstance(result, dict)
        assert "subscriptions" in result
        assert "total_count" in result
        assert len(result["subscriptions"]) == 2
        assert result["total_count"] == 2

        # Verify the correct endpoint was called
        mock_make_request.assert_called_once_with(
            "GET", "/api/v1/core/users/user-123/topics/subscriptions"
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_user_topic_subscriptions_validates_response_structure(self, mock_make_request):
        """Test that get_user_topic_subscriptions validates response structure."""
        # Test with non-dict response
        mock_make_request.return_value = []

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Unexpected response format"):
            client.get_user_topic_subscriptions(user_id="user-123")

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_user_topic_subscriptions_validates_subscriptions_field(self, mock_make_request):
        """Test that get_user_topic_subscriptions validates subscriptions field presence."""
        # Test with dict missing 'subscriptions' field
        mock_make_request.return_value = {"total_count": 0}

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Response missing 'subscriptions' field"):
            client.get_user_topic_subscriptions(user_id="user-123")

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_user_topic_subscriptions_empty_list(self, mock_make_request):
        """Test get_user_topic_subscriptions with empty subscriptions list."""
        mock_make_request.return_value = {"subscriptions": [], "total_count": 0}

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_user_topic_subscriptions(user_id="user-123")

        assert result["subscriptions"] == []
        assert result["total_count"] == 0


# Additional tests can be added here for:
# - _make_request method
# - _paginate method
# - list_topics, list_feeds, list_entries methods
# - get_feed_entries, get_topic_entries methods
# - Error handling and retry logic
