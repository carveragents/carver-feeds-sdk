"""
Tests for S3ContentClient module.

This module tests the S3ContentClient class and related functionality including
S3 path parsing, content fetching, batch operations, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from carver_feeds.s3_client import (
    S3ContentClient,
    S3Error,
    S3CredentialsError,
    S3FetchError,
    get_s3_client,
    BOTO3_AVAILABLE,
    MAX_CONTENT_SIZE_BYTES,
)


class TestS3PathParsing:
    """Test S3 path parsing and validation."""

    def test_parse_valid_s3_path_simple(self):
        """Test parsing a simple valid S3 path."""
        bucket, key = S3ContentClient.parse_s3_path("s3://my-bucket/path/to/file.md")
        assert bucket == "my-bucket"
        assert key == "path/to/file.md"

    def test_parse_valid_s3_path_single_key(self):
        """Test parsing S3 path with single-level key."""
        bucket, key = S3ContentClient.parse_s3_path("s3://bucket-name/file.txt")
        assert bucket == "bucket-name"
        assert key == "file.txt"

    def test_parse_valid_s3_path_deep_nesting(self):
        """Test parsing S3 path with deep folder nesting."""
        bucket, key = S3ContentClient.parse_s3_path("s3://my-bucket/a/b/c/d/e/f/file.md")
        assert bucket == "my-bucket"
        assert key == "a/b/c/d/e/f/file.md"

    def test_parse_valid_s3_path_with_dots(self):
        """Test parsing bucket name with dots (valid AWS naming)."""
        bucket, key = S3ContentClient.parse_s3_path("s3://my.bucket.name/key.txt")
        assert bucket == "my.bucket.name"
        assert key == "key.txt"

    def test_parse_valid_s3_path_with_numbers(self):
        """Test parsing bucket with numbers."""
        bucket, key = S3ContentClient.parse_s3_path("s3://bucket123/path456/file.txt")
        assert bucket == "bucket123"
        assert key == "path456/file.txt"

    def test_parse_invalid_format_https(self):
        """Test that HTTPS URLs are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("https://bucket/key")

    def test_parse_invalid_format_http(self):
        """Test that HTTP URLs are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("http://bucket/key")

    def test_parse_invalid_format_no_protocol(self):
        """Test that paths without protocol are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("bucket/key/file.txt")

    def test_parse_invalid_format_missing_key(self):
        """Test that paths without key are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("s3://bucket")

    def test_parse_invalid_format_missing_bucket(self):
        """Test that paths without bucket are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("s3:///key/path.txt")

    def test_parse_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path"):
            S3ContentClient.parse_s3_path("")

    def test_parse_none_value(self):
        """Test that None value is rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path"):
            S3ContentClient.parse_s3_path(None)  # type: ignore

    def test_parse_path_too_long(self):
        """Test that paths exceeding length limit are rejected."""
        long_path = "s3://bucket/" + "a" * 1100
        with pytest.raises(ValueError, match="S3 path too long"):
            S3ContentClient.parse_s3_path(long_path)

    def test_parse_path_with_traversal_attempt(self):
        """Test that path traversal attempts are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 key"):
            S3ContentClient.parse_s3_path("s3://bucket/path/../../../etc/passwd")

    def test_parse_bucket_uppercase_rejected(self):
        """Test that uppercase bucket names are rejected (AWS S3 rule)."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("s3://MyBucket/key.txt")

    def test_parse_bucket_with_underscore_rejected(self):
        """Test that bucket names with underscores are rejected (AWS S3 rule)."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("s3://my_bucket/key.txt")

    def test_parse_bucket_starting_with_hyphen_rejected(self):
        """Test that bucket names starting with hyphen are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("s3://-bucket/key.txt")

    def test_parse_bucket_ending_with_hyphen_rejected(self):
        """Test that bucket names ending with hyphen are rejected."""
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            S3ContentClient.parse_s3_path("s3://bucket-/key.txt")


class TestS3ClientInitialization:
    """Test S3 client initialization."""

    @patch("carver_feeds.s3_client.boto3")
    def test_init_with_profile_success(self, mock_boto3):
        """Test successful initialization with AWS profile."""
        # Setup mocks
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        # Initialize client
        client = S3ContentClient(profile_name="test-profile")

        # Verify
        assert client.profile_name == "test-profile"
        assert client.region_name == "us-east-1"
        assert client._s3_client is mock_s3_client
        mock_boto3.Session.assert_called_once_with(
            profile_name="test-profile", region_name="us-east-1"
        )

    @patch("carver_feeds.s3_client.boto3")
    def test_init_with_custom_region(self, mock_boto3):
        """Test initialization with custom region."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test-profile", region_name="us-west-2")

        assert client.region_name == "us-west-2"
        mock_boto3.Session.assert_called_once_with(
            profile_name="test-profile", region_name="us-west-2"
        )

    @patch("carver_feeds.s3_client.boto3")
    def test_init_without_credentials_raises_error(self, mock_boto3):
        """Test initialization without any credentials raises error."""
        # With the new behavior, we must provide either profile or credentials
        with pytest.raises(S3CredentialsError, match="AWS credentials not configured"):
            S3ContentClient(profile_name=None)

    @patch("carver_feeds.s3_client.boto3")
    def test_init_with_custom_retry_settings(self, mock_boto3):
        """Test initialization with custom retry settings."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test", max_retries=5, initial_retry_delay=2.0)

        assert client.max_retries == 5
        assert client.initial_retry_delay == 2.0

    @patch("carver_feeds.s3_client.boto3")
    def test_init_profile_not_found_error(self, mock_boto3):
        """Test initialization with non-existent profile."""
        from botocore.exceptions import ProfileNotFound

        mock_boto3.Session.side_effect = ProfileNotFound(profile="bad-profile")

        with pytest.raises(S3CredentialsError, match="AWS profile 'bad-profile' not found"):
            S3ContentClient(profile_name="bad-profile")

    @patch("carver_feeds.s3_client.boto3")
    def test_init_no_credentials_error(self, mock_boto3):
        """Test initialization with missing credentials."""
        from botocore.exceptions import NoCredentialsError

        mock_boto3.Session.side_effect = NoCredentialsError()

        with pytest.raises(S3CredentialsError, match="AWS credentials not found"):
            S3ContentClient(profile_name=None)

    @patch("carver_feeds.s3_client.boto3")
    def test_init_generic_error(self, mock_boto3):
        """Test initialization with generic error."""
        mock_boto3.Session.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(S3CredentialsError, match="Failed to initialize S3 client"):
            S3ContentClient(profile_name="test")

    @patch("carver_feeds.s3_client.BOTO3_AVAILABLE", False)
    def test_init_boto3_not_installed(self):
        """Test initialization when boto3 is not installed."""
        with pytest.raises(ImportError, match="boto3 is required for S3 content fetching"):
            S3ContentClient(profile_name="test")

    @patch("carver_feeds.s3_client.boto3")
    def test_init_with_credentials_success(self, mock_boto3):
        """Test successful initialization with AWS credentials."""
        # Setup mocks
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        # Initialize client with credentials
        client = S3ContentClient(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        # Verify
        assert client.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert client.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert client.region_name == "us-east-1"
        assert client._s3_client is mock_s3_client
        mock_boto3.Session.assert_called_once_with(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region_name="us-east-1",
        )

    @patch("carver_feeds.s3_client.boto3")
    def test_init_with_credentials_and_region(self, mock_boto3):
        """Test initialization with credentials and custom region."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region_name="eu-west-1",
        )

        assert client.region_name == "eu-west-1"
        mock_boto3.Session.assert_called_once_with(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region_name="eu-west-1",
        )

    @patch("carver_feeds.s3_client.boto3")
    def test_init_profile_takes_priority_over_credentials(self, mock_boto3):
        """Test that profile takes priority when both profile and credentials provided."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(
            profile_name="test-profile",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        # Verify profile is used (not credentials)
        assert client.profile_name == "test-profile"
        mock_boto3.Session.assert_called_once_with(
            profile_name="test-profile", region_name="us-east-1"
        )

    @patch("carver_feeds.s3_client.boto3")
    def test_init_no_credentials_error(self, mock_boto3):
        """Test initialization fails when no credentials provided."""
        with pytest.raises(S3CredentialsError, match="AWS credentials not configured"):
            S3ContentClient()

    @patch("carver_feeds.s3_client.boto3")
    def test_init_only_access_key_error(self, mock_boto3):
        """Test initialization fails when only access key provided."""
        with pytest.raises(S3CredentialsError, match="AWS credentials not configured"):
            S3ContentClient(aws_access_key_id="AKIAIOSFODNN7EXAMPLE")

    @patch("carver_feeds.s3_client.boto3")
    def test_init_only_secret_key_error(self, mock_boto3):
        """Test initialization fails when only secret key provided."""
        with pytest.raises(S3CredentialsError, match="AWS credentials not configured"):
            S3ContentClient(aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    @patch("carver_feeds.s3_client.boto3")
    def test_init_with_invalid_credentials_error(self, mock_boto3):
        """Test initialization with invalid credentials."""
        from botocore.exceptions import NoCredentialsError

        mock_boto3.Session.side_effect = NoCredentialsError()

        with pytest.raises(S3CredentialsError, match="AWS credentials not found"):
            S3ContentClient(
                aws_access_key_id="INVALID",
                aws_secret_access_key="INVALID",
            )


class TestFetchContent:
    """Test content fetching from S3."""

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_success(self, mock_boto3):
        """Test successful content fetch."""
        # Setup mocks
        mock_s3_client = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b"Test content from S3"
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        mock_s3_client.head_object.return_value = {"ContentLength": 20}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        # Test
        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/path/file.md")

        assert content == "Test content from S3"
        mock_s3_client.get_object.assert_called_once_with(Bucket="bucket", Key="path/file.md")

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_unicode(self, mock_boto3):
        """Test fetching content with unicode characters."""
        mock_s3_client = Mock()
        mock_body = Mock()
        mock_body.read.return_value = "Test unicode: 你好世界 🚀".encode("utf-8")
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        mock_s3_client.head_object.return_value = {"ContentLength": 50}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/unicode.md")

        assert content == "Test unicode: 你好世界 🚀"

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_empty_path(self, mock_boto3):
        """Test fetch with empty S3 path."""
        mock_session = Mock()
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("")

        assert content is None

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_invalid_path_format(self, mock_boto3):
        """Test fetch with invalid S3 path format."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("https://bucket/key")

        assert content is None

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_no_such_key(self, mock_boto3):
        """Test fetch when S3 key does not exist."""
        from botocore.exceptions import ClientError

        mock_s3_client = Mock()
        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/nonexistent.md")

        assert content is None

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_no_such_bucket(self, mock_boto3):
        """Test fetch when S3 bucket does not exist."""
        from botocore.exceptions import ClientError

        mock_s3_client = Mock()
        error_response = {"Error": {"Code": "NoSuchBucket"}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bad-bucket/file.md")

        assert content is None

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_access_denied(self, mock_boto3):
        """Test fetch when access is denied."""
        from botocore.exceptions import ClientError

        mock_s3_client = Mock()
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://restricted-bucket/file.md")

        assert content is None

    @patch("carver_feeds.s3_client.boto3")
    @patch("carver_feeds.s3_client.time.sleep")  # Mock sleep to speed up test
    def test_fetch_content_transient_error_with_retry(self, mock_sleep, mock_boto3):
        """Test fetch with transient error that succeeds on retry."""
        from botocore.exceptions import ClientError

        mock_s3_client = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b"Success after retry"

        # First call fails with 500, second succeeds
        error_response = {"Error": {"Code": "InternalServerError"}}
        mock_s3_client.get_object.side_effect = [
            ClientError(error_response, "GetObject"),
            {"Body": mock_body},
        ]
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test", max_retries=3)
        content = client.fetch_content("s3://bucket/file.md")

        assert content == "Success after retry"
        assert mock_s3_client.get_object.call_count == 2
        mock_sleep.assert_called_once()  # Should sleep once before retry

    @patch("carver_feeds.s3_client.boto3")
    @patch("carver_feeds.s3_client.time.sleep")
    def test_fetch_content_retry_exhausted(self, mock_sleep, mock_boto3):
        """Test fetch that fails after exhausting retries."""
        from botocore.exceptions import ClientError

        mock_s3_client = Mock()
        error_response = {"Error": {"Code": "ServiceUnavailable"}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test", max_retries=3)
        content = client.fetch_content("s3://bucket/file.md")

        assert content is None
        assert mock_s3_client.get_object.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_size_check_too_large(self, mock_boto3):
        """Test fetch when content size exceeds limit."""
        mock_s3_client = Mock()
        # Return content larger than 10MB limit
        mock_s3_client.head_object.return_value = {"ContentLength": MAX_CONTENT_SIZE_BYTES + 1}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/huge-file.md")

        assert content is None
        mock_s3_client.get_object.assert_not_called()  # Should not fetch

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_custom_max_size(self, mock_boto3):
        """Test fetch with custom maximum size limit."""
        mock_s3_client = Mock()
        mock_s3_client.head_object.return_value = {"ContentLength": 2 * 1024 * 1024}  # 2MB

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/file.md", max_size_mb=1)

        assert content is None  # Should reject 2MB file with 1MB limit

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_truncate_if_exceeds_limit_on_read(self, mock_boto3):
        """Test that content is truncated if it exceeds limit during read."""
        mock_s3_client = Mock()
        mock_body = Mock()
        # Return content larger than requested (simulating size mismatch)
        large_content = b"x" * (5 * 1024 * 1024 + 100)  # 5MB + 100 bytes
        mock_body.read.return_value = large_content

        mock_s3_client.get_object.return_value = {"Body": mock_body}
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}  # Wrong size reported

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/file.md", max_size_mb=5)

        # Should truncate to max_size_mb
        assert len(content) == 5 * 1024 * 1024

    @patch("carver_feeds.s3_client.boto3")
    def test_fetch_content_head_object_fails_gracefully(self, mock_boto3):
        """Test that fetch continues if head_object fails."""
        mock_s3_client = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b"Content fetched successfully"

        # head_object fails but get_object succeeds
        mock_s3_client.head_object.side_effect = Exception("Head failed")
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/file.md")

        assert content == "Content fetched successfully"

    @patch("carver_feeds.s3_client.boto3")
    @patch("carver_feeds.s3_client.time.sleep")
    def test_fetch_content_generic_exception_with_retry(self, mock_sleep, mock_boto3):
        """Test fetch with generic exception that retries."""
        mock_s3_client = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b"Success after generic error"

        # First call raises generic exception, second succeeds
        mock_s3_client.get_object.side_effect = [
            RuntimeError("Network error"),
            {"Body": mock_body},
        ]
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        content = client.fetch_content("s3://bucket/file.md")

        assert content == "Success after generic error"
        assert mock_s3_client.get_object.call_count == 2


class TestBatchFetching:
    """Test batch content fetching."""

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_success_multiple_files(self, mock_boto3):
        """Test successful batch fetch of multiple files."""
        mock_s3_client = Mock()

        # Setup responses for multiple files
        def mock_get_object(Bucket, Key):
            content_map = {
                "file1.md": b"Content 1",
                "file2.md": b"Content 2",
                "dir/file3.md": b"Content 3",
            }
            mock_body = Mock()
            mock_body.read.return_value = content_map.get(Key, b"Unknown")
            return {"Body": mock_body}

        mock_s3_client.get_object.side_effect = mock_get_object
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        # Test
        client = S3ContentClient(profile_name="test")
        paths = [
            "s3://bucket/file1.md",
            "s3://bucket/file2.md",
            "s3://bucket/dir/file3.md",
        ]
        results = client.fetch_content_batch(paths)

        assert len(results) == 3
        assert results["s3://bucket/file1.md"] == "Content 1"
        assert results["s3://bucket/file2.md"] == "Content 2"
        assert results["s3://bucket/dir/file3.md"] == "Content 3"

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_empty_list(self, mock_boto3):
        """Test batch fetch with empty path list."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        results = client.fetch_content_batch([])

        assert results == {}
        mock_s3_client.get_object.assert_not_called()

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_mixed_success_failure(self, mock_boto3):
        """Test batch fetch with some successes and some failures."""
        from botocore.exceptions import ClientError

        mock_s3_client = Mock()

        def mock_get_object(Bucket, Key):
            if Key == "missing.md":
                error_response = {"Error": {"Code": "NoSuchKey"}}
                raise ClientError(error_response, "GetObject")
            mock_body = Mock()
            mock_body.read.return_value = b"Success content"
            return {"Body": mock_body}

        mock_s3_client.get_object.side_effect = mock_get_object
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        paths = ["s3://bucket/exists.md", "s3://bucket/missing.md"]
        results = client.fetch_content_batch(paths)

        assert len(results) == 2
        assert results["s3://bucket/exists.md"] == "Success content"
        assert results["s3://bucket/missing.md"] is None

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_all_failures(self, mock_boto3):
        """Test batch fetch where all fetches fail."""
        from botocore.exceptions import ClientError

        mock_s3_client = Mock()
        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, "GetObject")
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        paths = ["s3://bucket/file1.md", "s3://bucket/file2.md"]
        results = client.fetch_content_batch(paths)

        assert len(results) == 2
        assert results["s3://bucket/file1.md"] is None
        assert results["s3://bucket/file2.md"] is None

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_invalid_max_workers(self, mock_boto3):
        """Test batch fetch with invalid max_workers parameter."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")

        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            client.fetch_content_batch(["s3://bucket/file.md"], max_workers=0)

        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            client.fetch_content_batch(["s3://bucket/file.md"], max_workers=-5)

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_max_workers_capped(self, mock_boto3):
        """Test that max_workers is capped at reasonable limit."""
        mock_s3_client = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b"Content"
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")

        # Should not raise error, just cap the value
        results = client.fetch_content_batch(["s3://bucket/file.md"], max_workers=1000)

        assert len(results) == 1

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_timeout_handling(self, mock_boto3):
        """Test batch fetch with timeout on individual fetch."""
        from concurrent.futures import Future, TimeoutError as FutureTimeoutError

        mock_s3_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")

        # Mock a future that times out
        with patch("carver_feeds.s3_client.ThreadPoolExecutor") as mock_executor:
            mock_future = Mock(spec=Future)
            mock_future.result.side_effect = FutureTimeoutError()

            mock_executor_instance = Mock()
            mock_executor_instance.__enter__ = Mock(return_value=mock_executor_instance)
            mock_executor_instance.__exit__ = Mock(return_value=False)
            mock_executor_instance.submit.return_value = mock_future
            mock_executor.return_value = mock_executor_instance

            # Need to mock as_completed to return our future
            with patch("carver_feeds.s3_client.as_completed") as mock_as_completed:
                mock_as_completed.return_value = [mock_future]

                results = client.fetch_content_batch(["s3://bucket/file.md"])

                assert results["s3://bucket/file.md"] is None

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_keyboard_interrupt(self, mock_boto3):
        """Test that KeyboardInterrupt is properly propagated."""
        mock_s3_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")

        with patch("carver_feeds.s3_client.ThreadPoolExecutor") as mock_executor:
            mock_executor_instance = Mock()
            mock_executor_instance.__enter__ = Mock(side_effect=KeyboardInterrupt())
            mock_executor_instance.__exit__ = Mock(return_value=False)
            mock_executor.return_value = mock_executor_instance

            with pytest.raises(KeyboardInterrupt):
                client.fetch_content_batch(["s3://bucket/file.md"])

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_fatal_error(self, mock_boto3):
        """Test batch fetch with fatal error in executor."""
        mock_s3_client = Mock()
        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")

        with patch("carver_feeds.s3_client.ThreadPoolExecutor") as mock_executor:
            mock_executor_instance = Mock()
            mock_executor_instance.__enter__ = Mock(side_effect=RuntimeError("Fatal error"))
            mock_executor_instance.__exit__ = Mock(return_value=False)
            mock_executor.return_value = mock_executor_instance

            with pytest.raises(S3FetchError, match="Batch fetch failed"):
                client.fetch_content_batch(["s3://bucket/file.md"])

    @patch("carver_feeds.s3_client.boto3")
    def test_batch_fetch_custom_max_workers(self, mock_boto3):
        """Test batch fetch with custom max_workers setting."""
        mock_s3_client = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b"Content"
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        mock_s3_client.head_object.return_value = {"ContentLength": 100}

        mock_session = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = S3ContentClient(profile_name="test")
        paths = ["s3://bucket/file1.md", "s3://bucket/file2.md"]

        results = client.fetch_content_batch(paths, max_workers=2)

        assert len(results) == 2


