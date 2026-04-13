"""
Tests for carver_api module.

This module tests the CarverFeedsAPIClient class and related functionality.
"""

from unittest.mock import patch

import pytest

from carver_feeds.carver_api import (
    AuthenticationError,
    CarverAPIError,
    CarverFeedsAPIClient,
    get_client,
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
    def test_get_user_topic_subscriptions_success(
        self, mock_make_request, sample_user_subscriptions
    ):
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


class TestGetAnnotations:
    """Tests for get_annotations method."""

    def test_get_annotations_requires_at_least_one_filter(self):
        """Test that get_annotations requires at least one filter parameter."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="At least one filter must be provided"):
            client.get_annotations()

    def test_get_annotations_rejects_multiple_filters(self):
        """Test that get_annotations rejects multiple filter parameters."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="Only one filter can be used per request"):
            client.get_annotations(feed_entry_ids=["entry-1"], topic_ids=["topic-1"])

        with pytest.raises(ValueError, match="Only one filter can be used per request"):
            client.get_annotations(topic_ids=["topic-1"], user_ids=["user-1"])

        with pytest.raises(ValueError, match="Only one filter can be used per request"):
            client.get_annotations(feed_entry_ids=["entry-1"], user_ids=["user-1"])

        with pytest.raises(ValueError, match="Only one filter can be used per request"):
            client.get_annotations(
                feed_entry_ids=["entry-1"],
                topic_ids=["topic-1"],
                user_ids=["user-1"],
            )

    def test_get_annotations_rejects_empty_lists(self):
        """Test that get_annotations rejects empty filter lists."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="feed_entry_ids cannot be an empty list"):
            client.get_annotations(feed_entry_ids=[])

        with pytest.raises(ValueError, match="topic_ids cannot be an empty list"):
            client.get_annotations(topic_ids=[])

        with pytest.raises(ValueError, match="user_ids cannot be an empty list"):
            client.get_annotations(user_ids=[])

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_annotations_by_feed_entry_ids(self, mock_make_request, sample_annotations):
        """Test successful annotations retrieval by feed entry IDs."""
        mock_make_request.return_value = sample_annotations

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_annotations(feed_entry_ids=["entry-1", "entry-2"])

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["feed_entry_id"] == "entry-1"
        assert "annotation" in result[0]

        # Verify the correct endpoint and parameters were used
        mock_make_request.assert_called_once_with(
            "GET",
            "/api/v1/core/annotations",
            {"feed_entry_ids_in": "entry-1,entry-2"},
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_annotations_by_topic_ids(self, mock_make_request, sample_annotations):
        """Test successful annotations retrieval by topic IDs."""
        mock_make_request.return_value = sample_annotations

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_annotations(topic_ids=["topic-1"])

        assert isinstance(result, list)
        assert len(result) == 2

        # Verify the correct endpoint and parameters were used
        mock_make_request.assert_called_once_with(
            "GET", "/api/v1/core/annotations", {"topic_ids_in": "topic-1"}
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_annotations_by_user_ids(self, mock_make_request, sample_annotations):
        """Test successful annotations retrieval by user IDs."""
        mock_make_request.return_value = sample_annotations

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_annotations(user_ids=["user-1", "user-2"])

        assert isinstance(result, list)
        assert len(result) == 2

        # Verify the correct endpoint and parameters were used
        mock_make_request.assert_called_once_with(
            "GET",
            "/api/v1/core/annotations",
            {"user_ids_in": "user-1,user-2"},
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_annotations_validates_response_is_list(self, mock_make_request):
        """Test that get_annotations validates response is a list."""
        # Test with non-list response
        mock_make_request.return_value = {"error": "invalid"}

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Unexpected response format"):
            client.get_annotations(feed_entry_ids=["entry-1"])

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_annotations_empty_result(self, mock_make_request):
        """Test get_annotations with empty result list."""
        mock_make_request.return_value = []

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_annotations(feed_entry_ids=["nonexistent-entry"])

        assert result == []
        assert isinstance(result, list)

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_annotations_single_id(self, mock_make_request):
        """Test get_annotations with single ID in each filter type."""
        mock_make_request.return_value = []

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        # Test single feed_entry_id
        client.get_annotations(feed_entry_ids=["entry-1"])
        mock_make_request.assert_called_with(
            "GET", "/api/v1/core/annotations", {"feed_entry_ids_in": "entry-1"}
        )

        # Test single topic_id
        client.get_annotations(topic_ids=["topic-1"])
        mock_make_request.assert_called_with(
            "GET", "/api/v1/core/annotations", {"topic_ids_in": "topic-1"}
        )

        # Test single user_id
        client.get_annotations(user_ids=["user-1"])
        mock_make_request.assert_called_with(
            "GET", "/api/v1/core/annotations", {"user_ids_in": "user-1"}
        )


# Additional tests can be added here for:
# - _make_request method
# - _paginate method
# - list_topics, list_feeds, list_entries methods
# - get_feed_entries, get_topic_entries methods
# - Error handling and retry logic


class TestListCategories:
    """Tests for list_categories method."""

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_categories_success(self, mock_make_request, sample_categories):
        """Test successful categories retrieval."""
        mock_make_request.return_value = sample_categories

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.list_categories()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Finance"
        assert result[1]["name"] == "Medical Devices"

        mock_make_request.assert_called_once_with(
            "GET", "/api/v1/feeds/categories"
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_categories_empty(self, mock_make_request):
        """Test list_categories with empty result."""
        mock_make_request.return_value = []

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.list_categories()

        assert result == []
        assert isinstance(result, list)


class TestListTopicsWithCategory:
    """Tests for list_topics with category_id parameter."""

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_topics_with_category_id(self, mock_make_request, sample_topics):
        """Test list_topics filters by category_id."""
        mock_make_request.return_value = sample_topics

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.list_topics(category_id="cat-1")

        assert isinstance(result, list)
        mock_make_request.assert_called_once_with(
            "GET", "/api/v1/feeds/topics", params={"category_id": "cat-1"}
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_topics_without_category_id(self, mock_make_request, sample_topics):
        """Test list_topics without category_id preserves backward compatibility."""
        mock_make_request.return_value = sample_topics

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.list_topics()

        assert isinstance(result, list)
        mock_make_request.assert_called_once_with(
            "GET", "/api/v1/feeds/topics", params=None
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_topics_with_category_id_and_details(self, mock_make_request, sample_topics):
        """Test list_topics with both category_id and details."""
        mock_make_request.return_value = sample_topics

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.list_topics(details=True, category_id="cat-1")

        assert isinstance(result, list)
        mock_make_request.assert_called_once_with(
            "GET", "/api/v1/feeds/topics",
            params={"details": "true", "category_id": "cat-1"}
        )


class TestListStatutes:
    """Tests for list_statutes method."""

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_no_filters(self, mock_make_request, sample_statutes):
        """Test list_statutes with no filters sends only limit and offset."""
        mock_make_request.return_value = sample_statutes

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.list_statutes()

        assert isinstance(result, dict)
        assert "statutes" in result
        mock_make_request.assert_called_once_with(
            "GET", "/api/v1/statutes/", params={"limit": 50, "offset": 0}
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_with_jurisdiction(self, mock_make_request, sample_statutes):
        """Test list_statutes passes jurisdiction param."""
        mock_make_request.return_value = sample_statutes

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        client.list_statutes(jurisdiction="US")

        mock_make_request.assert_called_once_with(
            "GET",
            "/api/v1/statutes/",
            params={"limit": 50, "offset": 0, "jurisdiction": "US"},
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_with_multiple_filters(self, mock_make_request, sample_statutes):
        """Test list_statutes combines multiple filter params."""
        mock_make_request.return_value = sample_statutes

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        client.list_statutes(jurisdiction="EU", legal_level="legislative", document_type="regulation")

        mock_make_request.assert_called_once_with(
            "GET",
            "/api/v1/statutes/",
            params={
                "limit": 50,
                "offset": 0,
                "jurisdiction": "EU",
                "legal_level": "legislative",
                "document_type": "regulation",
            },
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_with_year_filter(self, mock_make_request, sample_statutes):
        """Test list_statutes passes year as int."""
        mock_make_request.return_value = sample_statutes

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        client.list_statutes(year=2016)

        mock_make_request.assert_called_once_with(
            "GET",
            "/api/v1/statutes/",
            params={"limit": 50, "offset": 0, "year": 2016},
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_validates_response_is_dict(self, mock_make_request):
        """Test list_statutes raises CarverAPIError when response is not a dict."""
        mock_make_request.return_value = ["unexpected", "list"]

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Unexpected response format"):
            client.list_statutes()

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_returns_paginated_response(self, mock_make_request, sample_statutes):
        """Test list_statutes response contains expected pagination keys."""
        mock_make_request.return_value = sample_statutes

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.list_statutes()

        assert "statutes" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert result["total"] == 2
        assert len(result["statutes"]) == 2

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_with_search(self, mock_make_request, sample_statutes):
        """Test list_statutes passes search param correctly."""
        mock_make_request.return_value = sample_statutes

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        client.list_statutes(search="Basel III")

        call_params = mock_make_request.call_args[1]["params"]
        assert call_params["search"] == "Basel III"

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_with_offset(self, mock_make_request, sample_statutes):
        """Test list_statutes passes offset param correctly."""
        mock_make_request.return_value = sample_statutes

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        client.list_statutes(offset=50)

        call_params = mock_make_request.call_args[1]["params"]
        assert call_params["offset"] == 50

    def test_list_statutes_invalid_limit_raises_error(self):
        """Test list_statutes raises ValueError for non-positive limit."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            client.list_statutes(limit=0)

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            client.list_statutes(limit=-1)

    def test_list_statutes_invalid_offset_raises_error(self):
        """Test list_statutes raises ValueError for negative offset."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="offset must be a non-negative integer"):
            client.list_statutes(offset=-1)

    def test_list_statutes_invalid_year_raises_error(self):
        """Test list_statutes raises ValueError for out-of-range year."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="year must be a 4-digit calendar year"):
            client.list_statutes(year=-1)

        with pytest.raises(ValueError, match="year must be a 4-digit calendar year"):
            client.list_statutes(year=0)

        with pytest.raises(ValueError, match="year must be a 4-digit calendar year"):
            client.list_statutes(year=999)

        with pytest.raises(ValueError, match="year must be a 4-digit calendar year"):
            client.list_statutes(year=2101)

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_list_statutes_validates_statutes_field_present(self, mock_make_request):
        """Test list_statutes raises CarverAPIError when 'statutes' key is missing."""
        mock_make_request.return_value = {"total": 0, "limit": 50, "offset": 0}

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Response missing 'statutes' field"):
            client.list_statutes()


class TestGetStatute:
    """Tests for get_statute method."""

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_success(self, mock_make_request, sample_statute):
        """Test successful single statute retrieval."""
        mock_make_request.return_value = sample_statute

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_statute("statute-1")

        assert isinstance(result, dict)
        assert result["id"] == "statute-1"
        assert result["canonical_name"] == "Dodd-Frank Wall Street Reform Act"
        mock_make_request.assert_called_once_with("GET", "/api/v1/statutes/statute-1")

    def test_get_statute_requires_statute_id(self):
        """Test that get_statute raises ValueError when statute_id is empty."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="statute_id is required"):
            client.get_statute("")

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_validates_response_is_dict(self, mock_make_request):
        """Test get_statute raises CarverAPIError when response is not a dict."""
        mock_make_request.return_value = ["unexpected"]

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Unexpected response format"):
            client.get_statute("statute-1")


class TestGetStatuteFilterOptions:
    """Tests for get_statute_filter_options method."""

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_filter_options_success(
        self, mock_make_request, sample_statute_filter_options
    ):
        """Test successful filter options retrieval."""
        mock_make_request.return_value = sample_statute_filter_options

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_statute_filter_options()

        assert isinstance(result, dict)
        assert "jurisdictions" in result
        assert "legal_levels" in result
        assert "document_types" in result
        assert "languages" in result
        assert "years" in result
        assert "US" in result["jurisdictions"]
        mock_make_request.assert_called_once_with("GET", "/api/v1/statutes/filters/options")

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_filter_options_validates_response_is_dict(self, mock_make_request):
        """Test get_statute_filter_options raises CarverAPIError when response is not a dict."""
        mock_make_request.return_value = ["unexpected"]

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Unexpected response format"):
            client.get_statute_filter_options()


class TestGetStatuteAnnotations:
    """Tests for get_statute_annotations method."""

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_annotations_success(
        self, mock_make_request, sample_statute_annotations
    ):
        """Test successful statute annotations retrieval."""
        mock_make_request.return_value = sample_statute_annotations

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        result = client.get_statute_annotations("statute-1")

        assert isinstance(result, dict)
        assert result["statute_id"] == "statute-1"
        assert "feed_entries" in result
        assert result["total"] == 1
        mock_make_request.assert_called_once_with(
            "GET",
            "/api/v1/statutes/statute-1/annotations",
            params={"limit": 100, "offset": 0},
        )

    def test_get_statute_annotations_requires_statute_id(self):
        """Test that get_statute_annotations raises ValueError when statute_id is empty."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="statute_id is required"):
            client.get_statute_annotations("")

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_annotations_with_pagination(
        self, mock_make_request, sample_statute_annotations
    ):
        """Test get_statute_annotations passes limit and offset params."""
        mock_make_request.return_value = sample_statute_annotations

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")
        client.get_statute_annotations("statute-1", limit=10, offset=20)

        mock_make_request.assert_called_once_with(
            "GET",
            "/api/v1/statutes/statute-1/annotations",
            params={"limit": 10, "offset": 20},
        )

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_annotations_validates_response_is_dict(self, mock_make_request):
        """Test get_statute_annotations raises CarverAPIError when response is not a dict."""
        mock_make_request.return_value = ["unexpected"]

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Unexpected response format"):
            client.get_statute_annotations("statute-1")

    def test_get_statute_annotations_invalid_limit_raises_error(self):
        """Test get_statute_annotations raises ValueError for non-positive limit."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            client.get_statute_annotations("statute-1", limit=0)

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            client.get_statute_annotations("statute-1", limit=-5)

    def test_get_statute_annotations_invalid_offset_raises_error(self):
        """Test get_statute_annotations raises ValueError for negative offset."""
        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(ValueError, match="offset must be a non-negative integer"):
            client.get_statute_annotations("statute-1", offset=-1)

    @patch.object(CarverFeedsAPIClient, "_make_request")
    def test_get_statute_annotations_validates_feed_entries_field_present(self, mock_make_request):
        """Test get_statute_annotations raises CarverAPIError when 'feed_entries' key is missing."""
        mock_make_request.return_value = {
            "statute_id": "statute-1",
            "statute_name": "Dodd-Frank Wall Street Reform Act",
            "total": 0,
        }

        client = CarverFeedsAPIClient(base_url="https://test.com", api_key="test-key")

        with pytest.raises(CarverAPIError, match="Response missing 'feed_entries' field"):
            client.get_statute_annotations("statute-1")
