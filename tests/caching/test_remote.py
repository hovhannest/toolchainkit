"""
Unit tests for remote cache backend configuration.

Tests the RemoteCacheConfig and RemoteCacheConfigurator classes
for distributed build caching with S3, Redis, HTTP, Memcached, and GCS.
"""

import pytest

from toolchainkit.caching.detection import BuildCacheConfig
from toolchainkit.caching.remote import (
    RemoteCacheConfig,
    RemoteCacheConfigurator,
    SecureCredentialHandler,
)


# =============================================================================
# RemoteCacheConfig Tests
# =============================================================================


class TestRemoteCacheConfig:
    """Tests for RemoteCacheConfig dataclass."""

    def test_s3_config_creation(self):
        """Test creating S3 remote cache configuration."""
        config = RemoteCacheConfig(
            backend_type="s3",
            bucket="my-build-cache",
            region="us-east-1",
            credentials={"access_key": "AKIA...", "secret_key": "***"},
        )

        assert config.backend_type == "s3"
        assert config.bucket == "my-build-cache"
        assert config.region == "us-east-1"
        assert config.credentials["access_key"] == "AKIA..."

    def test_redis_config_creation(self):
        """Test creating Redis remote cache configuration."""
        config = RemoteCacheConfig(
            backend_type="redis",
            endpoint="redis://localhost:6379",
            credentials={"password": "secret"},
        )

        assert config.backend_type == "redis"
        assert config.endpoint == "redis://localhost:6379"
        assert config.credentials["password"] == "secret"

    def test_invalid_backend_type_raises_error(self):
        """Test that invalid backend type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid backend_type"):
            RemoteCacheConfig(backend_type="invalid", endpoint="http://example.com")

    def test_s3_without_bucket_raises_error(self):
        """Test that S3 configuration without bucket raises error."""
        with pytest.raises(ValueError, match="requires 'bucket'"):
            RemoteCacheConfig(backend_type="s3", region="us-east-1")

    def test_redis_without_endpoint_raises_error(self):
        """Test that Redis configuration without endpoint raises error."""
        with pytest.raises(ValueError, match="requires 'endpoint'"):
            RemoteCacheConfig(backend_type="redis")

    def test_http_config_creation(self):
        """Test creating HTTP remote cache configuration."""
        config = RemoteCacheConfig(
            backend_type="http",
            endpoint="https://cache.example.com",
            credentials={"token": "abc123"},
        )

        assert config.backend_type == "http"
        assert config.endpoint == "https://cache.example.com"

    def test_memcached_config_creation(self):
        """Test creating Memcached remote cache configuration."""
        config = RemoteCacheConfig(
            backend_type="memcached",
            endpoint="localhost:11211,server2:11211",
            prefix="buildcache:",
        )

        assert config.backend_type == "memcached"
        assert config.endpoint == "localhost:11211,server2:11211"
        assert config.prefix == "buildcache:"

    def test_gcs_config_creation(self):
        """Test creating GCS remote cache configuration."""
        config = RemoteCacheConfig(
            backend_type="gcs",
            bucket="my-gcs-cache",
            credentials={"credentials_file": "/path/to/service-account.json"},
        )

        assert config.backend_type == "gcs"
        assert config.bucket == "my-gcs-cache"


# =============================================================================
# SecureCredentialHandler Tests
# =============================================================================


class TestSecureCredentialHandler:
    """Tests for SecureCredentialHandler class."""

    def test_sanitize_aws_credentials(self):
        """Test that AWS credentials are sanitized."""
        env_vars = {
            "SCCACHE_BUCKET": "my-bucket",
            "AWS_ACCESS_KEY_ID": "AKIA...",
            "AWS_SECRET_ACCESS_KEY": "secret123",
            "SCCACHE_REGION": "us-east-1",
        }

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized["SCCACHE_BUCKET"] == "my-bucket"
        assert sanitized["SCCACHE_REGION"] == "us-east-1"
        assert sanitized["AWS_ACCESS_KEY_ID"] == "***REDACTED***"
        assert sanitized["AWS_SECRET_ACCESS_KEY"] == "***REDACTED***"

    def test_sanitize_redis_password(self):
        """Test that Redis password is sanitized."""
        env_vars = {
            "SCCACHE_REDIS": "redis://localhost:6379",
            "SCCACHE_REDIS_PASSWORD": "secret",
        }

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized["SCCACHE_REDIS"] == "redis://localhost:6379"
        assert sanitized["SCCACHE_REDIS_PASSWORD"] == "***REDACTED***"

    def test_sanitize_http_token(self):
        """Test that HTTP token is sanitized."""
        env_vars = {
            "SCCACHE_ENDPOINT": "https://cache.example.com",
            "SCCACHE_HTTP_TOKEN": "bearer_token_123",
        }

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized["SCCACHE_ENDPOINT"] == "https://cache.example.com"
        assert sanitized["SCCACHE_HTTP_TOKEN"] == "***REDACTED***"

    def test_validate_s3_credentials_valid(self):
        """Test validation of valid S3 credentials."""
        credentials = {"access_key": "AKIA...", "secret_key": "***"}

        is_valid = SecureCredentialHandler.validate_credentials("s3", credentials)
        assert is_valid is True

    def test_validate_s3_credentials_incomplete(self):
        """Test validation of incomplete S3 credentials."""
        credentials = {
            "access_key": "AKIA..."
            # Missing secret_key
        }

        is_valid = SecureCredentialHandler.validate_credentials("s3", credentials)
        assert is_valid is False

    def test_validate_no_credentials(self):
        """Test validation with no credentials."""
        is_valid = SecureCredentialHandler.validate_credentials("redis", None)
        assert is_valid is True


# =============================================================================
# RemoteCacheConfigurator Tests
# =============================================================================


class TestRemoteCacheConfigurator:
    """Tests for RemoteCacheConfigurator class."""

    @pytest.fixture
    def cache_config(self, tmp_path):
        """Create a mock cache configuration."""
        executable = tmp_path / "sccache.exe"
        executable.touch()

        return BuildCacheConfig(
            tool="sccache",
            version="0.7.4",
            executable_path=executable,
            cache_dir=tmp_path / "cache",
            max_size="10G",
        )

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_init_with_cache_config(self, cache_config):
        """Test initialization with cache configuration."""
        configurator = RemoteCacheConfigurator(cache_config)

        assert configurator.cache_config == cache_config

    def test_init_with_none_raises_error(self):
        """Test initialization with None raises ValueError."""
        with pytest.raises(ValueError, match="cache_config cannot be None"):
            RemoteCacheConfigurator(None)

    # -------------------------------------------------------------------------
    # S3 Configuration Tests
    # -------------------------------------------------------------------------

    def test_configure_s3_basic(self, cache_config):
        """Test basic S3 configuration."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3", bucket="my-build-cache", region="us-east-1"
        )

        env_vars = configurator.configure_s3(remote_config)

        assert env_vars["SCCACHE_BUCKET"] == "my-build-cache"
        assert env_vars["SCCACHE_REGION"] == "us-east-1"
        assert env_vars["SCCACHE_S3_USE_SSL"] == "true"

    def test_configure_s3_with_credentials(self, cache_config):
        """Test S3 configuration with credentials."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3",
            bucket="my-build-cache",
            region="us-west-2",
            credentials={"access_key": "AKIA...", "secret_key": "secret"},
        )

        env_vars = configurator.configure_s3(remote_config)

        assert env_vars["AWS_ACCESS_KEY_ID"] == "AKIA..."
        assert env_vars["AWS_SECRET_ACCESS_KEY"] == "secret"

    def test_configure_s3_custom_endpoint(self, cache_config):
        """Test S3 configuration with custom endpoint (MinIO)."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3",
            bucket="build-cache",
            endpoint="http://minio:9000",
            use_ssl=False,
        )

        env_vars = configurator.configure_s3(remote_config)

        assert env_vars["SCCACHE_ENDPOINT"] == "http://minio:9000"
        assert env_vars["SCCACHE_S3_USE_SSL"] == "false"

    def test_configure_s3_with_prefix(self, cache_config):
        """Test S3 configuration with key prefix."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3", bucket="my-build-cache", prefix="project-a/"
        )

        env_vars = configurator.configure_s3(remote_config)

        assert env_vars["SCCACHE_S3_KEY_PREFIX"] == "project-a/"

    # -------------------------------------------------------------------------
    # Redis Configuration Tests
    # -------------------------------------------------------------------------

    def test_configure_redis_basic(self, cache_config):
        """Test basic Redis configuration."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="redis", endpoint="redis://localhost:6379"
        )

        env_vars = configurator.configure_redis(remote_config)

        assert env_vars["SCCACHE_REDIS"] == "redis://localhost:6379"

    def test_configure_redis_with_password(self, cache_config):
        """Test Redis configuration with password."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="redis",
            endpoint="redis://localhost:6379",
            credentials={"password": "secret"},
        )

        env_vars = configurator.configure_redis(remote_config)

        assert env_vars["SCCACHE_REDIS_PASSWORD"] == "secret"

    def test_configure_redis_with_db_and_prefix(self, cache_config):
        """Test Redis configuration with database and prefix."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="redis",
            endpoint="redis://localhost:6379",
            prefix="buildcache:",
            extra_config={"db": "1", "ttl": "86400"},
        )

        env_vars = configurator.configure_redis(remote_config)

        assert env_vars["SCCACHE_REDIS_DB"] == "1"
        assert env_vars["SCCACHE_REDIS_KEY_PREFIX"] == "buildcache:"
        assert env_vars["SCCACHE_REDIS_TTL"] == "86400"

    # -------------------------------------------------------------------------
    # HTTP Configuration Tests
    # -------------------------------------------------------------------------

    def test_configure_http_basic(self, cache_config):
        """Test basic HTTP configuration."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="http", endpoint="https://cache.example.com"
        )

        env_vars = configurator.configure_http(remote_config)

        assert env_vars["SCCACHE_ENDPOINT"] == "https://cache.example.com"

    def test_configure_http_with_token(self, cache_config):
        """Test HTTP configuration with authentication token."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="http",
            endpoint="https://cache.example.com",
            credentials={"token": "bearer_abc123"},
        )

        env_vars = configurator.configure_http(remote_config)

        assert env_vars["SCCACHE_HTTP_TOKEN"] == "bearer_abc123"

    # -------------------------------------------------------------------------
    # Memcached Configuration Tests
    # -------------------------------------------------------------------------

    def test_configure_memcached_single_server(self, cache_config):
        """Test Memcached configuration with single server."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="memcached", endpoint="localhost:11211"
        )

        env_vars = configurator.configure_memcached(remote_config)

        assert env_vars["SCCACHE_MEMCACHED"] == "localhost:11211"

    def test_configure_memcached_multiple_servers(self, cache_config):
        """Test Memcached configuration with multiple servers."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="memcached",
            endpoint="server1:11211,server2:11211,server3:11211",
            prefix="cache:",
        )

        env_vars = configurator.configure_memcached(remote_config)

        assert (
            env_vars["SCCACHE_MEMCACHED"] == "server1:11211,server2:11211,server3:11211"
        )
        assert env_vars["SCCACHE_MEMCACHED_KEY_PREFIX"] == "cache:"

    # -------------------------------------------------------------------------
    # GCS Configuration Tests
    # -------------------------------------------------------------------------

    def test_configure_gcs_basic(self, cache_config, tmp_path):
        """Test basic GCS configuration."""
        configurator = RemoteCacheConfigurator(cache_config)

        creds_file = tmp_path / "service-account.json"
        creds_file.write_text("{}")

        remote_config = RemoteCacheConfig(
            backend_type="gcs",
            bucket="my-gcs-cache",
            credentials={"credentials_file": str(creds_file)},
        )

        env_vars = configurator.configure_gcs(remote_config)

        assert env_vars["SCCACHE_GCS_BUCKET"] == "my-gcs-cache"
        assert env_vars["SCCACHE_GCS_CREDENTIALS_PATH"] == str(creds_file)

    def test_configure_gcs_with_prefix(self, cache_config):
        """Test GCS configuration with object prefix."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="gcs", bucket="my-gcs-cache", prefix="project-b/"
        )

        env_vars = configurator.configure_gcs(remote_config)

        assert env_vars["SCCACHE_GCS_KEY_PREFIX"] == "project-b/"

    # -------------------------------------------------------------------------
    # General Configuration Tests
    # -------------------------------------------------------------------------

    def test_configure_routes_to_correct_backend(self, cache_config):
        """Test that configure() routes to correct backend method."""
        configurator = RemoteCacheConfigurator(cache_config)

        # S3
        s3_config = RemoteCacheConfig(backend_type="s3", bucket="test")
        s3_env = configurator.configure(s3_config)
        assert "SCCACHE_BUCKET" in s3_env

        # Redis
        redis_config = RemoteCacheConfig(
            backend_type="redis", endpoint="redis://localhost"
        )
        redis_env = configurator.configure(redis_config)
        assert "SCCACHE_REDIS" in redis_env

    def test_get_all_env_vars_combines_local_and_remote(self, cache_config):
        """Test get_all_env_vars combines local and remote variables."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(backend_type="s3", bucket="my-cache")

        env_vars = configurator.get_all_env_vars(remote_config)

        # Should have local cache vars (SCCACHE_DIR, etc.)
        assert "SCCACHE_DIR" in env_vars

        # Should have remote S3 vars
        assert "SCCACHE_BUCKET" in env_vars

    def test_get_all_env_vars_without_remote(self, cache_config):
        """Test get_all_env_vars with no remote configuration."""
        configurator = RemoteCacheConfigurator(cache_config)

        env_vars = configurator.get_all_env_vars()

        # Should only have local cache vars
        assert "SCCACHE_DIR" in env_vars
        assert "SCCACHE_BUCKET" not in env_vars


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestRemoteCacheConfigEdgeCases:
    """Additional edge case tests for RemoteCacheConfig."""

    def test_gcs_without_bucket_raises_error(self):
        """Test that GCS configuration without bucket raises error."""
        with pytest.raises(ValueError, match="requires 'bucket'"):
            RemoteCacheConfig(backend_type="gcs", region="us-central1")

    def test_http_without_endpoint_raises_error(self):
        """Test that HTTP configuration without endpoint raises error."""
        with pytest.raises(ValueError, match="requires 'endpoint'"):
            RemoteCacheConfig(backend_type="http")

    def test_config_with_no_credentials(self):
        """Test config creation without credentials."""
        config = RemoteCacheConfig(
            backend_type="s3", bucket="my-bucket", region="us-east-1", credentials=None
        )

        assert config.credentials is None

    def test_config_with_empty_extra_config(self):
        """Test config creation with empty extra_config."""
        config = RemoteCacheConfig(
            backend_type="s3", bucket="my-bucket", extra_config={}
        )

        assert config.extra_config == {}

    def test_config_with_use_ssl_false(self):
        """Test config creation with use_ssl=False."""
        config = RemoteCacheConfig(backend_type="s3", bucket="my-bucket", use_ssl=False)

        assert config.use_ssl is False

    def test_config_with_all_optional_fields(self):
        """Test config creation with all optional fields."""
        config = RemoteCacheConfig(
            backend_type="s3",
            endpoint="https://s3.example.com",
            credentials={"access_key": "key", "secret_key": "secret"},
            bucket="test-bucket",
            region="eu-west-1",
            prefix="cache/",
            use_ssl=True,
            extra_config={"custom": "value"},
        )

        assert config.endpoint == "https://s3.example.com"
        assert config.region == "eu-west-1"
        assert config.prefix == "cache/"
        assert config.extra_config["custom"] == "value"


