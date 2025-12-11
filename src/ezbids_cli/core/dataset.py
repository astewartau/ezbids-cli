"""Dataset generation and organization for ezBIDS CLI."""

import json
import os
import re
from datetime import date
from operator import itemgetter
from pathlib import Path
from typing import Any, Optional

import nibabel as nib
from natsort import natsorted

from ezbids_cli.core.models import Acquisition


def get_phase_encoding_direction_label(pe_direction: str, orientation: str) -> str:
    """
    Determine the phase encoding direction label (AP, PA, LR, RL, etc.)
    from the PhaseEncodingDirection and image orientation.

    Parameters
    ----------
    pe_direction : str
        Phase encoding direction from metadata (i, j, k, i-, j-, k-)
    orientation : str
        Image orientation (e.g., "RAS", "LPS")

    Returns
    -------
    str
        Direction label (AP, PA, LR, RL, SI, IS, or empty)
    """
    if not pe_direction or not orientation:
        return ""

    # Map from axis to anatomical direction pairs
    axis_to_dir = {
        "R": ("R", "L"),
        "L": ("L", "R"),
        "A": ("A", "P"),
        "P": ("P", "A"),
        "S": ("S", "I"),
        "I": ("I", "S"),
    }

    # Get axis index from pe_direction (i=0, j=1, k=2)
    axis_map = {"i": 0, "j": 1, "k": 2}
    axis = pe_direction.replace("-", "")[0]
    if axis not in axis_map:
        return ""

    axis_idx = axis_map[axis]
    if axis_idx >= len(orientation):
        return ""

    ornt_char = orientation[axis_idx]
    if ornt_char not in axis_to_dir:
        return ""

    # Determine positive/negative direction
    pos_dir, neg_dir = axis_to_dir[ornt_char]
    if "-" in pe_direction:
        return neg_dir + pos_dir  # e.g., PA, RL
    else:
        return pos_dir + neg_dir  # e.g., AP, LR


def correct_phase_encoding(
    pe_direction: str, orientation: str
) -> tuple[str, bool]:
    """
    Correct phase encoding direction if necessary.

    Some dcm2niix versions may output incorrect PE direction.
    This function checks and corrects if needed.

    Parameters
    ----------
    pe_direction : str
        Original phase encoding direction
    orientation : str
        Image orientation

    Returns
    -------
    tuple[str, bool]
        Corrected PE direction and whether correction was applied
    """
    # For now, just return original - add correction logic if needed
    return pe_direction, False


def extract_subject_session_from_path(
    file_path: str,
    patient_id: str,
    patient_name: str,
) -> tuple[str, str]:
    """
    Extract subject and session IDs from file path or patient metadata.

    Parameters
    ----------
    file_path : str
        Path to the file
    patient_id : str
        Patient ID from metadata
    patient_name : str
        Patient name from metadata

    Returns
    -------
    tuple[str, str]
        Subject ID and session ID
    """
    subject = ""
    session = ""

    # Check file path and metadata for sub- and ses- patterns
    for value in [file_path, patient_id, patient_name]:
        if "sub-" in value.lower():
            match = re.split(r"[^a-zA-Z0-9]", value.lower().split("sub-")[-1])[0]
            subject = match
            break

    for value in [file_path, patient_id, patient_name]:
        if "ses-" in value.lower():
            match = re.split(r"[^a-zA-Z0-9]", value.lower().split("ses-")[-1])[0]
            session = match
            break

    # Clean up - remove non-alphanumeric characters
    subject = re.sub(r"[^A-Za-z0-9]+", "", subject)
    session = re.sub(r"[^A-Za-z0-9]+", "", session)

    return subject, session


