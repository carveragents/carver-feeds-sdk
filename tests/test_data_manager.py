"""
Tests for data_manager module.

This module tests the FeedsDataManager class and related functionality.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from carver_feeds.data_manager import FeedsDataManager, create_data_manager
from carver_feeds.carver_api import CarverFeedsAPIClient


class TestFeedsDataManager:
    """Tests for FeedsDataManager class."""

    def test_initialization_requires_api_client(self, mock_api_client):
        """Test that initialization requires CarverFeedsAPIClient instance."""
        dm = FeedsDataManager(mock_api_client)
        assert dm.api_client == mock_api_client

    def test_initialization_with_invalid_client_raises_error(self):
        """Test that initialization with non-client raises TypeError."""
        with pytest.raises(TypeError, match="CarverFeedsAPIClient"):
            FeedsDataManager("not-a-client")

    def test_get_topics_df_returns_dataframe(self, mock_api_client, sample_topics):
        """Test that get_topics_df returns a DataFrame."""
        mock_api_client.list_topics.return_value = sample_topics
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_topics_df()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "id" in result.columns
        assert "name" in result.columns

class TestCreateDataManager:
    """Tests for create_data_manager factory function."""

    @patch("carver_feeds.data_manager.get_client")
    def test_create_data_manager(self, mock_get_client, mock_api_client):
        """Test create_data_manager factory function."""
        mock_get_client.return_value = mock_api_client

        dm = create_data_manager()

        assert isinstance(dm, FeedsDataManager)
        mock_get_client.assert_called_once()


class TestGetTopicEntriesDF:
    """Tests for get_topic_entries_df method."""

    def test_get_topic_entries_df_without_fetch_content(self, mock_api_client, sample_entries):
        """Test get_topic_entries_df without fetching content from S3."""
        mock_api_client.get_topic_entries.return_value = sample_entries
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=False)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "id" in result.columns
        assert "title" in result.columns
        assert "entry_content_markdown" in result.columns
        # Content should be None when not fetched
        assert result["entry_content_markdown"].isna().all()

    @patch("carver_feeds.data_manager.get_s3_client")
    def test_get_topic_entries_df_with_fetch_content_no_s3_client(
        self, mock_get_s3_client, mock_api_client, sample_entries
    ):
        """Test get_topic_entries_df with fetch_content=True but no S3 client available."""
        mock_api_client.get_topic_entries.return_value = sample_entries
        mock_get_s3_client.return_value = None  # Simulate no S3 credentials

        dm = FeedsDataManager(mock_api_client)
        result = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=True)

        assert isinstance(result, pd.DataFrame)
        # Content should be None when S3 client unavailable
        assert result["entry_content_markdown"].isna().all()

    @patch("carver_feeds.data_manager.get_s3_client")
    def test_get_topic_entries_df_with_fetch_content_success(
        self, mock_get_s3_client, mock_api_client
    ):
        """Test get_topic_entries_df with successful S3 content fetch."""
        # Sample entries with S3 paths in extracted_metadata
        entries_with_s3 = [
            {
                "id": "entry-1",
                "title": "Entry 1",
                "link": "https://example.com/entry-1",
                "published_date": "2024-01-15T10:00:00Z",
                "created_at": "2024-01-15T10:00:00Z",
                "is_active": True,
                "extracted_metadata": {
                    "feed_id": "feed-1",
                    "topic_id": "topic-1",
                    "status": "completed",
                    "timestamp": "2024-01-15T10:00:00Z",
                    "s3_content_md_path": "s3://bucket/entry1.md",
                    "s3_content_html_path": "s3://bucket/entry1.html",
                    "s3_aggregated_content_md_path": None,
                },
            }
        ]

        mock_api_client.get_topic_entries.return_value = entries_with_s3

        # Mock S3 client
        mock_s3 = Mock()
        mock_s3.fetch_content_batch.return_value = {
            "s3://bucket/entry1.md": "# Content from S3"
        }
        mock_get_s3_client.return_value = mock_s3

        dm = FeedsDataManager(mock_api_client)
        result = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result["entry_content_markdown"].iloc[0] == "# Content from S3"
        mock_s3.fetch_content_batch.assert_called_once()

    def test_get_topic_entries_df_with_explicit_s3_client(self, mock_api_client):
        """Test get_topic_entries_df with explicitly provided S3 client."""
        entries_with_s3 = [
            {
                "id": "entry-1",
                "title": "Entry 1",
                "link": "https://example.com/entry-1",
                "published_date": "2024-01-15T10:00:00Z",
                "created_at": "2024-01-15T10:00:00Z",
                "is_active": True,
                "extracted_metadata": {
                    "feed_id": "feed-1",
                    "s3_content_md_path": "s3://bucket/entry1.md",
                },
            }
        ]

        mock_api_client.get_topic_entries.return_value = entries_with_s3

        # Explicit S3 client
        mock_s3 = Mock()
        mock_s3.fetch_content_batch.return_value = {
            "s3://bucket/entry1.md": "Explicit S3 content"
        }

        dm = FeedsDataManager(mock_api_client)
        result = dm.get_topic_entries_df(topic_id="topic-123", fetch_content=True, s3_client=mock_s3)

        assert result["entry_content_markdown"].iloc[0] == "Explicit S3 content"
        mock_s3.fetch_content_batch.assert_called_once()


class TestFetchContentsFromS3:
    """Tests for fetch_contents_from_s3 public method."""

    def test_fetch_contents_from_s3_success(self, mock_api_client):
        """Test successful S3 content fetching."""
        # Create DataFrame with S3 paths
        df = pd.DataFrame(
            {
                "id": ["entry-1", "entry-2"],
                "s3_content_md_path": ["s3://bucket/file1.md", "s3://bucket/file2.md"],
            }
        )

        mock_s3 = Mock()
        mock_s3.fetch_content_batch.return_value = {
            "s3://bucket/file1.md": "Content 1",
            "s3://bucket/file2.md": "Content 2",
        }

        dm = FeedsDataManager(mock_api_client)
        result = dm.fetch_contents_from_s3(df, mock_s3)

        assert "entry_content_markdown" in result.columns
        assert result["entry_content_markdown"].iloc[0] == "Content 1"
        assert result["entry_content_markdown"].iloc[1] == "Content 2"

    def test_fetch_contents_from_s3_no_s3_paths(self, mock_api_client):
        """Test fetch_contents_from_s3 when no S3 paths are present."""
        df = pd.DataFrame({"id": ["entry-1", "entry-2"]})

        mock_s3 = Mock()
        dm = FeedsDataManager(mock_api_client)
        result = dm.fetch_contents_from_s3(df, mock_s3)

        assert "entry_content_markdown" in result.columns
        assert result["entry_content_markdown"].isna().all()
        mock_s3.fetch_content_batch.assert_not_called()

    def test_fetch_contents_from_s3_empty_paths(self, mock_api_client):
        """Test fetch_contents_from_s3 with all null S3 paths."""
        df = pd.DataFrame(
            {"id": ["entry-1", "entry-2"], "s3_content_md_path": [None, None]}
        )

        mock_s3 = Mock()
        dm = FeedsDataManager(mock_api_client)
        result = dm.fetch_contents_from_s3(df, mock_s3)

        assert "entry_content_markdown" in result.columns
        assert result["entry_content_markdown"].isna().all()
        mock_s3.fetch_content_batch.assert_not_called()

    def test_fetch_contents_from_s3_partial_success(self, mock_api_client):
        """Test fetch_contents_from_s3 with some failed fetches."""
        df = pd.DataFrame(
            {
                "id": ["entry-1", "entry-2"],
                "s3_content_md_path": ["s3://bucket/exists.md", "s3://bucket/missing.md"],
            }
        )

        mock_s3 = Mock()
        mock_s3.fetch_content_batch.return_value = {
            "s3://bucket/exists.md": "Content",
            "s3://bucket/missing.md": None,  # Failed fetch
        }

        dm = FeedsDataManager(mock_api_client)
        result = dm.fetch_contents_from_s3(df, mock_s3)

        assert result["entry_content_markdown"].iloc[0] == "Content"
        assert pd.isna(result["entry_content_markdown"].iloc[1])


class TestHandleS3Fetch:
    """Tests for _handle_s3_fetch helper method."""

    def test_handle_s3_fetch_disabled(self, mock_api_client):
        """Test _handle_s3_fetch when fetch_content=False."""
        df = pd.DataFrame({"id": ["entry-1"]})
        dm = FeedsDataManager(mock_api_client)

        result = dm._handle_s3_fetch(df, s3_client=None, fetch_content=False)

        assert "entry_content_markdown" in result.columns
        assert result["entry_content_markdown"].isna().all()

    @patch("carver_feeds.data_manager.get_s3_client")
    def test_handle_s3_fetch_creates_client_from_env(
        self, mock_get_s3_client, mock_api_client
    ):
        """Test _handle_s3_fetch creates S3 client from environment."""
        df = pd.DataFrame({"id": ["entry-1"], "s3_content_md_path": ["s3://bucket/file.md"]})

        mock_s3 = Mock()
        mock_s3.fetch_content_batch.return_value = {"s3://bucket/file.md": "Content"}
        mock_get_s3_client.return_value = mock_s3

        dm = FeedsDataManager(mock_api_client)
        result = dm._handle_s3_fetch(df, s3_client=None, fetch_content=True)

        mock_get_s3_client.assert_called_once()
        assert result["entry_content_markdown"].iloc[0] == "Content"

    def test_handle_s3_fetch_uses_provided_client(self, mock_api_client):
        """Test _handle_s3_fetch uses explicitly provided S3 client."""
        df = pd.DataFrame({"id": ["entry-1"], "s3_content_md_path": ["s3://bucket/file.md"]})

        mock_s3 = Mock()
        mock_s3.fetch_content_batch.return_value = {"s3://bucket/file.md": "Content"}

        dm = FeedsDataManager(mock_api_client)
        result = dm._handle_s3_fetch(df, s3_client=mock_s3, fetch_content=True)

        assert result["entry_content_markdown"].iloc[0] == "Content"


class TestExtractMetadataFields:
    """Tests for _extract_metadata_fields helper method."""

    def test_extract_metadata_fields_with_metadata(self, mock_api_client):
        """Test extraction of fields from extracted_metadata."""
        entry = {
            "id": "entry-1",
            "title": "Entry 1",
            "extracted_metadata": {
                "feed_id": "feed-1",
                "topic_id": "topic-1",
                "status": "completed",
                "timestamp": "2024-01-15T10:00:00Z",
                "s3_content_md_path": "s3://bucket/file.md",
                "s3_content_html_path": "s3://bucket/file.html",
                "s3_aggregated_content_md_path": None,
            },
        }

        dm = FeedsDataManager(mock_api_client)
        result = dm._extract_metadata_fields(entry)

        assert result["feed_id"] == "feed-1"
        assert result["topic_id"] == "topic-1"
        assert result["content_status"] == "completed"
        assert result["s3_content_md_path"] == "s3://bucket/file.md"
        assert "extracted_metadata_full" in result

    def test_extract_metadata_fields_without_metadata(self, mock_api_client):
        """Test extraction when no extracted_metadata is present."""
        entry = {"id": "entry-1", "title": "Entry 1"}

        dm = FeedsDataManager(mock_api_client)
        result = dm._extract_metadata_fields(entry)

        # Should return entry unchanged
        assert result == entry

    def test_extract_metadata_fields_null_metadata(self, mock_api_client):
        """Test extraction when extracted_metadata is null."""
        entry = {"id": "entry-1", "title": "Entry 1", "extracted_metadata": None}

        dm = FeedsDataManager(mock_api_client)
        result = dm._extract_metadata_fields(entry)

        # Should return entry unchanged
        assert result["id"] == "entry-1"

    def test_extract_metadata_fields_missing_fields(self, mock_api_client):
        """Test extraction with missing fields in metadata."""
        entry = {
            "id": "entry-1",
            "extracted_metadata": {
                "feed_id": "feed-1"
                # Missing other fields
            },
        }

        dm = FeedsDataManager(mock_api_client)
        result = dm._extract_metadata_fields(entry)

        assert result["feed_id"] == "feed-1"
        assert result["topic_id"] is None
        assert result["content_status"] is None


class TestGetUserTopicSubscriptionsDF:
    """Tests for get_user_topic_subscriptions_df method."""

    def test_get_user_topic_subscriptions_df_requires_user_id(self, mock_api_client):
        """Test that get_user_topic_subscriptions_df requires user_id parameter."""
        dm = FeedsDataManager(mock_api_client)

        with pytest.raises(ValueError, match="user_id is required"):
            dm.get_user_topic_subscriptions_df(user_id="")

    def test_get_user_topic_subscriptions_df_returns_dataframe(
        self, mock_api_client, sample_user_subscriptions
    ):
        """Test that get_user_topic_subscriptions_df returns a DataFrame."""
        mock_api_client.get_user_topic_subscriptions.return_value = sample_user_subscriptions
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_user_topic_subscriptions_df(user_id="user-123")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "id" in result.columns
        assert "name" in result.columns
        assert "description" in result.columns
        assert "base_domain" in result.columns

        # Verify API was called with correct user_id
        mock_api_client.get_user_topic_subscriptions.assert_called_once_with("user-123")

    def test_get_user_topic_subscriptions_df_empty_subscriptions(self, mock_api_client):
        """Test get_user_topic_subscriptions_df with empty subscriptions list."""
        mock_api_client.get_user_topic_subscriptions.return_value = {
            "subscriptions": [],
            "total_count": 0,
        }
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_user_topic_subscriptions_df(user_id="user-123")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        # Verify expected columns exist even with empty DataFrame
        assert list(result.columns) == ["id", "name", "description", "base_domain"]

    def test_get_user_topic_subscriptions_df_handles_null_base_domain(
        self, mock_api_client
    ):
        """Test get_user_topic_subscriptions_df handles null base_domain values."""
        mock_api_client.get_user_topic_subscriptions.return_value = {
            "subscriptions": [
                {
                    "id": "topic-1",
                    "name": "Topic 1",
                    "description": "Description 1",
                    "base_domain": None,
                },
                {
                    "id": "topic-2",
                    "name": "Topic 2",
                    "description": "Description 2",
                    "base_domain": "example.com",
                },
            ],
            "total_count": 2,
        }
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_user_topic_subscriptions_df(user_id="user-123")

        assert len(result) == 2
        assert pd.isna(result.iloc[0]["base_domain"])
        assert result.iloc[1]["base_domain"] == "example.com"

    def test_get_user_topic_subscriptions_df_validates_data(self, mock_api_client):
        """Test that get_user_topic_subscriptions_df validates subscription data."""
        # Test with subscriptions containing extra fields
        mock_api_client.get_user_topic_subscriptions.return_value = {
            "subscriptions": [
                {
                    "id": "topic-1",
                    "name": "Topic 1",
                    "description": "Description 1",
                    "base_domain": None,
                    "extra_field": "extra_value",
                }
            ],
            "total_count": 1,
        }
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_user_topic_subscriptions_df(user_id="user-123")

        # Should successfully convert even with extra fields
        assert len(result) == 1
        assert "extra_field" in result.columns


# Additional tests can be added here for:
# - get_hierarchical_view method with S3 content
# - _json_to_dataframe method
# - Date conversion handling
# - Schema validation
