"""BIDS schema access for ezBIDS CLI.

This module provides access to BIDS schema information via bidsschematools.
All schema data (datatypes, suffixes, entities, ordering) comes from the
official BIDS specification.
"""

from ezbids_cli.schema._bst_adapter import (
    BIDSSchemaAdapter,
    EntityInfo,
    FileRule,
    SuffixInfo,
)
from ezbids_cli.schema._cache import (
    clear_schema_cache,
    get_schema_adapter,
    get_schema_version,
    preload_schema,
    set_schema_version,
)
from ezbids_cli.schema._validation import (
    get_optional_entities,
    get_required_entities,
    get_valid_datatypes,
    get_valid_suffixes,
    validate_entities_for_file,
    validate_file_naming,
    validate_suffix_for_datatype,
)


def get_bids_version() -> str:
    """Return the BIDS version from the schema."""
    return get_schema_adapter().bids_version


def get_entity_order() -> list[str]:
    """Return the canonical order of BIDS entities for filenames."""
    return get_schema_adapter().get_entity_order()


def get_entities() -> dict[str, EntityInfo]:
    """Return all entity definitions."""
    return get_schema_adapter().get_entities()


def get_entity_short_key(entity_name: str) -> str:
    """Get the short key for an entity (e.g., 'subject' -> 'sub')."""
    return get_schema_adapter().get_entity_short_key(entity_name)


def build_entity_mapping() -> dict[str, str]:
    """Build mapping from full entity names to short keys."""
    entities = get_schema_adapter().get_entities()
    return {name: info.short_key for name, info in entities.items()}


def get_suffixes() -> dict[str, SuffixInfo]:
    """Return all suffix definitions."""
    return get_schema_adapter().get_suffixes()


def get_datatypes() -> list[str]:
    """Return all valid datatype names."""
    return get_schema_adapter().get_datatypes()


def get_file_rules(datatype: str) -> dict[str, FileRule]:
    """Return all file rules for a datatype."""
    return get_schema_adapter().get_file_rules(datatype)


def get_entities_for_suffix(datatype: str, suffix: str) -> dict[str, str]:
    """Return entity requirements for a datatype/suffix combination."""
    return get_schema_adapter().get_entities_for_suffix(datatype, suffix)


__all__ = [
    # Adapter and data classes
    "BIDSSchemaAdapter",
    "EntityInfo",
    "FileRule",
    "SuffixInfo",
    # Cache management
    "clear_schema_cache",
    "get_schema_adapter",
    "get_schema_version",
    "preload_schema",
    "set_schema_version",
    # Schema access
    "get_bids_version",
    "get_datatypes",
    "get_entities",
    "get_entities_for_suffix",
    "get_entity_order",
    "get_entity_short_key",
    "get_file_rules",
    "get_suffixes",
    "build_entity_mapping",
    # Validation
    "get_optional_entities",
    "get_required_entities",
    "get_valid_datatypes",
    "get_valid_suffixes",
    "validate_entities_for_file",
    "validate_file_naming",
    "validate_suffix_for_datatype",
]