class TestFactoryFunction:
    """Test get_s3_client factory function."""

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "test-profile"})
    def test_factory_from_env_with_profile(self, mock_boto3):
        """Test factory function with AWS_PROFILE_NAME in environment."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = get_s3_client()

        assert client is not None
        assert client.profile_name == "test-profile"

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "test-profile", "AWS_REGION": "eu-west-1"})
    def test_factory_from_env_with_region(self, mock_boto3):
        """Test factory function with custom AWS_REGION."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = get_s3_client()

        assert client is not None
        assert client.region_name == "eu-west-1"

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {}, clear=True)
    def test_factory_without_profile_returns_none(self, mock_boto3):
        """Test factory function returns None when AWS_PROFILE_NAME not set."""
        # Pass load_from_env=False to prevent loading from .env file
        client = get_s3_client(load_from_env=False)

        assert client is None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "invalid-profile"})
    def test_factory_with_invalid_profile_returns_none(self, mock_boto3):
        """Test factory function returns None gracefully for invalid profile."""
        from botocore.exceptions import ProfileNotFound

        mock_boto3.Session.side_effect = ProfileNotFound(profile="invalid-profile")

        client = get_s3_client()

        assert client is None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "test-profile"})
    def test_factory_with_credentials_error_returns_none(self, mock_boto3):
        """Test factory function returns None for credentials errors."""
        from botocore.exceptions import NoCredentialsError

        mock_boto3.Session.side_effect = NoCredentialsError()

        client = get_s3_client()

        assert client is None

    @patch("carver_feeds.s3_client.BOTO3_AVAILABLE", False)
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "test-profile"})
    def test_factory_without_boto3_returns_none(self):
        """Test factory function returns None when boto3 is not installed."""
        client = get_s3_client()

        assert client is None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "test-profile"})
    def test_factory_with_load_dotenv(self, mock_boto3):
        """Test factory function calls load_dotenv by default."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        with patch("carver_feeds.s3_client.load_dotenv") as mock_load_dotenv:
            client = get_s3_client(load_from_env=True)

            mock_load_dotenv.assert_called_once()
            assert client is not None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "test-profile"})
    def test_factory_skip_load_dotenv(self, mock_boto3):
        """Test factory function can skip load_dotenv."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        with patch("carver_feeds.s3_client.load_dotenv") as mock_load_dotenv:
            client = get_s3_client(load_from_env=False)

            mock_load_dotenv.assert_not_called()
            assert client is not None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_PROFILE_NAME": "test-profile"})
    def test_factory_unexpected_error_returns_none(self, mock_boto3):
        """Test factory function handles unexpected errors gracefully."""
        mock_boto3.Session.side_effect = RuntimeError("Unexpected error")

        client = get_s3_client()

        assert client is None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict(
        "os.environ",
        {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        },
    )
    def test_factory_from_env_with_credentials(self, mock_boto3):
        """Test factory function with AWS credentials in environment."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = get_s3_client(load_from_env=False)

        assert client is not None
        assert client.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert client.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        mock_boto3.Session.assert_called_once_with(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region_name="us-east-1",
        )

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict(
        "os.environ",
        {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AWS_REGION": "ap-southeast-1",
        },
    )
    def test_factory_from_env_with_credentials_and_region(self, mock_boto3):
        """Test factory function with credentials and custom region."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = get_s3_client(load_from_env=False)

        assert client is not None
        assert client.region_name == "ap-southeast-1"

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict(
        "os.environ",
        {
            "AWS_PROFILE_NAME": "test-profile",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        },
    )
    def test_factory_profile_takes_priority_over_credentials(self, mock_boto3):
        """Test that profile takes priority over credentials in factory."""
        mock_session = Mock()
        mock_s3_client = Mock()
        mock_session.client.return_value = mock_s3_client
        mock_boto3.Session.return_value = mock_session

        client = get_s3_client(load_from_env=False)

        assert client is not None
        assert client.profile_name == "test-profile"
        # Verify profile authentication was used (not credentials)
        mock_boto3.Session.assert_called_once_with(
            profile_name="test-profile", region_name="us-east-1"
        )

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE"})
    def test_factory_only_access_key_returns_none(self, mock_boto3):
        """Test factory returns None when only access key provided."""
        client = get_s3_client(load_from_env=False)

        assert client is None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict("os.environ", {"AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"})
    def test_factory_only_secret_key_returns_none(self, mock_boto3):
        """Test factory returns None when only secret key provided."""
        client = get_s3_client(load_from_env=False)

        assert client is None

    @patch("carver_feeds.s3_client.boto3")
    @patch.dict(
        "os.environ",
        {
            "AWS_ACCESS_KEY_ID": "INVALID",
            "AWS_SECRET_ACCESS_KEY": "INVALID",
        },
    )
    def test_factory_with_invalid_credentials_returns_none(self, mock_boto3):
        """Test factory returns None gracefully for invalid credentials."""
        from botocore.exceptions import NoCredentialsError

        mock_boto3.Session.side_effect = NoCredentialsError()

        client = get_s3_client(load_from_env=False)

        assert client is None
