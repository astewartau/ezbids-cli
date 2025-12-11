"""Configuration export module for ezBIDS CLI.

This module exports analysis results as reusable configuration files.
"""

from pathlib import Path
from typing import Any

import yaml


def export_config(analysis_result: dict[str, Any], output_path: Path) -> None:
    """
    Export analysis result as a reusable YAML configuration.

    Parameters
    ----------
    analysis_result : dict
        Analysis result from Analyzer
    output_path : Path
        Path to write configuration file
    """
    config = {
        "version": "1.0",
        "dataset": _extract_dataset_config(analysis_result),
        "series": _extract_series_rules(analysis_result),
        "output": {
            "link_mode": "hardlink",
            "validate": True,
        },
    }

    with open(output_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def _extract_dataset_config(analysis_result: dict[str, Any]) -> dict[str, Any]:
    """Extract dataset configuration from analysis result."""
    desc = analysis_result.get("datasetDescription", {})
    return {
        "name": desc.get("Name", "Untitled"),
        "bids_version": desc.get("BIDSVersion", "1.9.0"),
        "authors": desc.get("Authors", []),
        "license": desc.get("License", ""),
    }


def _extract_series_rules(analysis_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract series mapping rules from analysis result."""
    series_list = analysis_result.get("series", [])
    rules = []

    for series in series_list:
        series_desc = series.get("SeriesDescription", "")
        datatype = series.get("datatype", "")
        suffix = series.get("suffix", "")
        series_type = series.get("type", "")

        if not series_desc:
            continue

        rule: dict[str, Any] = {
            "match": {
                "series_description": f".*{_escape_regex(series_desc)}.*",
            },
        }

        if series_type == "exclude":
            rule["exclude"] = True
        elif datatype and suffix:
            rule["datatype"] = datatype
            rule["suffix"] = suffix

            entities = series.get("entities", {})
            if entities:
                rule["entities"] = entities

        rules.append(rule)

    return rules


def _escape_regex(text: str) -> str:
    """Escape special regex characters in text."""
    import re
    return re.escape(text)
