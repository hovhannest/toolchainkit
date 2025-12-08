"""
Remote cache backend configuration for distributed build caching.

This module provides configuration for remote cache backends (S3, Redis, HTTP,
Memcached, GCS) that enable teams to share build cache across multiple machines.

Usage:
    from toolchainkit.caching.detection import BuildCacheManager
    from toolchainkit.caching.remote import RemoteCacheConfig, RemoteCacheConfigurator

    # Get cache tool
    manager = BuildCacheManager()
    cache_config = manager.get_or_install()

    # Configure S3 remote backend
    remote_config = RemoteCacheConfig(
        backend_type='s3',
        bucket='my-build-cache',
        region='us-east-1',
        credentials={'access_key': 'AKIA...', 'secret_key': '***'}
    )

    # Create configurator
    configurator = RemoteCacheConfigurator(cache_config)
    env_vars = configurator.configure(remote_config)

    # Use env_vars in build environment
    import os
    os.environ.update(env_vars)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from .detection import BuildCacheConfig

logger = logging.getLogger(__name__)


@dataclass
class RemoteCacheConfig:
    """
    Remote cache backend configuration.

    Attributes:
        backend_type: Backend type ('s3', 'redis', 'http', 'memcached', 'gcs')
        endpoint: Connection endpoint or bucket name
        credentials: Authentication credentials (keys vary by backend)
        bucket: S3/GCS bucket name (for S3/GCS backends)
        region: AWS region (for S3 backend)
        prefix: Key/object prefix for namespacing
        use_ssl: Use SSL/TLS connections
        extra_config: Additional backend-specific configuration

    Example:
        >>> config = RemoteCacheConfig(
        ...     backend_type='s3',
        ...     bucket='my-build-cache',
        ...     region='us-east-1',
        ...     credentials={'access_key': 'AKIA...', 'secret_key': '***'}
        ... )
    """

    backend_type: str
    endpoint: str = ""
    credentials: Optional[Dict[str, str]] = None
    bucket: Optional[str] = None
    region: Optional[str] = "us-east-1"
    prefix: Optional[str] = None
    use_ssl: bool = True
    extra_config: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_backends = {"s3", "redis", "http", "memcached", "gcs"}
        if self.backend_type not in valid_backends:
            raise ValueError(
                f"Invalid backend_type: {self.backend_type}. "
                f"Must be one of: {', '.join(valid_backends)}"
            )

        # Backend-specific validation
        if self.backend_type in ("s3", "gcs") and not self.bucket:
            raise ValueError(f"{self.backend_type} backend requires 'bucket' parameter")

        if self.backend_type in ("redis", "http") and not self.endpoint:
            raise ValueError(
                f"{self.backend_type} backend requires 'endpoint' parameter"
            )


class SecureCredentialHandler:
    """Handle credentials securely without logging sensitive data."""

    # Sensitive environment variable keys
    SENSITIVE_KEYS = {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "SCCACHE_REDIS_PASSWORD",
        "SCCACHE_HTTP_TOKEN",
        "GCS_CREDENTIALS_PATH",
    }

    @classmethod
    def sanitize_for_logging(cls, env_vars: Dict[str, str]) -> Dict[str, str]:
        """
        Remove sensitive values for safe logging.

        Args:
            env_vars: Environment variables dictionary

        Returns:
            Dictionary with sensitive values redacted
        """
        sanitized = {}
        for key, value in env_vars.items():
            if (
                key in cls.SENSITIVE_KEYS
                or "password" in key.lower()
                or "secret" in key.lower()
            ):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def validate_credentials(
        backend_type: str, credentials: Optional[Dict[str, str]]
    ) -> bool:
        """
        Validate credentials are present and correctly formatted.

        Args:
            backend_type: Type of backend
            credentials: Credentials dictionary

        Returns:
            True if credentials are valid
        """
        if credentials is None:
            return True  # Credentials optional for some backends

        if backend_type == "s3":
            # S3 requires both access_key and secret_key if credentials provided
            if credentials:
                required = {"access_key", "secret_key"}
                if not required.issubset(credentials.keys()):
                    logger.warning(f"S3 credentials incomplete. Required: {required}")
                    return False

        elif backend_type == "redis":
            # Redis may have password
            pass  # No strict validation

        return True


class RemoteCacheConfigurator:
    """
    Configure remote caching backends for distributed build caching.

    Supports multiple backends:
    - **S3**: AWS S3 and S3-compatible storage (MinIO, DigitalOcean Spaces, Wasabi)
    - **Redis**: In-memory distributed cache
    - **HTTP**: Custom HTTP cache servers
    - **Memcached**: Distributed memory caching system
    - **GCS**: Google Cloud Storage

    Attributes:
        cache_config: Base build cache configuration
    """

    def __init__(self, cache_config: BuildCacheConfig):
        """
        Initialize remote cache configurator.

        Args:
            cache_config: BuildCacheConfig from detection module
        """
        if cache_config is None:
            raise ValueError("cache_config cannot be None")

        self.cache_config = cache_config
        logger.info(f"Initialized RemoteCacheConfigurator for {cache_config.tool}")

    def configure(self, remote_config: RemoteCacheConfig) -> Dict[str, str]:
        """
        Configure remote backend based on type.

        Args:
            remote_config: Remote cache configuration

        Returns:
            Dictionary of environment variables for the backend

        Raises:
            ValueError: If backend type not supported
        """
        if remote_config.backend_type == "s3":
            return self.configure_s3(remote_config)
        elif remote_config.backend_type == "redis":
            return self.configure_redis(remote_config)
        elif remote_config.backend_type == "http":
            return self.configure_http(remote_config)
        elif remote_config.backend_type == "memcached":
            return self.configure_memcached(remote_config)
        elif remote_config.backend_type == "gcs":
            return self.configure_gcs(remote_config)
        else:
            raise ValueError(f"Unsupported backend: {remote_config.backend_type}")

    def configure_s3(self, config: RemoteCacheConfig) -> Dict[str, str]:
        """
        Configure S3 backend for sccache.

        Supports AWS S3 and S3-compatible storage (MinIO, DigitalOcean Spaces, etc.).

        Environment Variables:
        - SCCACHE_BUCKET: S3 bucket name
        - SCCACHE_REGION: AWS region
        - SCCACHE_ENDPOINT: Custom S3 endpoint (for S3-compatible storage)
        - SCCACHE_S3_USE_SSL: Use SSL for S3 connections
        - AWS_ACCESS_KEY_ID: AWS access key
        - AWS_SECRET_ACCESS_KEY: AWS secret key

        Args:
            config: RemoteCacheConfig with S3 settings

        Returns:
            Dictionary of environment variables
        """
        env_vars = {
            "SCCACHE_BUCKET": config.bucket,
            "SCCACHE_S3_USE_SSL": "true" if config.use_ssl else "false",
        }

        # Region (default: us-east-1)
        if config.region:
            env_vars["SCCACHE_REGION"] = config.region

        # Custom endpoint for S3-compatible storage (MinIO, etc.)
        if config.endpoint:
            env_vars["SCCACHE_ENDPOINT"] = config.endpoint

        # Credentials
        if config.credentials:
            if "access_key" in config.credentials:
                env_vars["AWS_ACCESS_KEY_ID"] = config.credentials["access_key"]
            if "secret_key" in config.credentials:
                env_vars["AWS_SECRET_ACCESS_KEY"] = config.credentials["secret_key"]

        # Key prefix for namespacing
        if config.prefix:
            env_vars["SCCACHE_S3_KEY_PREFIX"] = config.prefix

        # Extra config
        env_vars.update(config.extra_config)

        # Log (sanitized)
        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)
        logger.debug(f"Configured S3 backend: {sanitized}")

        return env_vars

    def configure_redis(self, config: RemoteCacheConfig) -> Dict[str, str]:
        """
        Configure Redis backend for sccache.

        Environment Variables:
        - SCCACHE_REDIS: Redis connection string (redis://host:port)
        - SCCACHE_REDIS_PASSWORD: Redis password
        - SCCACHE_REDIS_DB: Database number (default: 0)
        - SCCACHE_REDIS_KEY_PREFIX: Key prefix for namespacing
        - SCCACHE_REDIS_TTL: Key TTL in seconds

        Args:
            config: RemoteCacheConfig with Redis settings

        Returns:
            Dictionary of environment variables
        """
        env_vars = {
            "SCCACHE_REDIS": config.endpoint,
        }

        # Password
        if config.credentials and "password" in config.credentials:
            env_vars["SCCACHE_REDIS_PASSWORD"] = config.credentials["password"]

        # Database number
        if "db" in config.extra_config:
            env_vars["SCCACHE_REDIS_DB"] = config.extra_config["db"]

        # Key prefix
        if config.prefix:
            env_vars["SCCACHE_REDIS_KEY_PREFIX"] = config.prefix

        # TTL
        if "ttl" in config.extra_config:
            env_vars["SCCACHE_REDIS_TTL"] = config.extra_config["ttl"]

        # Extra config
        env_vars.update(
            {k: v for k, v in config.extra_config.items() if k not in ("db", "ttl")}
        )

        # Log (sanitized)
        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)
        logger.debug(f"Configured Redis backend: {sanitized}")

        return env_vars

    def configure_http(self, config: RemoteCacheConfig) -> Dict[str, str]:
        """
        Configure HTTP backend for sccache.

        Environment Variables:
        - SCCACHE_ENDPOINT: HTTP server endpoint
        - SCCACHE_HTTP_TOKEN: Authentication token

        Args:
            config: RemoteCacheConfig with HTTP settings

        Returns:
            Dictionary of environment variables
        """
        env_vars = {
            "SCCACHE_ENDPOINT": config.endpoint,
        }

        # Authentication token
        if config.credentials and "token" in config.credentials:
            env_vars["SCCACHE_HTTP_TOKEN"] = config.credentials["token"]

        # Extra config
        env_vars.update(config.extra_config)

        # Log (sanitized)
        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)
        logger.debug(f"Configured HTTP backend: {sanitized}")

        return env_vars

    def configure_memcached(self, config: RemoteCacheConfig) -> Dict[str, str]:
        """
        Configure Memcached backend for sccache.

        Environment Variables:
        - SCCACHE_MEMCACHED: Memcached endpoints (comma-separated)
        - SCCACHE_MEMCACHED_KEY_PREFIX: Key prefix for namespacing

        Args:
            config: RemoteCacheConfig with Memcached settings

        Returns:
            Dictionary of environment variables
        """
        # Endpoint can be single or comma-separated list
        env_vars = {
            "SCCACHE_MEMCACHED": config.endpoint,
        }

        # Key prefix
        if config.prefix:
            env_vars["SCCACHE_MEMCACHED_KEY_PREFIX"] = config.prefix

        # Extra config
        env_vars.update(config.extra_config)

        logger.debug(f"Configured Memcached backend: {env_vars}")

        return env_vars

    def configure_gcs(self, config: RemoteCacheConfig) -> Dict[str, str]:
        """
        Configure Google Cloud Storage backend for sccache.

        Environment Variables:
        - SCCACHE_GCS_BUCKET: GCS bucket name
        - SCCACHE_GCS_CREDENTIALS_PATH: Service account JSON file path
        - SCCACHE_GCS_KEY_PREFIX: Object key prefix
        - SCCACHE_GCS_RW_MODE: Read-write mode (READ_ONLY, READ_WRITE)

        Args:
            config: RemoteCacheConfig with GCS settings

        Returns:
            Dictionary of environment variables
        """
        env_vars = {
            "SCCACHE_GCS_BUCKET": config.bucket,
        }

        # Credentials file
        if config.credentials and "credentials_file" in config.credentials:
            creds_path = config.credentials["credentials_file"]
            env_vars["SCCACHE_GCS_CREDENTIALS_PATH"] = creds_path

        # Key prefix
        if config.prefix:
            env_vars["SCCACHE_GCS_KEY_PREFIX"] = config.prefix

        # Read-write mode
        if "rw_mode" in config.extra_config:
            env_vars["SCCACHE_GCS_RW_MODE"] = config.extra_config["rw_mode"]

        # Extra config
        env_vars.update(
            {k: v for k, v in config.extra_config.items() if k != "rw_mode"}
        )

        # Log (sanitized)
        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)
        logger.debug(f"Configured GCS backend: {sanitized}")

        return env_vars

    def get_all_env_vars(
        self, remote_config: Optional[RemoteCacheConfig] = None
    ) -> Dict[str, str]:
        """
        Get all environment variables including local + remote.

        Combines launcher environment variables with remote backend variables.

        Args:
            remote_config: Optional remote cache configuration

        Returns:
            Dictionary with all environment variables
        """
        # Get local cache environment from launcher
        from .launcher import CompilerLauncherConfig

        launcher = CompilerLauncherConfig(self.cache_config)
        env_vars = launcher.configure_environment()

        # Add remote backend if configured
        if remote_config:
            remote_env = self.configure(remote_config)
            env_vars.update(remote_env)

        return env_vars

    def test_connection(self, config: RemoteCacheConfig) -> Tuple[bool, Optional[str]]:
        """
        Test remote cache connectivity.

        Attempts a minimal connection test appropriate for the backend type.

        Args:
            config: Remote cache configuration

        Returns:
            Tuple of (success, error_message)

        Example:
            >>> success, error = configurator.test_connection(remote_config)
            >>> if not success:
            ...     print(f"Connection failed: {error}")
        """
        try:
            if config.backend_type == "s3":
                return self._test_s3_connection(config)
            elif config.backend_type == "redis":
                return self._test_redis_connection(config)
            elif config.backend_type == "http":
                return self._test_http_connection(config)
            elif config.backend_type == "memcached":
                return self._test_memcached_connection(config)
            elif config.backend_type == "gcs":
                return self._test_gcs_connection(config)
            else:
                return False, f"Unknown backend type: {config.backend_type}"

        except Exception as e:
            logger.error(f"Connection test failed: {e}", exc_info=True)
            return False, str(e)

    def _test_s3_connection(
        self, config: RemoteCacheConfig
    ) -> Tuple[bool, Optional[str]]:
        """Test S3 connection by attempting to list bucket."""
        try:
            import boto3
            from botocore.exceptions import (  # noqa: F401
                BotoCoreError,
                ClientError,
            )

            # Create S3 client
            s3_config = {}
            if config.endpoint:
                s3_config["endpoint_url"] = config.endpoint
            if config.region:
                s3_config["region_name"] = config.region

            if config.credentials:
                s3_config["aws_access_key_id"] = config.credentials.get("access_key")
                s3_config["aws_secret_access_key"] = config.credentials.get(
                    "secret_key"
                )

            s3 = boto3.client("s3", **s3_config)

            # Try to list objects (minimal permissions required)
            s3.list_objects_v2(Bucket=config.bucket, MaxKeys=1)

            return True, None

        except ImportError:
            logger.warning("boto3 not installed, skipping S3 connection test")
            return True, None  # Assume it will work
        except Exception as e:
            return False, f"S3 connection failed: {e}"

    def _test_redis_connection(
        self, config: RemoteCacheConfig
    ) -> Tuple[bool, Optional[str]]:
        """Test Redis connection with PING command."""
        try:
            import redis  # type: ignore[import-untyped]

            # Parse Redis URL
            url_parts = urlparse(config.endpoint)
            host = url_parts.hostname or "localhost"
            port = url_parts.port or 6379

            password = None
            if config.credentials:
                password = config.credentials.get("password")

            # Create Redis client
            r = redis.Redis(host=host, port=port, password=password, socket_timeout=5)

            # Test connection
            r.ping()

            return True, None

        except Exception as e:
            return False, f"Redis connection failed: {e}"

    def _test_http_connection(
        self, config: RemoteCacheConfig
    ) -> Tuple[bool, Optional[str]]:
        """Test HTTP connection with HEAD request."""
        try:
            import requests

            headers = {}
            if config.credentials and "token" in config.credentials:
                headers["Authorization"] = f"Bearer {config.credentials['token']}"

            response = requests.head(config.endpoint, headers=headers, timeout=10)

            if response.status_code < 400:
                return True, None
            else:
                return False, f"HTTP {response.status_code}"

        except ImportError:
            logger.warning("requests not installed, skipping HTTP connection test")
            return True, None
        except Exception as e:
            return False, f"HTTP connection failed: {e}"

    def _test_memcached_connection(
        self, config: RemoteCacheConfig
    ) -> Tuple[bool, Optional[str]]:
        """Test Memcached connection."""
        try:
            import pymemcache  # type: ignore[import-not-found]  # noqa: F401
            from pymemcache.client.base import Client  # type: ignore[import-not-found]

            # Parse first endpoint
            endpoints = config.endpoint.split(",")
            first_endpoint = endpoints[0].strip()

            host_port = first_endpoint.split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 11211

            client = Client((host, port), timeout=5)
            client.stats()

            return True, None

        except ImportError:
            logger.warning(
                "pymemcache not installed, skipping Memcached connection test"
            )
            return True, None
        except Exception as e:
            return False, f"Memcached connection failed: {e}"

    def _test_gcs_connection(
        self, config: RemoteCacheConfig
    ) -> Tuple[bool, Optional[str]]:
        """Test GCS connection by listing bucket."""
        try:
            from google.cloud import storage
            from google.auth.exceptions import GoogleAuthError  # noqa: F401

            # Create GCS client
            if config.credentials and "credentials_file" in config.credentials:
                client = storage.Client.from_service_account_json(
                    config.credentials["credentials_file"]
                )
            else:
                client = storage.Client()

            # Try to get bucket
            bucket = client.get_bucket(config.bucket)
            list(bucket.list_blobs(max_results=1))

            return True, None

        except ImportError:
            logger.warning(
                "google-cloud-storage not installed, skipping GCS connection test"
            )
            return True, None
        except Exception as e:
            return False, f"GCS connection failed: {e}"
