"""
Mock utilities for ToolchainKit testing.

This module provides utilities for mocking HTTP responses, creating mock
registries, and generating test data.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json


def mock_http_download(
    url: str,
    content: bytes,
    status: int = 200,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create mock HTTP download response configuration.

    Returns a dictionary suitable for use with responses library or
    unittest.mock to simulate HTTP downloads.

    Args:
        url: URL to mock
        content: Response body content
        status: HTTP status code (default: 200)
        headers: Optional HTTP headers to include

    Returns:
        Dictionary with mock response configuration

    Example:
        >>> import responses
        >>> @responses.activate
        ... def test_download():
        ...     mock = mock_http_download(
        ...         'https://example.com/toolchain.tar.gz',
        ...         b'mock archive content',
        ...         headers={'Content-Type': 'application/gzip'}
        ...     )
        ...     responses.add(responses.GET, mock['url'], **mock['response'])
    """
    default_headers = {"Content-Length": str(len(content))}
    if headers:
        default_headers.update(headers)

    return {
        "url": url,
        "method": "GET",
        "status": status,
        "body": content,
        "headers": default_headers,
        "response": {
            "body": content,
            "status": status,
            "headers": default_headers,
        },
    }


def create_mock_registry(
    toolchains: Optional[Dict[str, Any]] = None, version: str = "1.0"
) -> Dict[str, Any]:
    """
    Create a mock toolchain registry structure.

    Generates a registry dictionary compatible with ToolchainKit's
    registry format.

    Args:
        toolchains: Dictionary of toolchain entries (toolchain_id -> entry)
        version: Registry format version

    Returns:
        Mock registry dictionary

    Example:
        >>> registry = create_mock_registry({
        ...     'llvm-18.1.8-linux-x64': {
        ...         'name': 'llvm',
        ...         'version': '18.1.8',
        ...         'platform': 'linux-x64',
        ...         'install_time': '2024-01-15T10:30:00',
        ...         'last_used': '2024-01-20T14:00:00',
        ...         'reference_count': 2
        ...     }
        ... })
    """
    return {
        "version": version,
        "toolchains": toolchains or {},
        "metadata": {
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        },
    }


def create_mock_toolchain_entry(
    name: str,
    version: str,
    platform: str,
    toolchain_type: str = "llvm",
    path: Optional[str] = None,
    install_time: str = "2024-01-01T00:00:00",
    last_used: Optional[str] = None,
    reference_count: int = 0,
    **extra_fields,
) -> Dict[str, Any]:
    """
    Create a mock toolchain registry entry.

    Args:
        name: Toolchain name (e.g., 'llvm', 'gcc')
        version: Toolchain version (e.g., '18.1.8')
        platform: Platform identifier (e.g., 'linux-x64')
        toolchain_type: Toolchain type (default: 'llvm')
        path: Installation path (auto-generated if None)
        install_time: ISO timestamp of installation
        last_used: ISO timestamp of last use (defaults to install_time)
        reference_count: Number of projects using this toolchain
        **extra_fields: Additional fields to include in entry

    Returns:
        Mock toolchain entry dictionary

    Example:
        >>> entry = create_mock_toolchain_entry(
        ...     name='llvm',
        ...     version='18.1.8',
        ...     platform='linux-x64',
        ...     reference_count=3,
        ...     sha256='abc123...'
        ... )
    """
    if path is None:
        path = f"/opt/toolchains/{name}-{version}-{platform}"

    if last_used is None:
        last_used = install_time

    entry = {
        "id": f"{name}-{version}-{platform}",
        "name": name,
        "version": version,
        "platform": platform,
        "type": toolchain_type,
        "path": path,
        "install_time": install_time,
        "last_used": last_used,
        "reference_count": reference_count,
    }

    # Add any extra fields
    entry.update(extra_fields)

    return entry


def create_mock_state(
    bootstrap_complete: bool = True,
    active_toolchain: Optional[str] = None,
    config_hash: Optional[str] = None,
    **extra_fields,
) -> Dict[str, Any]:
    """
    Create a mock project state dictionary.

    Args:
        bootstrap_complete: Whether bootstrap is complete
        active_toolchain: Active toolchain identifier
        config_hash: Configuration hash for change detection
        **extra_fields: Additional state fields

    Returns:
        Mock state dictionary

    Example:
        >>> state = create_mock_state(
        ...     bootstrap_complete=True,
        ...     active_toolchain='llvm-18.1.8-linux-x64',
        ...     cmake_configured=True
        ... )
    """
    state = {
        "version": "1.0",
        "bootstrap_complete": bootstrap_complete,
        "active_toolchain": active_toolchain,
        "config_hash": config_hash,
        "last_updated": "2024-01-01T00:00:00",
    }

    state.update(extra_fields)

    return state


