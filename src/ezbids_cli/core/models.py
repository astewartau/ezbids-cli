"""Data models for ezBIDS CLI."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class Acquisition:
    """Represents a single imaging acquisition (NIfTI file with metadata)."""

    # File paths
    nifti_path: Path
    json_path: Path
    paths: list[Path] = field(default_factory=list)
    file_directory: str = ""

    # Patient info
    patient_id: str = "n/a"
    patient_name: str = "n/a"
    patient_birth_date: str = "00000000"
    patient_species: str = "homo sapiens"
    patient_sex: str = "n/a"
    patient_age: str | int | float = "n/a"
    patient_handedness: str = "n/a"

    # Subject/session mapping
    subject: str = ""
    session: str = ""
    subject_idx: int = 0
    session_idx: int = 0

    # Series info
    study_id: str = ""
    series_number: int = 0
    modified_series_number: str = "00"
    series_description: str = "n/a"
    protocol_name: str = "n/a"
    descriptor: str = "SeriesDescription"
    series_idx: int = 0

    # Acquisition timing
    acquisition_date_time: str = "0000-00-00T00:00:00.000000"
    acquisition_date: str = "0000-00-00"
    acquisition_time: str = "00:00:00.000000"

    # Image properties
    modality: str = "MR"
    image_type: list[str] = field(default_factory=list)
    repetition_time: float = 0.0
    echo_number: Optional[int] = None
    echo_time: float = 0.0
    num_volumes: int = 1
    ndim: int = 3
    orientation: Optional[str] = None
    filesize: int = 0

    # Phase encoding
    phase_encoding_direction: Optional[str] = None
    direction: str = ""  # Derived: AP, PA, LR, RL, etc.

    # BIDS classification
    datatype: str = ""
    suffix: str = ""
    type: str = ""  # "datatype/suffix" or "exclude"
    entities: dict[str, str] = field(default_factory=dict)

    # Field map relationships
    intended_for: Optional[list[int]] = None
    b0_field_identifier: Optional[str] = None
    b0_field_source: Optional[str] = None

    # Status/validation
    exclude: bool = False
    error: Optional[str] = None
    message: Optional[str] = None
    section_id: int = 1
    finalized_match: bool = False

    # Raw metadata
    sidecar: dict[str, Any] = field(default_factory=dict)
    headers: str = ""

    def __post_init__(self) -> None:
        """Ensure paths are Path objects."""
        if isinstance(self.nifti_path, str):
            self.nifti_path = Path(self.nifti_path)
        if isinstance(self.json_path, str):
            self.json_path = Path(self.json_path)
        self.paths = [Path(p) if isinstance(p, str) else p for p in self.paths]


@dataclass
class Subject:
    """Represents a subject in the dataset."""

    subject: str
    patient_info: list[dict[str, str]] = field(default_factory=list)
    sessions: list["Session"] = field(default_factory=list)


@dataclass
class Session:
    """Represents a session within a subject."""

    session: str
    acquisition_date: str = ""
    acquisition_time: str = ""


@dataclass
class Series:
    """Represents a unique series (acquisition type) in the dataset."""

    series_idx: int
    series_description: str
    protocol_name: str
    modality: str
    image_type: list[str]
    repetition_time: float
    echo_time: float
    num_volumes: int
    phase_encoding_direction: str
    nifti_path: str
    acquisition_date_time: str

    # BIDS classification
    datatype: str = ""
    suffix: str = ""
    type: str = ""
    entities: dict[str, str] = field(default_factory=dict)

    # Field map relationships
    intended_for: Optional[list[int]] = None
    b0_field_identifier: Optional[str] = None
    b0_field_source: Optional[str] = None

    # Status
    error: Optional[str] = None
    message: Optional[str] = None
    object_indices: list[int] = field(default_factory=list)


@dataclass
class DatasetDescription:
    """BIDS dataset_description.json content."""

    name: str = "Untitled"
    bids_version: str = "1.9.0"
    dataset_type: str = "raw"
    license: str = ""
    authors: list[str] = field(default_factory=list)
    acknowledgements: str = ""
    how_to_acknowledge: str = ""
    funding: list[str] = field(default_factory=list)
    ethics_approvals: list[str] = field(default_factory=list)
    references_and_links: list[str] = field(default_factory=list)
    dataset_doi: str = ""
    generated_by: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Add ezBIDS as generator."""
        if not self.generated_by:
            self.generated_by = [
                {
                    "Name": "ezBIDS-cli",
                    "Version": "0.1.0",
                    "CodeURL": "https://github.com/brainlife/ezbids-cli",
                }
            ]


@dataclass
class ParticipantInfo:
    """Participant phenotype information."""

    species: str = "homo sapiens"
    sex: str = "n/a"
    age: str | int | float = "n/a"
    handedness: str = "n/a"


@dataclass
class AnalysisResult:
    """Complete analysis result for a dataset."""

    readme: str = ""
    dataset_description: DatasetDescription = field(default_factory=DatasetDescription)
    subjects: list[Subject] = field(default_factory=list)
    participants_column: dict[str, dict[str, Any]] = field(default_factory=dict)
    participants_info: dict[int, ParticipantInfo] = field(default_factory=dict)
    series: list[Series] = field(default_factory=list)
    objects: list[dict[str, Any]] = field(default_factory=list)
    events: dict[str, Any] = field(default_factory=dict)
    bids_uri: bool = False