def generate_dataset_list(
    input_dir: Path,
    file_list: Optional[list[Path]] = None,
) -> list[Acquisition]:
    """
    Generate a list of Acquisition objects from NIfTI/JSON files.

    Parameters
    ----------
    input_dir : Path
        Directory containing NIfTI and JSON files
    file_list : list[Path], optional
        Explicit list of files to process. If None, discovers files automatically.

    Returns
    -------
    list[Acquisition]
        List of Acquisition objects with metadata
    """
    today = date.today().isoformat()

    # Discover files if not provided
    if file_list is None:
        file_list = list(input_dir.rglob("*.nii.gz")) + list(input_dir.rglob("*.nii"))

    # Get all related files (JSON, bval, bvec)
    all_files = (
        list(input_dir.rglob("*.json"))
        + list(input_dir.rglob("*.bval"))
        + list(input_dir.rglob("*.bvec"))
    )

    img_list = natsorted([str(f) for f in file_list if f.suffix in [".gz", ".nii"]])
    corresponding_files = natsorted([str(f) for f in all_files])

    acquisitions: list[Acquisition] = []
    sub_info_list: list[dict] = []
    sub_info_list_id = "01"

    for img_file in img_list:
        img_path = Path(img_file)

        # Determine extension
        if img_file.endswith(".nii.gz"):
            ext = ".nii.gz"
        else:
            ext = img_path.suffix

        # Find corresponding JSON sidecar
        base_name = str(img_path).replace(ext, "")
        json_matches = [f for f in corresponding_files if f.endswith(".json") and base_name in f]

        if json_matches:
            json_path = Path(json_matches[0])
            with open(json_path) as f:
                sidecar = json.load(f)
        else:
            json_path = Path(base_name + ".json")
            sidecar = {
                "ConversionSoftware": "ezBIDS-cli",
                "ConversionSoftwareVersion": "0.1.0",
            }

        # Extract metadata with defaults
        modality = sidecar.get("Modality", "MR")
        pe_direction = sidecar.get("PhaseEncodingDirection")
        patient_id = sidecar.get("PatientID", "n/a")
        patient_name = sidecar.get("PatientName", "n/a")
        patient_birth_date = sidecar.get("PatientBirthDate", "00000000")
        if patient_birth_date:
            patient_birth_date = patient_birth_date.replace("-", "")
        patient_sex = sidecar.get("PatientSex", "n/a")
        patient_age = sidecar.get("PatientAge", "n/a")
        manufacturer = sidecar.get("Manufacturer", "n/a")
        repetition_time = sidecar.get("RepetitionTime", 0)
        echo_number = sidecar.get("EchoNumber")
        echo_time = sidecar.get("EchoTime", 0)
        series_number = sidecar.get("SeriesNumber", 0)
        series_description = sidecar.get("SeriesDescription", "n/a")
        protocol_name = sidecar.get("ProtocolName", "n/a")
        image_type = sidecar.get("ImageType", [])
        study_id = sidecar.get("StudyID", img_file.split("/")[0])

        # Acquisition timing
        acquisition_date_time = sidecar.get("AcquisitionDateTime", "0000-00-00T00:00:00.000000")
        acquisition_date = sidecar.get("AcquisitionDate", "0000-00-00")
        acquisition_time = sidecar.get("AcquisitionTime", "00:00:00.000000")

        # Descriptor field
        descriptor = "SeriesDescription" if series_description != "n/a" else "ProtocolName"
        if series_description == "n/a" and protocol_name == "n/a":
            series_description = img_file
            descriptor = "SeriesDescription"

        # Modified series number for sorting
        mod_series_number = f"{series_number:02d}" if series_number < 100 else str(series_number)

        # Load NIfTI to get image properties
        try:
            image = nib.load(img_file)
            ndim = image.ndim
            orientation = "".join(nib.aff2axcodes(image.affine))

            # Get volume count
            try:
                num_volumes = image.shape[3]
            except IndexError:
                num_volumes = 1

            # Get TR from header if not in sidecar
            if repetition_time == 0 and len(image.header.get_zooms()) == 4:
                repetition_time = round(float(image.header.get_zooms()[-1]), 2)
                sidecar["RepetitionTime"] = repetition_time
        except Exception:
            ndim = 3
            orientation = None
            num_volumes = 1

        # Determine phase encoding direction label
        direction = ""
        if pe_direction and orientation:
            corrected_pe, _ = correct_phase_encoding(pe_direction, orientation)
            direction = get_phase_encoding_direction_label(corrected_pe, orientation)

        # File size
        filesize = os.stat(img_file).st_size

        # Calculate age if possible
        age: str | int | float = "n/a"
        if isinstance(patient_age, (int, float)):
            age = patient_age
        elif patient_birth_date and patient_birth_date != "00000000":
            try:
                birth_year = int(patient_birth_date[:4])
                current_year = int(today.split("-")[0])
                age = current_year - birth_year
            except (ValueError, IndexError):
                pass

        # Subject/session extraction
        extracted_subject, extracted_session = extract_subject_session_from_path(
            img_file, patient_id, patient_name
        )

        # Track subject info for auto-assignment
        folder = "n/a"
        if patient_id == "n/a" and patient_name == "n/a" and patient_birth_date == "00000000":
            # Completely anonymized data
            folder = Path(img_file).parent.name

        sub_info = {
            "PatientID": patient_id,
            "PatientName": patient_name,
            "PatientBirthDate": patient_birth_date,
            "Folder": folder,
            "Subject": sub_info_list_id,
        }
        sub_info_list.append(sub_info)

        # Increment subject ID if info changed
        if len(sub_info_list) > 1:
            prev_info = sub_info_list[-2].copy()
            prev_info["Subject"] = sub_info_list[-1]["Subject"]  # Ignore Subject field in comparison
            curr_info = sub_info.copy()
            if prev_info != curr_info:
                sub_info_list_id = f"{int(sub_info_list_id) + 1:02d}"
                sub_info_list[-1]["Subject"] = sub_info_list_id

        # Use extracted subject or auto-assigned
        subject = extracted_subject if extracted_subject else sub_info["Subject"]
        session = extracted_session

        # Find associated files (bval, bvec, etc.)
        associated_files = [
            Path(f) for f in corresponding_files
            if base_name in f and not f.endswith(ext)
        ]
        paths = natsorted([img_path] + associated_files, key=str)

        # Create Acquisition object
        acq = Acquisition(
            nifti_path=img_path,
            json_path=json_path,
            paths=paths,
            file_directory=str(img_path.parent),
            patient_id=patient_id,
            patient_name=patient_name,
            patient_birth_date=patient_birth_date,
            patient_sex=patient_sex,
            patient_age=age,
            subject=subject,
            session=session,
            study_id=study_id,
            series_number=series_number,
            modified_series_number=mod_series_number,
            series_description=series_description,
            protocol_name=protocol_name,
            descriptor=descriptor,
            acquisition_date_time=acquisition_date_time,
            acquisition_date=acquisition_date,
            acquisition_time=acquisition_time,
            modality=modality,
            image_type=image_type if isinstance(image_type, list) else [image_type],
            repetition_time=repetition_time,
            echo_number=echo_number,
            echo_time=echo_time,
            num_volumes=num_volumes,
            ndim=ndim,
            orientation=orientation,
            filesize=filesize,
            phase_encoding_direction=pe_direction,
            direction=direction,
            sidecar=sidecar,
        )
        acquisitions.append(acq)

    # Sort by acquisition parameters
    acquisitions.sort(
        key=lambda x: (
            x.acquisition_date,
            x.subject,
            x.session,
            x.acquisition_time,
            x.modified_series_number,
            str(x.json_path),
        )
    )

    return acquisitions


