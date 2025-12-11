"""BIDS Schema Tools adapter for ezBIDS CLI.

This module wraps bidsschematools to provide a stable internal API
for accessing BIDS schema information.
"""

from dataclasses import dataclass
from typing import Any

from bidsschematools import schema as bst_schema


@dataclass
class EntityInfo:
    """Information about a BIDS entity."""

    name: str  # Full name (e.g., "subject")
    short_key: str  # Short key (e.g., "sub")
    format: str  # Expected format ("label" or "index")
    description: str


@dataclass
class SuffixInfo:
    """Information about a BIDS suffix."""

    name: str  # Suffix name (e.g., "T1w")
    display_name: str
    description: str


@dataclass
class FileRule:
    """A file rule defining valid suffix/entity combinations."""

    suffixes: list[str]
    entities: dict[str, str]  # entity_name -> "required" | "optional"
    extensions: list[str]


class BIDSSchemaAdapter:
    """Wrapper around bidsschematools with stable internal API."""

    def __init__(self, version: str | None = None) -> None:
        """
        Initialize the adapter.

        Parameters
        ----------
        version : str, optional
            Specific BIDS version to use. If None, uses latest bundled version.
            Note: Version pinning requires the version to be available in bidsschematools.
        """
        self._version = version
        self._schema = bst_schema.load_schema()

    @property
    def bids_version(self) -> str:
        """Return the BIDS version from the schema."""
        return str(self._schema.get("bids_version", "unknown"))

    @property
    def schema_version(self) -> str:
        """Return the schema version."""
        return str(self._schema.get("schema_version", "unknown"))

    def get_entity_order(self) -> list[str]:
        """Return the canonical order of BIDS entities for filenames."""
        return list(self._schema.rules.entities)

    def get_entities(self) -> dict[str, EntityInfo]:
        """Return all entity definitions."""
        result = {}
        for entity_name, entity_obj in self._schema.objects.entities.items():
            result[entity_name] = EntityInfo(
                name=entity_name,
                short_key=entity_obj.get("name", entity_name[:3]),
                format=entity_obj.get("format", "label"),
                description=entity_obj.get("description", ""),
            )
        return result

    def get_entity_short_key(self, entity_name: str) -> str:
        """Get the short key for an entity (e.g., 'subject' -> 'sub')."""
        entities = self._schema.objects.entities
        if entity_name in entities:
            return entities[entity_name].get("name", entity_name[:3])
        return entity_name[:3]

    def get_datatypes(self) -> list[str]:
        """Return all valid datatype names."""
        return list(self._schema.objects.datatypes.keys())

    def get_suffixes(self) -> dict[str, SuffixInfo]:
        """Return all suffix definitions."""
        result = {}
        for suffix_name, suffix_obj in self._schema.objects.suffixes.items():
            result[suffix_name] = SuffixInfo(
                name=suffix_name,
                display_name=suffix_obj.get("display_name", suffix_name),
                description=suffix_obj.get("description", ""),
            )
        return result

    def get_suffixes_for_datatype(self, datatype: str) -> list[str]:
        """Return all valid suffixes for a datatype."""
        suffixes = set()
        try:
            datatype_rules = self._schema.rules.files.raw.get(datatype, {})
            for rule_name, rule in datatype_rules.items():
                if hasattr(rule, "get"):
                    rule_suffixes = rule.get("suffixes", [])
                    suffixes.update(rule_suffixes)
        except (AttributeError, KeyError):
            pass
        return sorted(suffixes)

    def get_file_rules(self, datatype: str) -> dict[str, FileRule]:
        """Return all file rules for a datatype."""
        result = {}
        try:
            datatype_rules = self._schema.rules.files.raw.get(datatype, {})
            for rule_name, rule in datatype_rules.items():
                if not hasattr(rule, "get"):
                    continue

                suffixes = rule.get("suffixes", [])
                extensions = rule.get("extensions", [])

                # Parse entities
                entities = {}
                rule_entities = rule.get("entities", {})
                for entity_name, entity_config in rule_entities.items():
                    if isinstance(entity_config, str):
                        entities[entity_name] = entity_config
                    elif hasattr(entity_config, "get"):
                        entities[entity_name] = entity_config.get("level", "optional")
                    else:
                        entities[entity_name] = "optional"

                result[rule_name] = FileRule(
                    suffixes=list(suffixes),
                    entities=entities,
                    extensions=list(extensions),
                )
        except (AttributeError, KeyError):
            pass
        return result

    def get_entities_for_suffix(
        self, datatype: str, suffix: str
    ) -> dict[str, str]:
        """
        Return entity requirements for a datatype/suffix combination.

        Returns dict mapping entity names to requirement level
        ("required" or "optional").
        """
        rules = self.get_file_rules(datatype)
        for rule in rules.values():
            if suffix in rule.suffixes:
                return rule.entities
        return {}

    def get_required_entities(self, datatype: str, suffix: str) -> list[str]:
        """Return required entities for a datatype/suffix combination."""
        entities = self.get_entities_for_suffix(datatype, suffix)
        return [
            name for name, level in entities.items()
            if level == "required" and name not in ("subject", "session")
        ]

    def get_optional_entities(self, datatype: str, suffix: str) -> list[str]:
        """Return optional entities for a datatype/suffix combination."""
        entities = self.get_entities_for_suffix(datatype, suffix)
        return [
            name for name, level in entities.items()
            if level == "optional" and name not in ("subject", "session")
        ]

    def is_valid_suffix_for_datatype(
        self, datatype: str, suffix: str
    ) -> tuple[bool, str | None]:
        """
        Check if a suffix is valid for a datatype.

        Returns (is_valid, error_message_if_invalid).
        """
        valid_suffixes = self.get_suffixes_for_datatype(datatype)
        if not valid_suffixes:
            return False, f"Unknown datatype: {datatype}"
        if suffix not in valid_suffixes:
            return False, f"Invalid suffix '{suffix}' for datatype '{datatype}'"
        return True, None

    def is_valid_combination(
        self,
        datatype: str,
        suffix: str,
        entities: dict[str, str],
    ) -> tuple[bool, list[str]]:
        """
        Validate a datatype/suffix/entity combination.

        Returns (is_valid, list_of_errors).
        """
        errors = []

        # Check suffix is valid for datatype
        valid, error = self.is_valid_suffix_for_datatype(datatype, suffix)
        if not valid:
            errors.append(error)
            return False, errors

        # Check required entities
        required = self.get_required_entities(datatype, suffix)
        for entity in required:
            if entity not in entities:
                errors.append(f"Missing required entity: {entity}")

        # Check entities are valid for this suffix
        valid_entities = self.get_entities_for_suffix(datatype, suffix)
        for entity in entities:
            if entity not in valid_entities and entity not in ("subject", "session"):
                errors.append(f"Entity '{entity}' not valid for {datatype}/{suffix}")

        return len(errors) == 0, errors

    def get_metadata_definition(self, field: str) -> dict[str, Any]:
        """Return metadata field definition."""
        metadata = self._schema.objects.metadata
        if field in metadata:
            meta_obj = metadata[field]
            return {
                "name": meta_obj.get("name", field),
                "type": meta_obj.get("type", "string"),
                "description": meta_obj.get("description", ""),
                "unit": meta_obj.get("unit"),
                "enum": meta_obj.get("enum"),
            }
        return {}
