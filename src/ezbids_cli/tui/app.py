"""Interactive TUI application for ezBIDS CLI.

This module provides a terminal user interface for reviewing and editing
BIDS mappings.
"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class EzbidsTUI:
    """Interactive TUI for reviewing BIDS mappings.

    This is a placeholder implementation. The full TUI will be built
    using Textual in a future version.
    """

    def __init__(
        self,
        analysis_file: Path,
        config_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize the TUI.

        Parameters
        ----------
        analysis_file : Path
            Path to ezBIDS_core.json analysis file
        config_path : Path, optional
            Path to configuration file
        """
        self.analysis_file = analysis_file
        self.config_path = config_path
        self.data: dict = {}

        # Load analysis data
        with open(analysis_file) as f:
            self.data = json.load(f)

    def run(self) -> None:
        """Run the TUI application."""
        console.print("[bold blue]ezBIDS Interactive Review[/]")
        console.print()
        console.print("[yellow]Note: Full interactive TUI is not yet implemented.[/]")
        console.print("[yellow]Using simple text-based review mode.[/]")
        console.print()

        self._show_summary()
        self._show_series()

        console.print()
        console.print("[dim]To edit mappings, modify the analysis file directly or use a config file.[/]")

    def _show_summary(self) -> None:
        """Show dataset summary."""
        dataset_desc = self.data.get("datasetDescription", {})
        subjects = self.data.get("subjects", [])
        objects = self.data.get("objects", [])

        console.print("[bold]Dataset Summary[/]")
        console.print(f"  Name: {dataset_desc.get('Name', 'Untitled')}")
        console.print(f"  Subjects: {len(subjects)}")
        console.print(f"  Acquisitions: {len(objects)}")
        console.print()

    def _show_series(self) -> None:
        """Show series mappings."""
        series_list = self.data.get("series", [])

        console.print("[bold]Series Mappings[/]")
        console.print()

        for idx, series in enumerate(series_list):
            series_desc = series.get("SeriesDescription", "Unknown")
            datatype = series.get("datatype", "?")
            suffix = series.get("suffix", "?")
            series_type = series.get("type", "")
            num_volumes = series.get("NumVolumes", 1)
            count = len(series.get("object_indices", []))

            if series_type == "exclude":
                status = "[red]EXCLUDED[/]"
            elif datatype and suffix:
                status = f"[green]{datatype}/{suffix}[/]"
            else:
                status = "[yellow]UNIDENTIFIED[/]"

            console.print(f"  {idx + 1:2d}. {series_desc[:40]:<40s} {status}")
            console.print(f"      Volumes: {num_volumes}, Count: {count}")

        console.print()
