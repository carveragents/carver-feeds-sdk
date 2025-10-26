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
        assert 'id' in result.columns
        assert 'name' in result.columns

    def test_get_feeds_df_returns_dataframe(self, mock_api_client, sample_feeds):
        """Test that get_feeds_df returns a DataFrame."""
        mock_api_client.list_feeds.return_value = sample_feeds
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_feeds_df()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'id' in result.columns
        assert 'name' in result.columns
        assert 'topic_id' in result.columns

    def test_get_feeds_df_flattens_topic_object(self, mock_api_client, sample_feeds):
        """Test that get_feeds_df properly flattens nested topic object."""
        mock_api_client.list_feeds.return_value = sample_feeds
        dm = FeedsDataManager(mock_api_client)

        result = dm.get_feeds_df()

        assert 'topic_id' in result.columns
        assert 'topic_name' in result.columns
        assert result['topic_id'].iloc[0] == 'topic-1'
        assert result['topic_name'].iloc[0] == 'Banking'


class TestCreateDataManager:
    """Tests for create_data_manager factory function."""

    @patch('carver_feeds.data_manager.get_client')
    def test_create_data_manager(self, mock_get_client, mock_api_client):
        """Test create_data_manager factory function."""
        mock_get_client.return_value = mock_api_client

        dm = create_data_manager()

        assert isinstance(dm, FeedsDataManager)
        mock_get_client.assert_called_once()


# Additional tests can be added here for:
# - get_entries_df method
# - get_hierarchical_view method
# - _json_to_dataframe method
# - Date conversion handling
# - Schema validation
