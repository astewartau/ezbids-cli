"""BIDS validation module for ezBIDS CLI.

This module uses the bids-validator Python package to check BIDS compliance.
"""

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

console = Console()


@dataclass
class ValidationResult:
    """Result of BIDS validation."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files_checked: int = 0


def validate_dataset(bids_dir: Path, verbose: bool = False) -> ValidationResult:
    """
    Validate a BIDS dataset using the bids-validator Python package.

    Parameters
    ----------
    bids_dir : Path
        Path to BIDS dataset root
    verbose : bool
        Print detailed output

    Returns
    -------
    ValidationResult
        Validation result with errors and warnings
    """
    try:
        from bids_validator import BIDSValidator
    except ImportError:
        return ValidationResult(
            valid=False,
            errors=["bids-validator package not installed. Install with: pip install bids-validator"],
        )

    result = ValidationResult()
    validator = BIDSValidator()

    # Walk the dataset and validate each file
    bids_dir = Path(bids_dir)
    if not bids_dir.exists():
        result.valid = False
        result.errors.append(f"Dataset directory does not exist: {bids_dir}")
        return result

    # Check required top-level files
    dataset_description = bids_dir / "dataset_description.json"
    if not dataset_description.exists():
        result.errors.append("Missing required file: dataset_description.json")

    # Validate all files in the dataset
    invalid_files = []
    for file_path in bids_dir.rglob("*"):
        if file_path.is_file():
            # Skip hidden files and work directories
            if any(part.startswith(".") for part in file_path.parts):
                continue

            # Get path relative to BIDS root with leading slash
            rel_path = "/" + str(file_path.relative_to(bids_dir))

            result.files_checked += 1

            if not validator.is_bids(rel_path):
                invalid_files.append(rel_path)

    if invalid_files:
        result.errors.extend([f"Invalid BIDS filename: {f}" for f in invalid_files[:20]])
        if len(invalid_files) > 20:
            result.errors.append(f"... and {len(invalid_files) - 20} more invalid files")

    result.valid = len(result.errors) == 0

    return result


def print_validation_result(result: ValidationResult, verbose: bool = False) -> None:
    """Print validation results to console."""
    if result.valid:
        console.print(f"[green]✓ Dataset is BIDS valid![/] ({result.files_checked} files checked)")
    else:
        console.print(f"[red]✗ Validation errors found[/] ({result.files_checked} files checked)")
        for error in result.errors:
            console.print(f"  [red]• {error}[/]")

    if verbose and result.warnings:
        console.print("[yellow]Warnings:[/]")
        for warning in result.warnings:
            console.print(f"  [yellow]• {warning}[/]")
