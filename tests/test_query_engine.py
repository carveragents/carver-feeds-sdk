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

    @patch('carver_feeds.query_engine.create_data_manager')
    def test_create_query_engine(self, mock_create_dm):
        """Test create_query_engine factory function."""
        mock_dm = Mock(spec=FeedsDataManager)
        mock_create_dm.return_value = mock_dm

        qe = create_query_engine()

        assert isinstance(qe, EntryQueryEngine)
        assert qe.data_manager == mock_dm
        mock_create_dm.assert_called_once()


# Additional tests can be added here for:
# - filter_by_topic method
# - filter_by_feed method
# - filter_by_date method
# - filter_by_active method
# - search_entries method
# - to_dataframe, to_dict, to_json, to_csv methods
# - Method chaining
# - Lazy loading behavior
