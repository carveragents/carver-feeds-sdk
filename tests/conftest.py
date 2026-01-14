"""
Pytest configuration and fixtures for carver_feeds tests.

This module provides common fixtures and test data for the test suite.
"""

from unittest.mock import MagicMock, Mock

import pytest

from carver_feeds import CarverFeedsAPIClient


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    client = Mock(spec=CarverFeedsAPIClient)
    client.base_url = "https://test.carveragents.ai"
    client.api_key = "test-api-key"
    return client


@pytest.fixture
def sample_topics() -> list[dict]:
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
def sample_feeds() -> list[dict]:
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
def sample_entries() -> list[dict]:
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
def sample_user_subscriptions() -> dict:
    """Sample user topic subscription data for testing (mimics API response format)."""
    return {
        "subscriptions": [
            {
                "id": "topic-1",
                "name": "Abu Dhabi Global Market",
                "description": "A financial free zone in Abu Dhabi...",
                "base_domain": None,
            },
            {
                "id": "topic-2",
                "name": "Reserve Bank of India",
                "description": "India's central banking institution...",
                "base_domain": "rbi.org.in",
            },
        ],
        "total_count": 2,
    }


@pytest.fixture
def sample_annotations() -> list[dict]:
    """Sample annotation data for testing (mimics actual API response format)."""
    return [
        {
            "annotation": {
                "scores": {
                    "impact": {"label": "medium", "score": 7, "confidence": 0.9},
                    "urgency": {"label": "low", "score": 1, "confidence": 0.95},
                    "relevance": {"label": "medium", "score": 4.0, "confidence": 0.92},
                },
                "classification": {
                    "update_type": "regulatory_update",
                    "regulatory_source": {
                        "name": "Banking Regulatory Authority",
                        "division_office": "Compliance Division",
                    },
                    "metadata": {
                        "title": "New AML Regulations",
                        "language": ["English"],
                    },
                },
                "metadata": {
                    "tags": ["banking", "aml", "kyc", "compliance"],
                    "impact_summary": {
                        "objective": "Implement enhanced KYC procedures for banking institutions",
                        "why_it_matters": "Strengthens AML compliance framework",
                        "what_changed": "New requirements for customer verification",
                        "risk_impact": "Non-compliance may result in penalties",
                        "key_requirements": ["Enhanced due diligence", "Ongoing monitoring"],
                    },
                    "impacted_business": {
                        "industry": ["Banking", "Financial Services"],
                        "jurisdiction": ["Federal"],
                        "type": ["Banks", "Credit Unions"],
                    },
                    "impacted_functions": ["Compliance", "Risk Management", "Operations"],
                },
                "entry_id": "entry-1",
            },
            "feed_entry_id": "entry-1",
            "topic_id": "topic-1",
            "user_id": "user-1",
        },
        {
            "annotation": {
                "scores": {
                    "impact": {"label": "low", "score": 3, "confidence": 0.85},
                    "urgency": {"label": "low", "score": 0, "confidence": 0.9},
                    "relevance": {"label": "low", "score": 2.5, "confidence": 0.88},
                },
                "classification": {
                    "update_type": "guidance",
                    "regulatory_source": {
                        "name": "Health & Human Services",
                        "division_office": "Office of Civil Rights",
                    },
                    "metadata": {
                        "title": "HIPAA EHR Compliance Guidance",
                        "language": ["English"],
                    },
                },
                "metadata": {
                    "tags": ["healthcare", "privacy", "hipaa", "ehr"],
                    "impact_summary": {
                        "objective": "Clarify HIPAA requirements for electronic health records",
                        "why_it_matters": "Ensures patient data privacy and security",
                        "what_changed": "Updated guidance on data encryption and access controls",
                        "risk_impact": "Data breaches may lead to regulatory action",
                        "key_requirements": ["Data encryption", "Access logging"],
                    },
                    "impacted_business": {
                        "industry": ["Healthcare", "Medical Technology"],
                        "jurisdiction": ["Federal"],
                        "type": ["Hospitals", "Clinics", "Healthcare Providers"],
                    },
                    "impacted_functions": ["IT Security", "Compliance", "Healthcare Operations"],
                },
                "entry_id": "entry-2",
            },
            "feed_entry_id": "entry-2",
            "topic_id": "topic-2",
            "user_id": "user-1",
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
