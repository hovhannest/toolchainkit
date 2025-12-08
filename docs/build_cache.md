# Build Cache

Distributed build caching with sccache/ccache for faster rebuilds.

## Quick Start

```python
from toolchainkit.caching.detection import detect_cache_tool
from toolchainkit.caching.launcher import configure_compiler_launcher

# Auto-detect or install sccache
cache_tool = detect_cache_tool(prefer="sccache")

# Configure CMake compiler launcher
cmake_vars = configure_compiler_launcher(
    cache_tool="sccache",
    cache_dir=Path(".toolchainkit/cache")
)
```

## Supported Tools

- **sccache**: Recommended, supports S3/Redis/GCS remote backends
- **ccache**: Linux/macOS, local cache only

## Configuration

```yaml
# toolchainkit.yaml
cache:
  enabled: true
  tool: sccache
  size_gb: 10
  remote:
    type: s3
    bucket: my-build-cache
    region: us-east-1
```

## Remote Cache Configuration API

```python
from toolchainkit.caching.remote import RemoteCacheConfig, RemoteCacheConfigurator
from toolchainkit.caching.detection import BuildCacheManager

# Get cache tool
manager = BuildCacheManager()
cache_config = manager.get_or_install()

# Configure S3 backend
remote_config = RemoteCacheConfig(
    backend_type='s3',
    bucket='my-build-cache',
    region='us-east-1',
    credentials={
        'access_key': 'AKIA...',
        'secret_key': '***'
    }
)

# Create configurator
configurator = RemoteCacheConfigurator(cache_config)
env_vars = configurator.configure(remote_config)

# Apply to environment
import os
os.environ.update(env_vars)
```

### RemoteCacheConfig

```python
@dataclass
class RemoteCacheConfig:
    """Remote cache backend configuration."""

    backend_type: str  # 's3', 'redis', 'http', 'memcached', 'gcs'
    endpoint: str = ""
    credentials: Optional[Dict[str, str]] = None
    bucket: Optional[str] = None
    region: Optional[str] = "us-east-1"
    prefix: Optional[str] = None
    use_ssl: bool = True
    extra_config: Dict[str, str] = field(default_factory=dict)
```

### RemoteCacheConfigurator

```python
class RemoteCacheConfigurator:
    """Configure remote cache backends."""

    def __init__(self, cache_config: BuildCacheConfig):
        """Initialize with build cache configuration."""

    def configure(self, remote_config: RemoteCacheConfig) -> Dict[str, str]:
        """
        Configure remote cache backend.

        Returns:
            Environment variables to set for remote cache
        """

    def validate(self, remote_config: RemoteCacheConfig) -> Tuple[bool, List[str]]:
        """
        Validate remote cache configuration.

        Returns:
            (is_valid, list_of_issues)
        """
```

## Remote Backends

### S3 (AWS, MinIO, DigitalOcean Spaces)

**Manual configuration:**
```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export SCCACHE_BUCKET=my-build-cache
export SCCACHE_REGION=us-east-1
```

**API configuration:**
```python
remote_config = RemoteCacheConfig(
    backend_type='s3',
    bucket='my-build-cache',
    region='us-east-1',
    credentials={'access_key': 'AKIA...', 'secret_key': '***'},
    prefix='myteam/'  # Optional namespace
)
env_vars = configurator.configure(remote_config)
```

### Redis

**Manual configuration:**
```bash
export SCCACHE_REDIS=redis://localhost:6379
```

**API configuration:**
```python
remote_config = RemoteCacheConfig(
    backend_type='redis',
    endpoint='redis://cache.example.com:6379',
    credentials={'password': '***'}  # Optional
)
env_vars = configurator.configure(remote_config)
```

### GCS (Google Cloud Storage)

**Manual configuration:**
```bash
export SCCACHE_GCS_BUCKET=my-build-cache
export SCCACHE_GCS_KEY_PATH=/path/to/service-account.json
```

**API configuration:**
```python
remote_config = RemoteCacheConfig(
    backend_type='gcs',
    bucket='my-build-cache',
    credentials={'key_path': '/path/to/service-account.json'}
)
env_vars = configurator.configure(remote_config)
```

### HTTP

**API configuration:**
```python
remote_config = RemoteCacheConfig(
    backend_type='http',
    endpoint='https://cache.example.com',
    use_ssl=True
)
env_vars = configurator.configure(remote_config)
```

### Memcached

**API configuration:**
```python
remote_config = RemoteCacheConfig(
    backend_type='memcached',
    endpoint='cache1.example.com:11211,cache2.example.com:11211'
)
env_vars = configurator.configure(remote_config)
```

## CMake Integration

```cmake
set(CMAKE_C_COMPILER_LAUNCHER "sccache")
set(CMAKE_CXX_COMPILER_LAUNCHER "sccache")
```

## Statistics

```python
from toolchainkit.caching.launcher import get_cache_stats

stats = get_cache_stats("sccache")
print(f"Hit rate: {stats['hit_rate']:.1f}%")
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
```

## Benefits

- **Faster CI**: 5-10x faster rebuilds with cache hits
- **Team Sharing**: Remote cache shared across developers
- **Cross-platform**: Works on Windows, Linux, macOS

##Integration

Used by: CMake toolchain generation, CI/CD pipelines
