"""BIDS converter for ezBIDS CLI.

This module handles the conversion of analyzed data into BIDS format.
"""

import json
import os
from pathlib import Path
from typing import Any

from rich.console import Console

from ezbids_cli.schema import get_bids_version, get_entity_order, build_entity_mapping

console = Console()


class BIDSConverter:
    """Convert analyzed imaging data to BIDS format."""

    def __init__(
        self,
        analysis_data: dict[str, Any],
        output_dir: Path,
        link_mode: str = "hardlink",
    ) -> None:
        """
        Initialize the converter.

        Parameters
        ----------
        analysis_data : dict
            Analysis result from Analyzer (or loaded from ezBIDS_core.json)
        output_dir : Path
            Output directory for BIDS dataset
        link_mode : str
            File linking strategy: "hardlink", "symlink", or "copy"
        """
        self.data = analysis_data
        self.output_dir = Path(output_dir)
        self.link_mode = link_mode
        self.entity_order = get_entity_order()
        self.entity_mapping = build_entity_mapping()

    def convert(self) -> None:
        """Run the full BIDS conversion."""
        dataset_name = self.data.get("datasetDescription", {}).get("Name", "dataset")
        dataset_name = self._sanitize_name(dataset_name)

        bids_dir = self.output_dir / dataset_name
        bids_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"[dim]Creating BIDS dataset: {bids_dir}[/]")

        # Write dataset-level files
        self._write_dataset_description(bids_dir)
        self._write_readme(bids_dir)
        self._write_bidsignore(bids_dir)
        self._write_participants(bids_dir)

        # Convert all objects, tracking filenames to handle duplicates
        objects = self.data.get("objects", [])
        self._filename_counts: dict[str, int] = {}

        for obj in objects:
            self._convert_object(obj, bids_dir)

        console.print(f"[green]BIDS dataset created: {bids_dir}[/]")

    def _sanitize_name(self, name: str) -> str:
        """Sanitize dataset name for filesystem."""
        import re
        # Replace spaces and special chars with underscores
        name = re.sub(r"[^\w\-]", "_", name)
        # Remove multiple underscores
        name = re.sub(r"_+", "_", name)
        return name.strip("_") or "dataset"

    def _write_dataset_description(self, bids_dir: Path) -> None:
        """Write dataset_description.json."""
        desc = self.data.get("datasetDescription", {})

        # Ensure required fields
        desc.setdefault("Name", "Untitled")
        desc.setdefault("BIDSVersion", get_bids_version())
        desc.setdefault("DatasetType", "raw")

        # Add GeneratedBy
        if "GeneratedBy" not in desc:
            desc["GeneratedBy"] = [{
                "Name": "ezBIDS-cli",
                "Version": "0.1.0",
                "CodeURL": "https://github.com/brainlife/ezbids-cli",
            }]

        output_file = bids_dir / "dataset_description.json"
        with open(output_file, "w") as f:
            json.dump(desc, f, indent=2)

    def _write_readme(self, bids_dir: Path) -> None:
        """Write README file."""
        readme = self.data.get("readme", "")
        if not readme:
            readme = "# Dataset\n\nConverted using ezBIDS-cli.\n"

        output_file = bids_dir / "README"
        with open(output_file, "w") as f:
            f.write(readme)

    def _write_bidsignore(self, bids_dir: Path) -> None:
        """Write .bidsignore file."""
        ignore_patterns = [
            "excluded/",
            "finalized.json",
            "ezBIDS_core.json",
        ]

        output_file = bids_dir / ".bidsignore"
        with open(output_file, "w") as f:
            f.write("\n".join(ignore_patterns) + "\n")

    def _write_participants(self, bids_dir: Path) -> None:
        """Write participants.tsv and participants.json."""
        subjects = self.data.get("subjects", [])
        participants_info = self.data.get("participantsInfo", {})
        participants_column = self.data.get("participantsColumn", {})

        if not subjects:
            return

        # Build column headers
        columns = ["participant_id"] + list(participants_column.keys())

        # Write TSV
        tsv_file = bids_dir / "participants.tsv"
        with open(tsv_file, "w") as f:
            f.write("\t".join(columns) + "\n")

            for idx, subject in enumerate(subjects):
                subj_id = f"sub-{subject['subject']}"
                row = [subj_id]

                # Get participant info
                info = participants_info.get(str(idx), {})
                for col in columns[1:]:
                    value = info.get(col, "n/a")
                    row.append(str(value) if value is not None else "n/a")

                f.write("\t".join(row) + "\n")

        # Write JSON
        json_file = bids_dir / "participants.json"
        with open(json_file, "w") as f:
            json.dump(participants_column, f, indent=2)

    def _convert_object(self, obj: dict[str, Any], bids_dir: Path) -> None:
        """Convert a single object to BIDS format."""
        obj_type = obj.get("_type", "")

        # Skip excluded objects
        if obj_type == "exclude" or obj.get("exclude", False):
            return

        if not obj_type or "/" not in obj_type:
            return

        datatype, suffix = obj_type.split("/", 1)
        entities = obj.get("_entities", {}).copy()

        # Build BIDS path
        path = self._build_bids_path(entities, datatype, bids_dir)
        path.mkdir(parents=True, exist_ok=True)

        # Build BIDS filename and handle duplicates
        base_filename = self._build_bids_filename(entities, suffix)
        full_key = f"{path}/{base_filename}_{suffix}"

        # Track filename usage and add run numbers for duplicates
        if full_key in self._filename_counts:
            self._filename_counts[full_key] += 1
            run_num = self._filename_counts[full_key]
            # Add or update run entity
            entities["run"] = f"{run_num:02d}"
            base_filename = self._build_bids_filename(entities, suffix)
        else:
            self._filename_counts[full_key] = 1

        # Process each item (nifti, json, bvec, bval, etc.)
        items = obj.get("items", [])
        for item in items:
            self._process_item(item, path, base_filename, suffix)

    def _build_bids_path(
        self,
        entities: dict[str, str],
        datatype: str,
        bids_dir: Path,
    ) -> Path:
        """Build the BIDS directory path for an object."""
        path = bids_dir

        # Add subject directory
        subject = entities.get("subject", "unknown")
        path = path / f"sub-{subject}"

        # Add session directory if present
        session = entities.get("session")
        if session:
            path = path / f"ses-{session}"

        # Add datatype directory
        path = path / datatype

        return path

    def _build_bids_filename(
        self,
        entities: dict[str, str],
        suffix: str,
    ) -> str:
        """Build the BIDS filename (without extension)."""
        tokens = []

        # Add entities in correct order
        for entity_name in self.entity_order:
            short_key = self.entity_mapping.get(entity_name, entity_name[:3])
            value = entities.get(entity_name)

            if value:
                tokens.append(f"{short_key}-{value}")

        return "_".join(tokens)

    def _process_item(
        self,
        item: dict[str, Any],
        output_path: Path,
        base_filename: str,
        suffix: str,
    ) -> None:
        """Process a single item (file) within an object."""
        item_path = item.get("path", "")
        item_name = item.get("name", "")

        if not item_path:
            return

        source_path = Path(item_path)

        # Determine extension
        if item_name == "nii.gz":
            ext = ".nii.gz"
        elif item_name == "json":
            ext = ".json"
        elif item_name == "bval":
            ext = ".bval"
        elif item_name == "bvec":
            ext = ".bvec"
        elif item_name == "tsv":
            ext = ".tsv"
        else:
            ext = source_path.suffix

        # Build output filename
        output_file = output_path / f"{base_filename}_{suffix}{ext}"

        # Handle JSON specially - may need to update sidecar
        if item_name == "json" and "sidecar" in item:
            sidecar = item["sidecar"]
            with open(output_file, "w") as f:
                json.dump(sidecar, f, indent=2)
            return

        # Link or copy the file
        if not source_path.exists():
            console.print(f"[yellow]Warning: Source file not found: {source_path}[/]")
            return

        # Remove existing file if present
        if output_file.exists():
            output_file.unlink()

        if self.link_mode == "hardlink":
            try:
                os.link(source_path, output_file)
            except OSError:
                # Fall back to copy if hardlink fails
                import shutil
                shutil.copy2(source_path, output_file)
        elif self.link_mode == "symlink":
            output_file.symlink_to(source_path.resolve())
        else:  # copy
            import shutil
            shutil.copy2(source_path, output_file)