def create_mock_metadata(
    name: str,
    version: str,
    platforms: Optional[list[str]] = None,
    url_template: Optional[str] = None,
    sha256: Optional[Dict[str, str]] = None,
    size: Optional[Dict[str, int]] = None,
    **extra_fields,
) -> Dict[str, Any]:
    """
    Create mock toolchain metadata.

    Args:
        name: Toolchain name
        version: Toolchain version
        platforms: List of supported platforms
        url_template: Download URL template with {platform} placeholder
        sha256: Dictionary mapping platform to SHA256 hash
        size: Dictionary mapping platform to size in bytes
        **extra_fields: Additional metadata fields

    Returns:
        Mock metadata dictionary

    Example:
        >>> metadata = create_mock_metadata(
        ...     name='llvm',
        ...     version='18.1.8',
        ...     platforms=['linux-x64', 'linux-arm64', 'windows-x64'],
        ...     url_template='https://example.com/llvm-18.1.8-{platform}.tar.gz',
        ...     sha256={
        ...         'linux-x64': 'abc123...',
        ...         'linux-arm64': 'def456...'
        ...     }
        ... )
    """
    if platforms is None:
        platforms = ["linux-x64", "windows-x64", "macos-x64"]

    if url_template is None:
        url_template = f"https://example.com/{name}-{version}-{{platform}}.tar.gz"

    metadata = {
        "name": name,
        "version": version,
        "type": "llvm" if "llvm" in name.lower() or "clang" in name.lower() else "gcc",
        "platforms": platforms,
        "url": url_template,
    }

    if sha256:
        metadata["sha256"] = sha256

    if size:
        metadata["size"] = size

    metadata.update(extra_fields)

    return metadata


def write_mock_json(path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write mock JSON data to file.

    Convenience function for writing mock registry, state, or metadata
    JSON files.

    Args:
        path: File path to write
        data: Dictionary to serialize
        indent: JSON indentation (default: 2)

    Example:
        >>> registry = create_mock_registry({'llvm-18': {...}})
        >>> write_mock_json(tmp_path / 'registry.json', registry)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent), encoding="utf-8")


def create_mock_download_info(
    url: str,
    filename: str,
    size: int,
    sha256: str,
    sha512: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create mock download information.

    Args:
        url: Download URL
        filename: Expected filename
        size: File size in bytes
        sha256: SHA256 checksum
        sha512: Optional SHA512 checksum

    Returns:
        Mock download info dictionary

    Example:
        >>> download_info = create_mock_download_info(
        ...     url='https://example.com/toolchain.tar.gz',
        ...     filename='toolchain.tar.gz',
        ...     size=1024*1024*100,  # 100MB
        ...     sha256='abc123...'
        ... )
    """
    info = {
        "url": url,
        "filename": filename,
        "size": size,
        "sha256": sha256,
    }

    if sha512:
        info["sha512"] = sha512

    return info


def create_mock_config_yaml(
    project_name: str = "test-project",
    toolchains: Optional[list[Dict[str, str]]] = None,
    generator: str = "Ninja",
) -> str:
    """
    Create mock toolchainkit.yaml configuration content.

    Args:
        project_name: Project name
        toolchains: List of toolchain dictionaries
        generator: CMake generator

    Returns:
        YAML configuration string

    Example:
        >>> yaml_content = create_mock_config_yaml(
        ...     project_name='my-project',
        ...     toolchains=[{'name': 'llvm-18', 'version': '18.1.8'}]
        ... )
        >>> config_file.write_text(yaml_content)
    """
    if toolchains is None:
        toolchains = [{"name": "llvm-18", "type": "llvm", "version": "18.1.8"}]

    config = f"""version: 1
project:
  name: {project_name}
  language: cpp

toolchains:
"""

    for tc in toolchains:
        config += f"""  - name: {tc.get('name', 'llvm')}
    type: {tc.get('type', 'llvm')}
    version: "{tc.get('version', '18.1.8')}"
"""

    config += f"""
build:
  generator: {generator}
  configurations:
    - Debug
    - Release
"""

    return config
