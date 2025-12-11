"""Main analysis orchestration for ezBIDS CLI."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from ezbids_cli.core.dataset import (
    determine_unique_series,
    generate_dataset_list,
    organize_dataset,
)
from ezbids_cli.core.identification import identify_all_acquisitions
from ezbids_cli.core.entities import extract_entity_labels
from ezbids_cli.preprocess.dcm2niix import preprocess_input
from ezbids_cli.core.models import (
    Acquisition,
    AnalysisResult,
    DatasetDescription,
    ParticipantInfo,
    Series,
    Subject,
    Session,
)

console = Console()


class Analyzer:
    """Orchestrates the analysis of imaging data for BIDS conversion."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        config_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize the analyzer.

        Parameters
        ----------
        input_dir : Path
            Directory containing input data (DICOM or NIfTI)
        output_dir : Path
            Directory for output files
        config_path : Path, optional
            Path to configuration YAML file
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config_path = config_path
        self.config: dict[str, Any] = {}

        if config_path and config_path.exists():
            import yaml
            with open(config_path) as f:
                self.config = yaml.safe_load(f) or {}

    def analyze(self) -> dict[str, Any]:
        """
        Run the full analysis pipeline.

        Returns
        -------
        dict[str, Any]
            Analysis result as dictionary (compatible with ezBIDS_core.json format)
        """
        console.print("[dim]Step 1/4: Discovering files...[/]")
        acquisitions = self._discover_and_load_files()

        console.print("[dim]Step 2/4: Organizing dataset...[/]")
        acquisitions = organize_dataset(acquisitions)

        console.print("[dim]Step 3/4: Identifying datatypes and suffixes...[/]")
        acquisitions = identify_all_acquisitions(acquisitions)

        console.print("[dim]Step 4/4: Extracting entity labels...[/]")
        acquisitions = extract_entity_labels(acquisitions)

        # Build result structure
        result = self._build_result(acquisitions)

        # Save to output directory
        output_file = self.output_dir / "ezBIDS_core.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        console.print(f"[green]Analysis saved to {output_file}[/]")

        return result

    def _discover_and_load_files(self) -> list[Acquisition]:
        """Discover and load NIfTI files from input directory."""
        # Preprocess input - runs dcm2niix if needed
        data_dir, was_preprocessed = preprocess_input(
            self.input_dir,
            self.output_dir,
            verbose=False,
        )

        # Check for NIfTI files
        nifti_files = list(data_dir.rglob("*.nii.gz")) + list(
            data_dir.rglob("*.nii")
        )

        if not nifti_files:
            console.print(
                "[yellow]No NIfTI files found after preprocessing.[/]"
            )
            return []

        console.print(f"[dim]Found {len(nifti_files)} NIfTI files[/]")

        return generate_dataset_list(data_dir, nifti_files)

    def _build_result(self, acquisitions: list[Acquisition]) -> dict[str, Any]:
        """Build the analysis result structure."""
        # Get unique series
        unique_series = determine_unique_series(acquisitions)

        # Build subjects structure
        subjects = self._build_subjects(acquisitions)

        # Build participants info
        participants_info = self._build_participants_info(acquisitions)

        # Build series list
        series_list = self._build_series_list(unique_series, acquisitions)

        # Build objects list (all acquisitions)
        objects_list = self._build_objects_list(acquisitions)

        # Build dataset description
        dataset_desc = self._build_dataset_description()

        return {
            "readme": self._generate_readme(),
            "datasetDescription": asdict(dataset_desc),
            "subjects": subjects,
            "participantsColumn": self._build_participants_columns(),
            "participantsInfo": participants_info,
            "series": series_list,
            "objects": objects_list,
            "events": {},
            "BIDSURI": False,
        }

    def _build_subjects(self, acquisitions: list[Acquisition]) -> list[dict]:
        """Build subjects structure from acquisitions."""
        subjects_dict: dict[str, dict] = {}

        for acq in acquisitions:
            subj_key = acq.subject

            if subj_key not in subjects_dict:
                subjects_dict[subj_key] = {
                    "subject": acq.subject,
                    "PatientInfo": [
                        {
                            "PatientID": acq.patient_id,
                            "PatientName": acq.patient_name,
                            "PatientBirthDate": acq.patient_birth_date,
                        }
                    ],
                    "sessions": [],
                    "_sessions_seen": set(),
                }

            # Add session if not already present
            if acq.session and acq.session not in subjects_dict[subj_key]["_sessions_seen"]:
                subjects_dict[subj_key]["sessions"].append({
                    "session": acq.session,
                    "AcquisitionDate": acq.acquisition_date,
                    "AcquisitionTime": acq.acquisition_time,
                })
                subjects_dict[subj_key]["_sessions_seen"].add(acq.session)

        # Clean up internal tracking
        result = []
        for subj in subjects_dict.values():
            del subj["_sessions_seen"]
            result.append(subj)

        return result

    def _build_participants_info(
        self, acquisitions: list[Acquisition]
    ) -> dict[str, dict]:
        """Build participants info from acquisitions."""
        participants: dict[str, dict] = {}

        for acq in acquisitions:
            subj_idx = str(acq.subject_idx)

            if subj_idx not in participants:
                participants[subj_idx] = {
                    "species": acq.patient_species,
                    "sex": acq.patient_sex,
                    "age": acq.patient_age,
                    "handedness": acq.patient_handedness,
                }

        return participants

    def _build_participants_columns(self) -> dict[str, dict]:
        """Build participants column definitions."""
        return {
            "species": {
                "Description": "Species of participant",
                "Levels": {"homo sapiens": "Human"},
            },
            "sex": {
                "Description": "Biological sex of participant",
                "Levels": {"M": "Male", "F": "Female"},
            },
            "age": {
                "Description": "Age of participant in years",
            },
            "handedness": {
                "Description": "Handedness of participant",
                "Levels": {"R": "Right", "L": "Left", "A": "Ambidextrous"},
            },
        }

    def _build_series_list(
        self,
        unique_series: list[Acquisition],
        all_acquisitions: list[Acquisition],
    ) -> list[dict]:
        """Build series list from unique acquisitions."""
        series_list = []

        for idx, series_acq in enumerate(unique_series):
            # Find all object indices for this series
            object_indices = [
                i for i, acq in enumerate(all_acquisitions)
                if acq.series_idx == idx
            ]

            series_list.append({
                "series_idx": idx,
                "SeriesDescription": series_acq.series_description,
                "ProtocolName": series_acq.protocol_name,
                "Modality": series_acq.modality,
                "ImageType": series_acq.image_type,
                "RepetitionTime": series_acq.repetition_time,
                "EchoTime": series_acq.echo_time,
                "NumVolumes": series_acq.num_volumes,
                "PED": series_acq.direction,
                "nifti_path": str(series_acq.nifti_path),
                "AcquisitionDateTime": series_acq.acquisition_date_time,
                "datatype": series_acq.datatype,
                "suffix": series_acq.suffix,
                "type": series_acq.type,
                "entities": series_acq.entities,
                "error": series_acq.error,
                "message": series_acq.message,
                "IntendedFor": series_acq.intended_for,
                "B0FieldIdentifier": series_acq.b0_field_identifier,
                "B0FieldSource": series_acq.b0_field_source,
                "object_indices": object_indices,
            })

        return series_list

    def _build_objects_list(self, acquisitions: list[Acquisition]) -> list[dict]:
        """Build objects list from all acquisitions."""
        objects_list = []

        for idx, acq in enumerate(acquisitions):
            # Build items list (files associated with this acquisition)
            items = []
            for path in acq.paths:
                item = {
                    "path": str(path),
                    "name": self._get_file_type(path),
                }
                if str(path).endswith(".json"):
                    item["sidecar"] = acq.sidecar
                items.append(item)

            obj = {
                "idx": idx,
                "series_idx": acq.series_idx,
                "subject_idx": acq.subject_idx,
                "session_idx": acq.session_idx,
                "SeriesDescription": acq.series_description,
                "SeriesNumber": acq.series_number,
                "ModifiedSeriesNumber": acq.modified_series_number,
                "AcquisitionDate": acq.acquisition_date,
                "AcquisitionTime": acq.acquisition_time,
                "nifti_path": str(acq.nifti_path),
                "PED": acq.direction,
                "datatype": acq.datatype,
                "suffix": acq.suffix,
                "type": acq.type,
                "entities": acq.entities,
                "_entities": {
                    "subject": acq.subject,
                    "session": acq.session,
                    **acq.entities,
                },
                "_type": acq.type if acq.type else f"{acq.datatype}/{acq.suffix}" if acq.datatype and acq.suffix else "exclude",
                "exclude": acq.exclude,
                "error": acq.error,
                "message": acq.message,
                "IntendedFor": acq.intended_for,
                "B0FieldIdentifier": acq.b0_field_identifier,
                "B0FieldSource": acq.b0_field_source,
                "items": items,
                "analysisResults": {
                    "errors": [acq.error] if acq.error else [],
                    "warnings": [],
                    "NumVolumes": acq.num_volumes,
                    "filesize": acq.filesize,
                    "orientation": acq.orientation,
                    "section_id": acq.section_id,
                },
                "validationErrors": [],
                "validationWarnings": [],
            }
            objects_list.append(obj)

        return objects_list

    def _get_file_type(self, path: Path) -> str:
        """Get file type from path."""
        path_str = str(path)
        if path_str.endswith(".nii.gz"):
            return "nii.gz"
        elif path_str.endswith(".json"):
            return "json"
        elif path_str.endswith(".bval"):
            return "bval"
        elif path_str.endswith(".bvec"):
            return "bvec"
        elif path_str.endswith(".tsv"):
            return "tsv"
        else:
            return path.suffix.lstrip(".")

    def _build_dataset_description(self) -> DatasetDescription:
        """Build dataset description from config or defaults."""
        config_dataset = self.config.get("dataset", {})

        return DatasetDescription(
            name=config_dataset.get("name", "Untitled"),
            bids_version=config_dataset.get("bids_version", "1.9.0"),
            license=config_dataset.get("license", ""),
            authors=config_dataset.get("authors", []),
            acknowledgements=config_dataset.get("acknowledgements", ""),
            funding=config_dataset.get("funding", []),
        )

    def _generate_readme(self) -> str:
        """Generate README content."""
        config_readme = self.config.get("readme", "")
        if config_readme:
            return config_readme

        return f"""# {self.config.get('dataset', {}).get('name', 'Dataset')}

This dataset was converted to BIDS format using ezBIDS-cli.

## Description

Add your dataset description here.

## License

Add license information here.
"""
