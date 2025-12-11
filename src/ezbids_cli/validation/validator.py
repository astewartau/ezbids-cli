"""BIDS validation module for ezBIDS CLI.

This module wraps the bids-validator to check BIDS compliance.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


def run_validator(bids_dir: Path) -> dict[str, Any]:
    """
    Run bids-validator on a BIDS dataset.

    Parameters
    ----------
    bids_dir : Path
        Path to BIDS dataset root

    Returns
    -------
    dict
        Validation result with 'valid', 'errors', and 'warnings' keys
    """
    result = {
        "valid": False,
        "errors": [],
        "warnings": [],
    }

    # Check if bids-validator is available
    try:
        version_check = subprocess.run(
            ["bids-validator", "--version"],
            capture_output=True,
            text=True,
        )
        if version_check.returncode != 0:
            result["errors"].append("bids-validator not found. Install with: npm install -g bids-validator")
            return result
    except FileNotFoundError:
        result["errors"].append("bids-validator not found. Install with: npm install -g bids-validator")
        return result

    # Run validation
    try:
        proc = subprocess.run(
            ["bids-validator", str(bids_dir), "--json"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.stdout:
            try:
                output = json.loads(proc.stdout)
                result["errors"] = [
                    issue.get("reason", str(issue))
                    for issue in output.get("issues", {}).get("errors", [])
                ]
                result["warnings"] = [
                    issue.get("reason", str(issue))
                    for issue in output.get("issues", {}).get("warnings", [])
                ]
                result["valid"] = len(result["errors"]) == 0
            except json.JSONDecodeError:
                # Parse text output
                if "This dataset appears to be BIDS compatible" in proc.stdout:
                    result["valid"] = True
                else:
                    result["errors"].append(proc.stdout)

        if proc.stderr:
            console.print(f"[dim]Validator stderr: {proc.stderr}[/]")

    except subprocess.TimeoutExpired:
        result["errors"].append("Validation timed out after 5 minutes")
    except Exception as e:
        result["errors"].append(f"Validation error: {str(e)}")

    return result


def validate_dataset(bids_dir: Path, verbose: bool = False) -> bool:
    """
    Validate a BIDS dataset and print results.

    Parameters
    ----------
    bids_dir : Path
        Path to BIDS dataset
    verbose : bool
        Print detailed output

    Returns
    -------
    bool
        True if valid, False otherwise
    """
    console.print(f"[dim]Validating: {bids_dir}[/]")

    result = run_validator(bids_dir)

    if result["valid"]:
        console.print("[green]Dataset is BIDS valid![/]")
    else:
        console.print("[red]Validation errors found:[/]")
        for error in result["errors"][:10]:  # Limit to first 10
            console.print(f"  [red]- {error}[/]")
        if len(result["errors"]) > 10:
            console.print(f"  [dim]... and {len(result['errors']) - 10} more errors[/]")

    if verbose and result["warnings"]:
        console.print("[yellow]Warnings:[/]")
        for warning in result["warnings"][:10]:
            console.print(f"  [yellow]- {warning}[/]")

    return result["valid"]
