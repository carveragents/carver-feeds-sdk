"""
S3 Content Client Module

This module provides functionality to fetch entry content from AWS S3.
Content is no longer returned directly by the Carver API and must be
fetched from S3 using paths in the extracted_metadata field.

Example:
    Basic usage with AWS profile from environment:

    >>> from carver_feeds import get_s3_client
    >>> s3 = get_s3_client()
    >>> content = s3.fetch_content('s3://bucket/path/content.md')

    Direct instantiation with specific profile:

    >>> from carver_feeds import S3ContentClient
    >>> s3 = S3ContentClient(profile_name='carver-prod', region_name='us-east-1')
    >>> content = s3.fetch_content('s3://bucket/path/content.md')

    Batch fetching for performance:

    >>> s3_paths = ['s3://bucket/path1.md', 's3://bucket/path2.md']
    >>> content_map = s3.fetch_content_batch(s3_paths)
"""

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

# Try importing boto3, handle gracefully if not available
try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        NoCredentialsError,
        ProfileNotFound,
    )

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None  # type: ignore
    Config = None  # type: ignore
    # Create placeholder exception types for type checking
    ClientError = type("ClientError", (Exception,), {})  # type: ignore
    NoCredentialsError = type("NoCredentialsError", (Exception,), {})  # type: ignore
    ProfileNotFound = type("ProfileNotFound", (Exception,), {})  # type: ignore
    BotoCoreError = type("BotoCoreError", (Exception,), {})  # type: ignore


# Configure module logger
logger = logging.getLogger(__name__)


# S3 Configuration Constants
DEFAULT_REGION = "us-east-1"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_MAX_WORKERS = 10
DEFAULT_S3_TIMEOUT = 60  # Longer than API timeout for large content files
MAX_CONTENT_SIZE_MB = 10  # Maximum file size to fetch
MAX_CONTENT_SIZE_BYTES = MAX_CONTENT_SIZE_MB * 1024 * 1024
BATCH_PROGRESS_LOG_INTERVAL = 10  # Log every N completions


class S3Error(Exception):
    """Base exception for S3 operations."""

    pass


class S3CredentialsError(S3Error):
    """Missing or invalid S3 credentials."""

    pass


class S3FetchError(S3Error):
    """Failed to fetch content from S3."""

    pass