class TestSecureCredentialHandlerEdgeCases:
    """Additional edge case tests for SecureCredentialHandler."""

    def test_sanitize_custom_password_field(self):
        """Test sanitizing custom field with 'password' in name."""
        env_vars = {
            "REDIS_PASSWORD": "secret",
            "MY_PASSWORD_FIELD": "also_secret",
            "NORMAL_FIELD": "normal_value",
        }

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized["REDIS_PASSWORD"] == "***REDACTED***"
        assert sanitized["MY_PASSWORD_FIELD"] == "***REDACTED***"
        assert sanitized["NORMAL_FIELD"] == "normal_value"

    def test_sanitize_custom_secret_field(self):
        """Test sanitizing custom field with 'secret' in name."""
        env_vars = {
            "MY_SECRET": "very_secret",
            "API_SECRET_KEY": "api_secret",
            "PUBLIC_KEY": "public_value",
        }

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized["MY_SECRET"] == "***REDACTED***"
        assert sanitized["API_SECRET_KEY"] == "***REDACTED***"
        assert sanitized["PUBLIC_KEY"] == "public_value"

    def test_sanitize_case_insensitive(self):
        """Test that sanitization is case-insensitive."""
        env_vars = {
            "my_PaSsWoRd": "secret",
            "API_SeCrEt": "secret",
        }

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized["my_PaSsWoRd"] == "***REDACTED***"
        assert sanitized["API_SeCrEt"] == "***REDACTED***"

    def test_sanitize_gcs_credentials_path(self):
        """Test sanitizing GCS credentials path."""
        env_vars = {
            "GCS_CREDENTIALS_PATH": "/path/to/creds.json",
            "SCCACHE_GCS_BUCKET": "my-bucket",
        }

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized["GCS_CREDENTIALS_PATH"] == "***REDACTED***"
        assert sanitized["SCCACHE_GCS_BUCKET"] == "my-bucket"

    def test_sanitize_empty_dict(self):
        """Test sanitizing empty dictionary."""
        env_vars = {}

        sanitized = SecureCredentialHandler.sanitize_for_logging(env_vars)

        assert sanitized == {}

    def test_validate_s3_credentials_empty_dict(self):
        """Test validation with empty credentials dict for S3."""
        credentials = {}

        is_valid = SecureCredentialHandler.validate_credentials("s3", credentials)

        # Empty dict means no credentials provided - returns True (valid but incomplete)
        assert is_valid is True

    def test_validate_s3_credentials_missing_secret(self):
        """Test validation with missing secret_key."""
        credentials = {"access_key": "AKIA..."}

        is_valid = SecureCredentialHandler.validate_credentials("s3", credentials)

        assert is_valid is False

    def test_validate_s3_credentials_missing_access(self):
        """Test validation with missing access_key."""
        credentials = {"secret_key": "secret"}

        is_valid = SecureCredentialHandler.validate_credentials("s3", credentials)

        assert is_valid is False

    def test_validate_redis_credentials_with_password(self):
        """Test validation of Redis credentials with password."""
        credentials = {"password": "secret"}

        is_valid = SecureCredentialHandler.validate_credentials("redis", credentials)

        assert is_valid is True

    def test_validate_redis_credentials_empty(self):
        """Test validation of Redis with empty credentials."""
        credentials = {}

        is_valid = SecureCredentialHandler.validate_credentials("redis", credentials)

        assert is_valid is True

    def test_validate_other_backend_types(self):
        """Test validation for other backend types."""
        assert SecureCredentialHandler.validate_credentials("http", {"token": "abc"})
        assert SecureCredentialHandler.validate_credentials("memcached", {})
        assert SecureCredentialHandler.validate_credentials("gcs", None)


