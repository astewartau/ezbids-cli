"""BIDS schema validation functions for ezBIDS CLI.

This module provides validation functions to check that datatype/suffix/entity
combinations are valid according to the BIDS specification.
"""

from ezbids_cli.schema._cache import get_schema_adapter


def validate_suffix_for_datatype(
    datatype: str, suffix: str
) -> tuple[bool, str | None]:
    """
    Check if a suffix is valid for a datatype.

    Parameters
    ----------
    datatype : str
        BIDS datatype (e.g., "anat", "func")
    suffix : str
        BIDS suffix (e.g., "T1w", "bold")

    Returns
    -------
    tuple[bool, str | None]
        (is_valid, error_message_if_invalid)
    """
    adapter = get_schema_adapter()
    return adapter.is_valid_suffix_for_datatype(datatype, suffix)


def validate_entities_for_file(
    datatype: str, suffix: str, entities: dict[str, str]
) -> list[str]:
    """
    Validate entities against schema rules.

    Parameters
    ----------
    datatype : str
        BIDS datatype
    suffix : str
        BIDS suffix
    entities : dict[str, str]
        Entities to validate (entity_name -> value)

    Returns
    -------
    list[str]
        List of validation errors (empty if valid)
    """
    adapter = get_schema_adapter()
    is_valid, errors = adapter.is_valid_combination(datatype, suffix, entities)
    return errors


def get_required_entities(datatype: str, suffix: str) -> list[str]:
    """
    Get required entities for a datatype/suffix combination.

    Parameters
    ----------
    datatype : str
        BIDS datatype
    suffix : str
        BIDS suffix

    Returns
    -------
    list[str]
        List of required entity names (excluding subject/session)
    """
    adapter = get_schema_adapter()
    return adapter.get_required_entities(datatype, suffix)


def get_optional_entities(datatype: str, suffix: str) -> list[str]:
    """
    Get optional entities for a datatype/suffix combination.

    Parameters
    ----------
    datatype : str
        BIDS datatype
    suffix : str
        BIDS suffix

    Returns
    -------
    list[str]
        List of optional entity names
    """
    adapter = get_schema_adapter()
    return adapter.get_optional_entities(datatype, suffix)


def get_valid_suffixes(datatype: str) -> list[str]:
    """
    Get all valid suffixes for a datatype.

    Parameters
    ----------
    datatype : str
        BIDS datatype

    Returns
    -------
    list[str]
        List of valid suffix names
    """
    adapter = get_schema_adapter()
    return adapter.get_suffixes_for_datatype(datatype)


def get_valid_datatypes() -> list[str]:
    """
    Get all valid datatype names.

    Returns
    -------
    list[str]
        List of valid datatype names
    """
    adapter = get_schema_adapter()
    return adapter.get_datatypes()


def validate_file_naming(
    datatype: str, suffix: str, entities: dict[str, str]
) -> list[str]:
    """
    Validate complete file naming against BIDS schema.

    This is a convenience function that combines suffix and entity validation.

    Parameters
    ----------
    datatype : str
        BIDS datatype
    suffix : str
        BIDS suffix
    entities : dict[str, str]
        Entities (entity_name -> value)

    Returns
    -------
    list[str]
        List of validation errors (empty if valid)
    """
    adapter = get_schema_adapter()
    is_valid, errors = adapter.is_valid_combination(datatype, suffix, entities)
    return errors
