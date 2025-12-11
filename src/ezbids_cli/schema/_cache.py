"""Schema caching layer for ezBIDS CLI.

This module provides caching for the BIDSSchemaAdapter to avoid
repeated schema loading. Supports version pinning.
"""

from functools import lru_cache

from ezbids_cli.schema._bst_adapter import BIDSSchemaAdapter

# Global version setting (can be set via config before first schema access)
_schema_version: str | None = None


def set_schema_version(version: str | None) -> None:
    """
    Set the BIDS schema version to use.

    Must be called before first schema access. Subsequent calls
    after schema is loaded will have no effect unless cache is cleared.

    Parameters
    ----------
    version : str or None
        BIDS version to use (e.g., "1.9.0"). If None, uses latest.
    """
    global _schema_version
    _schema_version = version


def get_schema_version() -> str | None:
    """Return the currently configured schema version."""
    return _schema_version


@lru_cache(maxsize=4)
def get_schema_adapter(version: str | None = None) -> BIDSSchemaAdapter:
    """
    Get a cached BIDSSchemaAdapter instance.

    Parameters
    ----------
    version : str or None
        BIDS version to use. If None, uses the globally configured version.

    Returns
    -------
    BIDSSchemaAdapter
        Cached adapter instance.
    """
    effective_version = version if version is not None else _schema_version
    return BIDSSchemaAdapter(version=effective_version)


def clear_schema_cache() -> None:
    """Clear the schema cache. Useful for testing or version switching."""
    get_schema_adapter.cache_clear()


def preload_schema() -> None:
    """Preload schema into cache. Call on startup for faster first access."""
    get_schema_adapter()
