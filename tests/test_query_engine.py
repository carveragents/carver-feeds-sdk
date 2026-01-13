"""
Tests for query_engine module.

This module tests the EntryQueryEngine class and related functionality.
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch
from carver_feeds.query_engine import EntryQueryEngine, create_query_engine
from carver_feeds.data_manager import FeedsDataManager


class TestEntryQueryEngine:
    """Tests for EntryQueryEngine class."""

    @pytest.fixture
    def mock_data_manager(self):
        """Create a mock data manager for testing."""
        return Mock(spec=FeedsDataManager)

    def test_initialization(self, mock_data_manager):
        """Test query engine initialization."""
        qe = EntryQueryEngine(mock_data_manager)
        assert qe.data_manager == mock_data_manager
        assert qe._results is None
        assert qe._initial_data_loaded is False

    def test_chain_method_returns_new_instance(self, mock_data_manager):
        """Test that chain() returns a fresh query engine instance."""
        qe1 = EntryQueryEngine(mock_data_manager)
        qe2 = qe1.chain()

        assert isinstance(qe2, EntryQueryEngine)
        assert qe2.data_manager == qe1.data_manager
        assert qe2._results is None


class TestCreateQueryEngine:
    """Tests for create_query_engine factory function."""

    @patch("carver_feeds.query_engine.create_data_manager")
    def test_create_query_engine(self, mock_create_dm):
        """Test create_query_engine factory function."""
        mock_dm = Mock(spec=FeedsDataManager)
        mock_create_dm.return_value = mock_dm

        qe = create_query_engine()

        assert isinstance(qe, EntryQueryEngine)
        assert qe.data_manager == mock_dm
        mock_create_dm.assert_called_once()


class TestFetchContentMethod:
    """Tests for fetch_content method in EntryQueryEngine."""

    @pytest.fixture
    def mock_data_manager(self):
        """Create a mock data manager with sample data."""
        mock_dm = Mock(spec=FeedsDataManager)
        # Create sample DataFrame for hierarchical view
        sample_df = pd.DataFrame(
            {
                "entry_id": ["entry-1", "entry-2"],
                "entry_title": ["Entry 1", "Entry 2"],
                "s3_content_md_path": ["s3://bucket/file1.md", "s3://bucket/file2.md"],
                "entry_content_markdown": [None, None],
            }
        )
        mock_dm.get_hierarchical_view.return_value = sample_df
        return mock_dm

    def test_fetch_content_with_explicit_client(self, mock_data_manager):
        """Test fetch_content with explicitly provided S3 client."""
        # Mock S3 client
        mock_s3 = Mock()
        mock_data_manager.fetch_contents_from_s3.return_value = pd.DataFrame(
            {
                "id": ["entry-1"],
                "entry_content_markdown": ["Content from S3"],
            }
        )

        qe = EntryQueryEngine(mock_data_manager)
        # Simulate data already loaded (as if filter_by_topic was called)
        qe._initial_data_loaded = True
        qe._results = pd.DataFrame({"id": ["entry-1"], "entry_content_markdown": [None]})

        # Now fetch content
        result = qe.fetch_content(s3_client=mock_s3)

        assert isinstance(result, EntryQueryEngine)
        mock_data_manager.fetch_contents_from_s3.assert_called_once()

    @patch("carver_feeds.query_engine.get_s3_client")
    def test_fetch_content_creates_client_from_env(self, mock_get_s3_client, mock_data_manager):
        """Test fetch_content creates S3 client from environment."""
        mock_s3 = Mock()
        mock_get_s3_client.return_value = mock_s3
        mock_data_manager.fetch_contents_from_s3.return_value = pd.DataFrame(
            {"id": ["entry-1"], "entry_content_markdown": ["Content"]}
        )

        qe = EntryQueryEngine(mock_data_manager)
        # Simulate data already loaded (as if filter_by_topic was called)
        qe._initial_data_loaded = True
        qe._results = pd.DataFrame({"id": ["entry-1"], "entry_content_markdown": [None]})

        result = qe.fetch_content()

        assert isinstance(result, EntryQueryEngine)
        mock_get_s3_client.assert_called_once()
        # Verify fetch_contents_from_s3 was called with the correct s3_client
        mock_data_manager.fetch_contents_from_s3.assert_called_once()
        call_args = mock_data_manager.fetch_contents_from_s3.call_args
        assert call_args[0][1] is mock_s3  # Second argument is s3_client

    @patch("carver_feeds.query_engine.get_s3_client")
    def test_fetch_content_no_s3_client_available(self, mock_get_s3_client, mock_data_manager):
        """Test fetch_content when no S3 client is available."""
        mock_get_s3_client.return_value = None

        qe = EntryQueryEngine(mock_data_manager)
        # Simulate data already loaded (as if filter_by_topic was called)
        qe._initial_data_loaded = True
        qe._results = pd.DataFrame({"id": ["entry-1"], "entry_content_markdown": [None]})

        # Should not raise error, just log warning
        result = qe.fetch_content()

        assert isinstance(result, EntryQueryEngine)
        mock_data_manager.fetch_contents_from_s3.assert_not_called()

    def test_fetch_content_before_loading_data(self):
        """Test fetch_content raises error when called without filter_by_topic first."""
        mock_dm = Mock(spec=FeedsDataManager)
        mock_s3 = Mock()
        qe = EntryQueryEngine(mock_dm)

        # Should raise ValueError telling user to call filter_by_topic first
        with pytest.raises(ValueError, match="You must call filter_by_topic\\(\\) first"):
            qe.fetch_content(s3_client=mock_s3)

        # Should not have attempted to fetch from S3
        mock_dm.fetch_contents_from_s3.assert_not_called()


class TestQueryEngineWithS3:
    """Tests for query engine initialization with S3 support."""

    @pytest.fixture
    def mock_data_manager(self):
        """Create a mock data manager."""
        return Mock(spec=FeedsDataManager)

    def test_init_with_fetch_content_enabled(self, mock_data_manager):
        """Test initialization with fetch_content=True."""
        mock_s3 = Mock()
        qe = EntryQueryEngine(mock_data_manager, fetch_content=True, s3_client=mock_s3)

        assert qe._fetch_content_on_load is True
        assert qe.s3_client is mock_s3

    def test_init_with_fetch_content_disabled(self, mock_data_manager):
        """Test initialization with fetch_content=False (default)."""
        qe = EntryQueryEngine(mock_data_manager)

        assert qe._fetch_content_on_load is False
        assert qe.s3_client is None

    def test_lazy_load_passes_fetch_content_param(self, mock_data_manager):
        """Test that lazy loading passes fetch_content parameter to data_manager."""
        mock_s3 = Mock()
        sample_df = pd.DataFrame(
            {"entry_id": ["entry-1"], "entry_entry_content_markdown": ["Content"], "topic_id": ["topic-1"]}
        )
        mock_data_manager.get_hierarchical_view.return_value = sample_df
        mock_data_manager.get_topics_df.return_value = pd.DataFrame(
            {"id": ["topic-1"], "name": ["Banking"]}
        )

        qe = EntryQueryEngine(mock_data_manager, fetch_content=True, s3_client=mock_s3)
        # Must call filter_by_topic first
        qe.filter_by_topic(topic_id="topic-1").to_dataframe()

        # Verify get_hierarchical_view was called with fetch_content and s3_client params
        mock_data_manager.get_hierarchical_view.assert_called_once()
        call_kwargs = mock_data_manager.get_hierarchical_view.call_args.kwargs
        assert call_kwargs["fetch_content"] is True
        assert call_kwargs["s3_client"] is mock_s3


class TestCreateQueryEngineWithS3:
    """Tests for create_query_engine factory with S3 support."""

    @patch("carver_feeds.query_engine.create_data_manager")
    def test_create_query_engine_with_fetch_content(self, mock_create_dm):
        """Test creating query engine with fetch_content enabled."""
        mock_dm = Mock(spec=FeedsDataManager)
        mock_create_dm.return_value = mock_dm
        mock_s3 = Mock()

        qe = create_query_engine(fetch_content=True, s3_client=mock_s3)

        assert isinstance(qe, EntryQueryEngine)
        assert qe._fetch_content_on_load is True
        assert qe.s3_client is mock_s3

    @patch("carver_feeds.query_engine.create_data_manager")
    def test_create_query_engine_default_no_fetch_content(self, mock_create_dm):
        """Test creating query engine with default (no fetch_content)."""
        mock_dm = Mock(spec=FeedsDataManager)
        mock_create_dm.return_value = mock_dm

        qe = create_query_engine()

        assert qe._fetch_content_on_load is False
        assert qe.s3_client is None


# Additional tests can be added here for:
# - filter_by_topic method
# - filter_by_feed method
# - filter_by_date method
# - filter_by_active method
# - search_entries method
# - to_dataframe, to_dict, to_json, to_csv methods
# - Method chaining
# - Lazy loading behavior