class TestRemoteCacheConfiguratorEdgeCases:
    """Additional edge case tests for RemoteCacheConfigurator."""

    @pytest.fixture
    def cache_config(self, tmp_path):
        """Create a mock cache configuration."""
        executable = tmp_path / "sccache.exe"
        executable.touch()

        return BuildCacheConfig(
            tool="sccache",
            version="0.7.4",
            executable_path=executable,
            cache_dir=tmp_path / "cache",
            max_size="10G",
        )

    def test_configure_unsupported_backend(self, cache_config):
        """Test configure() with unsupported backend type raises error."""
        configurator = RemoteCacheConfigurator(cache_config)

        # Create config with unsupported backend
        # (bypassing post_init validation for testing)
        remote_config = RemoteCacheConfig.__new__(RemoteCacheConfig)
        remote_config.backend_type = "unsupported"
        remote_config.endpoint = "test"

        with pytest.raises(ValueError, match="Unsupported backend"):
            configurator.configure(remote_config)

    def test_configure_s3_without_region(self, cache_config):
        """Test S3 configuration without region uses default."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3", bucket="my-bucket", region=None
        )

        env_vars = configurator.configure_s3(remote_config)

        # Should not have SCCACHE_REGION key if None
        assert "SCCACHE_REGION" not in env_vars

    def test_configure_s3_with_extra_config(self, cache_config):
        """Test S3 configuration with extra_config."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3",
            bucket="my-bucket",
            extra_config={"CUSTOM_VAR": "custom_value", "ANOTHER": "value"},
        )

        env_vars = configurator.configure_s3(remote_config)

        assert env_vars["CUSTOM_VAR"] == "custom_value"
        assert env_vars["ANOTHER"] == "value"

    def test_configure_redis_with_extra_config_filtering(self, cache_config):
        """Test Redis configuration filters known extra_config keys."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="redis",
            endpoint="redis://localhost:6379",
            extra_config={"db": "1", "ttl": "3600", "custom": "value"},
        )

        env_vars = configurator.configure_redis(remote_config)

        # db and ttl should be mapped to specific env vars
        assert env_vars["SCCACHE_REDIS_DB"] == "1"
        assert env_vars["SCCACHE_REDIS_TTL"] == "3600"
        # custom should also be included
        assert env_vars["custom"] == "value"

    def test_configure_http_without_credentials(self, cache_config):
        """Test HTTP configuration without credentials."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="http", endpoint="https://cache.example.com", credentials=None
        )

        env_vars = configurator.configure_http(remote_config)

        assert "SCCACHE_HTTP_TOKEN" not in env_vars

    def test_configure_memcached_without_prefix(self, cache_config):
        """Test Memcached configuration without prefix."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="memcached", endpoint="localhost:11211", prefix=None
        )

        env_vars = configurator.configure_memcached(remote_config)

        assert "SCCACHE_MEMCACHED_KEY_PREFIX" not in env_vars

    def test_configure_gcs_without_credentials(self, cache_config):
        """Test GCS configuration without credentials file."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="gcs", bucket="my-bucket", credentials=None
        )

        env_vars = configurator.configure_gcs(remote_config)

        assert "SCCACHE_GCS_CREDENTIALS_PATH" not in env_vars

    def test_configure_gcs_with_rw_mode(self, cache_config):
        """Test GCS configuration with rw_mode extra config."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="gcs",
            bucket="my-bucket",
            extra_config={"rw_mode": "READ_ONLY", "custom": "value"},
        )

        env_vars = configurator.configure_gcs(remote_config)

        assert env_vars["SCCACHE_GCS_RW_MODE"] == "READ_ONLY"
        assert env_vars["custom"] == "value"
        # rw_mode should not be duplicated
        assert list(env_vars.keys()).count("rw_mode") == 0


class TestConnectionTesting:
    """Tests for connection testing functionality."""

    @pytest.fixture
    def cache_config(self, tmp_path):
        """Create a mock cache configuration."""
        executable = tmp_path / "sccache.exe"
        executable.touch()

        return BuildCacheConfig(
            tool="sccache",
            version="0.7.4",
            executable_path=executable,
            cache_dir=tmp_path / "cache",
            max_size="10G",
        )

    def test_connection_test_unknown_backend(self, cache_config):
        """Test connection test with unknown backend type."""
        configurator = RemoteCacheConfigurator(cache_config)

        # Create config with unknown backend
        remote_config = RemoteCacheConfig.__new__(RemoteCacheConfig)
        remote_config.backend_type = "unknown"
        remote_config.endpoint = "test"

        success, error = configurator.test_connection(remote_config)

        assert success is False
        assert "Unknown backend type" in error

    def test_connection_test_s3_import_error(self, cache_config):
        """Test S3 connection test handles boto3 import error."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(backend_type="s3", bucket="test-bucket")

        # Mock boto3 import to fail
        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"boto3": None}):
            success, error = configurator._test_s3_connection(remote_config)

            # Should return True with None error when boto3 not available
            assert success is True
            assert error is None

    def test_connection_test_redis_import_error(self, cache_config):
        """Test Redis connection test handles redis import error."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="redis", endpoint="redis://localhost:6379"
        )

        # Mock redis import to fail
        import sys
        from unittest.mock import patch

        with patch("toolchainkit.caching.remote.urlparse") as mock_urlparse:
            mock_urlparse.return_value = type(
                "ParseResult",
                (),
                {"hostname": "localhost", "port": 6379, "scheme": "redis"},
            )()

            with patch.dict(sys.modules, {"redis": None}):
                try:
                    success, error = configurator._test_redis_connection(remote_config)
                    # Should raise exception when redis not available
                    assert success is False
                except ImportError:
                    pass  # Expected

    def test_connection_test_http_import_error(self, cache_config):
        """Test HTTP connection test handles requests import error."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="http", endpoint="https://cache.example.com"
        )

        # Should return True with None error when requests not available
        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"requests": None}):
            success, error = configurator._test_http_connection(remote_config)

            assert success is True
            assert error is None

    def test_connection_test_memcached_import_error(self, cache_config):
        """Test Memcached connection test handles pymemcache import error."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="memcached", endpoint="localhost:11211"
        )

        import sys
        from unittest.mock import patch

        with patch.dict(sys.modules, {"pymemcache": None}):
            success, error = configurator._test_memcached_connection(remote_config)

            assert success is True
            assert error is None

    def test_connection_test_gcs_import_error(self, cache_config):
        """Test GCS connection test handles google-cloud-storage import error."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(backend_type="gcs", bucket="test-bucket")

        import sys
        from unittest.mock import patch

        with patch.dict(
            sys.modules, {"google.cloud": None, "google.cloud.storage": None}
        ):
            success, error = configurator._test_gcs_connection(remote_config)

            assert success is True
            assert error is None

    def test_connection_test_exception_handling(self, cache_config):
        """Test connection test handles general exceptions."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(backend_type="s3", bucket="test-bucket")

        # Mock to raise exception
        from unittest.mock import patch

        with patch.object(
            configurator, "_test_s3_connection", side_effect=Exception("Test error")
        ):
            success, error = configurator.test_connection(remote_config)

            assert success is False
            assert "Test error" in error


class TestGetAllEnvVars:
    """Tests for get_all_env_vars method."""

    @pytest.fixture
    def cache_config(self, tmp_path):
        """Create a mock cache configuration."""
        executable = tmp_path / "sccache.exe"
        executable.touch()
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        return BuildCacheConfig(
            tool="sccache",
            version="0.7.4",
            executable_path=executable,
            cache_dir=cache_dir,
            max_size="10G",
        )

    def test_get_all_env_vars_with_s3_remote(self, cache_config):
        """Test get_all_env_vars with S3 remote config."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3", bucket="my-bucket", region="us-west-1"
        )

        env_vars = configurator.get_all_env_vars(remote_config)

        # Should have both local and remote vars
        assert "SCCACHE_DIR" in env_vars
        assert "SCCACHE_BUCKET" in env_vars
        assert env_vars["SCCACHE_BUCKET"] == "my-bucket"

    def test_get_all_env_vars_with_redis_remote(self, cache_config):
        """Test get_all_env_vars with Redis remote config."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="redis", endpoint="redis://localhost:6379"
        )

        env_vars = configurator.get_all_env_vars(remote_config)

        assert "SCCACHE_DIR" in env_vars
        assert "SCCACHE_REDIS" in env_vars

    def test_get_all_env_vars_local_only(self, cache_config):
        """Test get_all_env_vars without remote config."""
        configurator = RemoteCacheConfigurator(cache_config)

        env_vars = configurator.get_all_env_vars()

        # Should only have local vars
        assert "SCCACHE_DIR" in env_vars
        assert "SCCACHE_BUCKET" not in env_vars
        assert "SCCACHE_REDIS" not in env_vars


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    @pytest.fixture
    def cache_config(self, tmp_path):
        """Create a mock cache configuration."""
        executable = tmp_path / "sccache.exe"
        executable.touch()
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        return BuildCacheConfig(
            tool="sccache",
            version="0.7.4",
            executable_path=executable,
            cache_dir=cache_dir,
            max_size="10G",
        )

    def test_minio_configuration(self, cache_config):
        """Test configuration for MinIO (S3-compatible)."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="s3",
            bucket="builds",
            endpoint="http://minio.internal:9000",
            region="us-east-1",
            use_ssl=False,
            credentials={"access_key": "minioadmin", "secret_key": "minioadmin"},
        )

        env_vars = configurator.configure(remote_config)

        assert env_vars["SCCACHE_BUCKET"] == "builds"
        assert env_vars["SCCACHE_ENDPOINT"] == "http://minio.internal:9000"
        assert env_vars["SCCACHE_S3_USE_SSL"] == "false"
        assert env_vars["AWS_ACCESS_KEY_ID"] == "minioadmin"

    def test_redis_cluster_configuration(self, cache_config):
        """Test configuration for Redis cluster."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="redis",
            endpoint="redis://redis-cluster.internal:6379",
            credentials={"password": "strongpassword"},
            prefix="team-a:",
            extra_config={"db": "2", "ttl": "7200"},
        )

        env_vars = configurator.configure(remote_config)

        assert env_vars["SCCACHE_REDIS"] == "redis://redis-cluster.internal:6379"
        assert env_vars["SCCACHE_REDIS_PASSWORD"] == "strongpassword"
        assert env_vars["SCCACHE_REDIS_KEY_PREFIX"] == "team-a:"
        assert env_vars["SCCACHE_REDIS_DB"] == "2"
        assert env_vars["SCCACHE_REDIS_TTL"] == "7200"

    def test_multiple_memcached_servers(self, cache_config):
        """Test configuration with multiple Memcached servers."""
        configurator = RemoteCacheConfigurator(cache_config)

        remote_config = RemoteCacheConfig(
            backend_type="memcached",
            endpoint="cache1.internal:11211,cache2.internal:11211,cache3.internal:11211",
            prefix="builds:",
        )

        env_vars = configurator.configure(remote_config)

        assert "cache1.internal:11211" in env_vars["SCCACHE_MEMCACHED"]
        assert "cache2.internal:11211" in env_vars["SCCACHE_MEMCACHED"]
        assert "cache3.internal:11211" in env_vars["SCCACHE_MEMCACHED"]

    def test_gcs_with_service_account(self, cache_config, tmp_path):
        """Test GCS configuration with service account."""
        configurator = RemoteCacheConfigurator(cache_config)

        creds_file = tmp_path / "service-account.json"
        creds_file.write_text('{"type": "service_account"}')

        remote_config = RemoteCacheConfig(
            backend_type="gcs",
            bucket="company-build-cache",
            prefix="project-x/",
            credentials={"credentials_file": str(creds_file)},
            extra_config={"rw_mode": "READ_WRITE"},
        )

        env_vars = configurator.configure(remote_config)

        assert env_vars["SCCACHE_GCS_BUCKET"] == "company-build-cache"
        assert env_vars["SCCACHE_GCS_KEY_PREFIX"] == "project-x/"
        assert env_vars["SCCACHE_GCS_RW_MODE"] == "READ_WRITE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