def organize_dataset(acquisitions: list[Acquisition]) -> list[Acquisition]:
    """
    Organize acquisitions into subject/session groups.

    This handles anonymized data where metadata may be missing.

    Parameters
    ----------
    acquisitions : list[Acquisition]
        List of acquisitions to organize

    Returns
    -------
    list[Acquisition]
        Organized acquisitions with updated subject/session info
    """
    # Sort by acquisition parameters
    acquisitions.sort(
        key=lambda x: (
            x.acquisition_date,
            x.patient_id,
            x.patient_name,
            x.acquisition_time,
            x.modified_series_number,
        )
    )

    # Group acquisitions by subject indicators
    subject_idx = 0
    session_idx = 0
    prev_subject_key = None
    prev_session_key = None

    for acq in acquisitions:
        # Create subject key from available metadata
        subject_key = (acq.patient_id, acq.patient_name, acq.patient_birth_date)

        if subject_key != prev_subject_key:
            subject_idx += 1
            session_idx = 0
            prev_session_key = None

        # Create session key
        session_key = (acq.acquisition_date,)

        if session_key != prev_session_key:
            session_idx += 1

        acq.subject_idx = subject_idx
        acq.session_idx = session_idx

        # Auto-assign subject ID if not already set
        if not acq.subject:
            acq.subject = f"{subject_idx:02d}"

        prev_subject_key = subject_key
        prev_session_key = session_key

    return acquisitions


def determine_unique_series(acquisitions: list[Acquisition]) -> list[Acquisition]:
    """
    Determine unique series from acquisitions.

    Groups acquisitions by series characteristics and returns
    one representative acquisition per unique series.

    Parameters
    ----------
    acquisitions : list[Acquisition]
        All acquisitions

    Returns
    -------
    list[Acquisition]
        List of unique series (one per acquisition type)
    """
    seen_series: dict[tuple, int] = {}
    unique_series: list[Acquisition] = []

    for idx, acq in enumerate(acquisitions):
        # Create series key from characteristics
        series_key = (
            acq.series_description,
            acq.protocol_name,
            acq.echo_time,
            acq.repetition_time,
            acq.num_volumes,
            acq.direction,
            tuple(acq.image_type) if acq.image_type else (),
        )

        if series_key not in seen_series:
            seen_series[series_key] = len(unique_series)
            acq.series_idx = len(unique_series)
            unique_series.append(acq)
        else:
            acq.series_idx = seen_series[series_key]

    return unique_series