class S3ContentClient:
    """
    Client for fetching entry content from AWS S3.

    This client supports two authentication methods:
    1. AWS profile from ~/.aws/credentials (profile_name)
    2. Direct AWS credentials (aws_access_key_id, aws_secret_access_key)

    Supports batch fetching with parallel requests for performance.

    Args:
        profile_name: AWS profile name from ~/.aws/credentials (reads from
            AWS_PROFILE_NAME env if None). Takes priority over direct credentials.
        aws_access_key_id: AWS access key ID for direct authentication. Used if
            profile_name is not provided.
        aws_secret_access_key: AWS secret access key for direct authentication.
            Required if aws_access_key_id is provided.
        region_name: AWS region (reads from AWS_REGION env if None, default: us-east-1)
        max_retries: Maximum number of retries for failed fetches (default: 3)
        initial_retry_delay: Initial delay in seconds for retry backoff (default: 1.0)

    Raises:
        S3CredentialsError: If AWS credentials are not configured properly
        ImportError: If boto3 is not installed

    Example:
        >>> # Method 1: Profile-based authentication
        >>> s3 = S3ContentClient(profile_name='carver-prod')
        >>> content = s3.fetch_content('s3://bucket/key/content.md')
        >>>
        >>> # Method 2: Direct credential authentication
        >>> s3 = S3ContentClient(
        ...     aws_access_key_id='AKIAIOSFODNN7EXAMPLE',
        ...     aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        ... )
        >>> content = s3.fetch_content('s3://bucket/key/content.md')
    """

    def __init__(
        self,
        profile_name: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_retry_delay: float = DEFAULT_RETRY_DELAY,
    ):
        """Initialize S3 client with AWS credentials."""
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3 content fetching. " "Install it with: pip install boto3"
            )

        self.profile_name = profile_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name or DEFAULT_REGION
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self._s3_client = None

        # Initialize S3 client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize boto3 S3 client with profile or credential authentication."""
        try:
            # Priority 1: Profile authentication
            if self.profile_name:
                logger.info(f"Initializing S3 client with profile: {self.profile_name}")
                session = boto3.Session(
                    profile_name=self.profile_name, region_name=self.region_name
                )
            # Priority 2: Direct credential authentication
            elif self.aws_access_key_id and self.aws_secret_access_key:
                logger.info("Initializing S3 client with direct AWS credentials")
                session = boto3.Session(
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name,
                )
            # Priority 3: No credentials provided
            else:
                raise S3CredentialsError(
                    "AWS credentials not configured. Please provide either:\n"
                    "1. profile_name (AWS profile from ~/.aws/credentials), or\n"
                    "2. aws_access_key_id and aws_secret_access_key (direct credentials)\n"
                    "See: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html"
                )

            # Configure S3 client with timeouts
            config = Config(
                connect_timeout=10,
                read_timeout=DEFAULT_S3_TIMEOUT,
                retries={"max_attempts": 0},  # We handle retries manually
            )

            # Create S3 client
            self._s3_client = session.client("s3", config=config)
            logger.info(f"S3 client initialized successfully for region {self.region_name}")

        except ProfileNotFound as e:
            raise S3CredentialsError(
                f"AWS profile '{self.profile_name}' not found in ~/.aws/credentials. "
                f"Please configure the profile or update AWS_PROFILE_NAME. "
                f"See: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html"
            ) from e
        except NoCredentialsError as e:
            raise S3CredentialsError(
                "AWS credentials not found. Please configure either:\n"
                "1. AWS profile in ~/.aws/credentials with AWS_PROFILE_NAME env var, or\n"
                "2. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY env vars\n"
                "See: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html"
            ) from e
        except S3CredentialsError:
            # Re-raise our own exceptions without wrapping
            raise
        except Exception as e:
            raise S3CredentialsError(f"Failed to initialize S3 client: {e}") from e

    @staticmethod
    def parse_s3_path(s3_path: str) -> tuple[str, str]:
        """
        Parse S3 path into bucket and key components with validation.

        Args:
            s3_path: S3 URI in format s3://bucket/key/path

        Returns:
            Tuple of (bucket, key)

        Raises:
            ValueError: If S3 path format is invalid

        Example:
            >>> bucket, key = S3ContentClient.parse_s3_path('s3://my-bucket/path/to/file.txt')
            >>> print(bucket, key)
            my-bucket path/to/file.txt
        """
        if not s3_path or not isinstance(s3_path, str):
            raise ValueError(f"Invalid S3 path: {s3_path}")

        # Validate length
        if len(s3_path) > 1024:  # Reasonable limit
            raise ValueError(f"S3 path too long (max 1024 chars): {len(s3_path)}")

        # Match s3://bucket/key pattern with stricter validation
        # Bucket: lowercase alphanumeric, hyphens, dots (AWS S3 bucket naming rules)
        # Key: allow most chars but exclude control characters
        match = re.match(r"^s3://([a-z0-9][a-z0-9\-.]{1,61}[a-z0-9])/([^\x00-\x1f\x7f]+)$", s3_path)
        if not match:
            raise ValueError(
                f"Invalid S3 path format: {s3_path}. "
                f"Expected format: s3://bucket-name/key/path (bucket must follow AWS naming rules)"
            )

        bucket = match.group(1)
        key = match.group(2)

        # Additional validation - prevent path traversal attempts
        if ".." in key:
            raise ValueError(f"Invalid S3 key (contains '..'): {key}")

        return bucket, key

    def fetch_content(self, s3_path: str, max_size_mb: int | None = None) -> str | None:
        """
        Fetch content from S3 path with retry logic and size limits.

        Args:
            s3_path: S3 URI (e.g., s3://bucket/key/content.md)
            max_size_mb: Maximum file size in MB (default: 10MB)

        Returns:
            Content string, or None if fetch fails

        Example:
            >>> s3 = S3ContentClient(profile_name='carver-prod')
            >>> content = s3.fetch_content('s3://bucket/path/content.md')
            >>> if content:
            ...     print(f"Fetched {len(content)} characters")
        """
        if not s3_path:
            logger.error("Empty S3 path provided")
            return None

        max_size = (max_size_mb or MAX_CONTENT_SIZE_MB) * 1024 * 1024

        try:
            bucket, key = self.parse_s3_path(s3_path)

            # Retry loop
            for attempt in range(self.max_retries):
                try:
                    # Check content size before fetching
                    try:
                        assert self._s3_client is not None
                        head_response = self._s3_client.head_object(Bucket=bucket, Key=key)
                        content_length = head_response.get("ContentLength", 0)

                        if content_length > max_size:
                            logger.warning(
                                f"Content too large: {content_length} bytes (max: {max_size}). "
                                f"Skipping {s3_path}"
                            )
                            return None
                    except Exception as e:
                        logger.debug(f"Could not get content size for {s3_path}: {e}")

                    # Fetch object from S3
                    assert self._s3_client is not None
                    response = self._s3_client.get_object(Bucket=bucket, Key=key)

                    # Read with size limit
                    content_bytes = response["Body"].read(max_size + 1)  # Read one extra byte
                    if len(content_bytes) > max_size:
                        logger.warning(f"Content exceeds size limit, truncating: {s3_path}")
                        content_bytes = content_bytes[:max_size]

                    content = content_bytes.decode("utf-8")
                    logger.debug(f"Successfully fetched {len(content)} chars from {s3_path}")
                    return content

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")

                    # Permanent errors - don't retry
                    if error_code in [
                        "NoSuchKey",
                        "NoSuchBucket",
                        "AccessDenied",
                        "InvalidBucketName",
                    ]:
                        logger.warning(f"Permanent error for {s3_path}: {error_code}")
                        return None

                    # Transient errors - retry with backoff
                    if attempt < self.max_retries - 1:
                        delay = self.initial_retry_delay * (2**attempt)
                        logger.warning(
                            f"Transient error ({error_code}) for {s3_path}. "
                            f"Retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        logger.warning(
                            f"Permanent error after {self.max_retries} retries: {s3_path}"
                        )
                        return None

                except Exception as e:
                    if attempt < self.max_retries - 1:
                        delay = self.initial_retry_delay * (2**attempt)
                        logger.warning(f"Error fetching {s3_path}: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Failed to fetch {s3_path} after {self.max_retries} retries: {e}"
                        )
                        return None

        except ValueError as e:
            logger.error(f"Invalid S3 path format: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {s3_path}: {e}", exc_info=True)
            return None

    def fetch_content_batch(
        self, s3_paths: list[str], max_workers: int = DEFAULT_MAX_WORKERS
    ) -> dict[str, str | None]:
        """
        Fetch multiple contents from S3 in parallel.

        Uses ThreadPoolExecutor for concurrent fetches to improve performance.

        Args:
            s3_paths: List of S3 URIs to fetch
            max_workers: Maximum number of parallel workers (default: 10)

        Returns:
            Dict mapping S3 path to content (or None if fetch failed)

        Example:
            >>> s3 = S3ContentClient(profile_name='carver-prod')
            >>> paths = ['s3://bucket/path1.md', 's3://bucket/path2.md']
            >>> content_map = s3.fetch_content_batch(paths)
            >>> for path, content in content_map.items():
            ...     if content:
            ...         print(f"{path}: {len(content)} chars")
        """
        if not s3_paths:
            logger.warning("No S3 paths provided for batch fetch")
            return {}

        # Validate max_workers
        if max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {max_workers}")

        # Cap max_workers to reasonable limit
        max_workers = min(max_workers, 50)  # Prevent excessive thread creation

        logger.info(f"Batch fetching {len(s3_paths)} contents with {max_workers} workers...")
        results = {}

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all fetch tasks
                future_to_path = {
                    executor.submit(self.fetch_content, path): path for path in s3_paths
                }

                # Collect results as they complete
                completed = 0
                for future in as_completed(future_to_path):
                    path = future_to_path[future]
                    try:
                        results[path] = future.result(timeout=DEFAULT_S3_TIMEOUT)
                        completed += 1
                        if completed % BATCH_PROGRESS_LOG_INTERVAL == 0:
                            logger.info(f"Batch fetch progress: {completed}/{len(s3_paths)}")
                    except TimeoutError:
                        logger.warning(f"Timeout fetching {path}")
                        results[path] = None
                    except Exception as e:
                        logger.warning(f"Exception during batch fetch of {path}: {e}")
                        results[path] = None
        except KeyboardInterrupt:
            logger.warning("Batch fetch interrupted by user")
            raise
        except Exception as e:
            logger.error(f"Fatal error during batch fetch: {e}", exc_info=True)
            raise S3FetchError(f"Batch fetch failed: {e}") from e

        # Log summary
        success_count = sum(1 for content in results.values() if content is not None)
        logger.info(f"Batch fetch complete: {success_count}/{len(s3_paths)} successful")

        return results


