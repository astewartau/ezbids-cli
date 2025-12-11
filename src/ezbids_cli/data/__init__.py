"""Static data files for ezBIDS CLI."""

from pathlib import Path

DATA_DIR = Path(__file__).parent


def get_data_path(name: str) -> Path:
    """Get path to a data file."""
    return DATA_DIR / name
