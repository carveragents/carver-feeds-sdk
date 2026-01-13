"""
Pytest configuration and fixtures for carver_feeds tests.

This module provides common fixtures and test data for the test suite.
"""

import pytest
from typing import Dict, List
from unittest.mock import Mock, MagicMock
from carver_feeds import CarverFeedsAPIClient


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    client = Mock(spec=CarverFeedsAPIClient)
    client.base_url = "https://test.carveragents.ai"
    client.api_key = "test-api-key"
    return client


@pytest.fixture
def sample_topics() -> List[Dict]:
    """Sample topic data for testing."""
    return [
        {
            "id": "topic-1",
            "name": "Banking",
            "description": "Banking regulations",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "is_active": True,
        },
        {
            "id": "topic-2",
            "name": "Healthcare",
            "description": "Healthcare regulations",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "is_active": True,
        },
    ]


@pytest.fixture
def sample_feeds() -> List[Dict]:
    """Sample feed data for testing."""
    return [
        {
            "id": "feed-1",
            "name": "Banking News",
            "url": "https://example.com/banking",
            "topic": {"id": "topic-1", "name": "Banking"},
            "description": "Latest banking news",
            "created_at": "2024-01-01T00:00:00Z",
            "is_active": True,
        },
        {
            "id": "feed-2",
            "name": "Healthcare Updates",
            "url": "https://example.com/healthcare",
            "topic": {"id": "topic-2", "name": "Healthcare"},
            "description": "Healthcare updates",
            "created_at": "2024-01-01T00:00:00Z",
            "is_active": True,
        },
    ]


@pytest.fixture
def sample_entries() -> List[Dict]:
    """Sample entry data for testing (mimics API response format)."""
    return [
        {
            "id": "entry-1",
            "title": "New Banking Regulation",
            "link": "https://example.com/entry-1",
            "content_markdown": "# New Banking Regulation\nDetails about the regulation...",
            "published_date": "2024-01-15T10:00:00Z",
            "created_at": "2024-01-15T10:00:00Z",
            "is_active": True,
        },
        {
            "id": "entry-2",
            "title": "Healthcare Compliance Update",
            "link": "https://example.com/entry-2",
            "content_markdown": "# Healthcare Compliance\nNew compliance requirements...",
            "published_date": "2024-01-16T10:00:00Z",
            "created_at": "2024-01-16T10:00:00Z",
            "is_active": True,
        },
    ]


@pytest.fixture
def mock_successful_response():
    """Mock a successful API response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"status": "success"}
    return response


@pytest.fixture
def mock_auth_error_response():
    """Mock an authentication error response."""
    response = MagicMock()
    response.status_code = 401
    response.text = "Unauthorized"
    return response


@pytest.fixture
def mock_rate_limit_response():
    """Mock a rate limit error response."""
    response = MagicMock()
    response.status_code = 429
    response.text = "Rate limit exceeded"
    return response