def get_s3_client(load_from_env: bool = True) -> S3ContentClient | None:
    """
    Factory function to create S3 client from environment configuration.

    Supports multiple authentication methods with priority order:
    1. AWS profile (AWS_PROFILE_NAME) - highest priority
    2. Direct credentials (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)
    3. No credentials - returns None, SDK works without S3

    Environment variables:
    - AWS_PROFILE_NAME: AWS profile name from ~/.aws/credentials (priority 1)
    - AWS_ACCESS_KEY_ID: AWS access key for direct auth (priority 2)
    - AWS_SECRET_ACCESS_KEY: AWS secret key for direct auth (priority 2)
    - AWS_REGION: AWS region (optional, defaults to us-east-1)

    Args:
        load_from_env: If True, load .env file (default: True)

    Returns:
        S3ContentClient instance, or None if credentials not configured

    Example:
        >>> # With profile in environment
        >>> s3 = get_s3_client()
        >>> if s3:
        ...     content = s3.fetch_content('s3://bucket/path.md')
    """
    if not BOTO3_AVAILABLE:
        logger.error("boto3 is not installed. Install it with: pip install boto3")
        return None

    if load_from_env:
        load_dotenv()

    # Get configuration from environment
    profile_name = os.getenv("AWS_PROFILE_NAME")
    access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_REGION", DEFAULT_REGION)

    # Priority 1: Profile authentication
    if profile_name:
        try:
            return S3ContentClient(profile_name=profile_name, region_name=region_name)
        except S3CredentialsError as e:
            logger.error(f"Failed to create S3 client with profile: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating S3 client with profile: {e}")
            return None

    # Priority 2: Direct credential authentication
    if access_key_id and secret_access_key:
        try:
            return S3ContentClient(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region_name,
            )
        except S3CredentialsError as e:
            logger.error(f"Failed to create S3 client with credentials: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating S3 client with credentials: {e}")
            return None

    # Priority 3: No credentials configured
    logger.warning(
        "AWS credentials not configured. S3 content fetching disabled. "
        "To enable, configure either:\n"
        "1. AWS_PROFILE_NAME in .env and ~/.aws/credentials, or\n"
        "2. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env\n"
        "See: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html"
    )
    return None
