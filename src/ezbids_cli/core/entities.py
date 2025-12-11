"""Entity label extraction for ezBIDS CLI.

This module extracts BIDS entity labels (task, acq, run, dir, echo, etc.)
from acquisition metadata.
"""

import re
from typing import Optional

from ezbids_cli.core.models import Acquisition
from ezbids_cli.schema import (
    get_entity_order,
    get_required_entities,
    validate_entities_for_file,
)


def extract_task_entity(acq: Acquisition) -> Optional[str]:
    """
    Extract task entity from acquisition metadata.

    Parameters
    ----------
    acq : Acquisition
        Acquisition to extract task from

    Returns
    -------
    str or None
        Task name or None if not found
    """
    desc = acq.series_description.lower()
    proto = acq.protocol_name.lower()

    # Common task patterns
    task_patterns = [
        r"task[_-]?(\w+)",
        r"(\w+)[_-]?task",
        r"rest",
        r"motor",
        r"language",
        r"memory",
        r"attention",
        r"emotion",
        r"faces",
        r"localizer",
    ]

    for pattern in task_patterns:
        match = re.search(pattern, desc) or re.search(pattern, proto)
        if match:
            task = match.group(1) if match.lastindex else match.group(0)
            # Clean task name (alphanumeric only)
            task = re.sub(r"[^a-zA-Z0-9]", "", task)
            if task and len(task) >= 2:
                return task

    # Default to "rest" for resting state
    if "rest" in desc or "rest" in proto or "rsfmri" in desc:
        return "rest"

    # For func data without clear task, use generic name
    if acq.datatype == "func":
        return "task"

    return None


def extract_direction_entity(acq: Acquisition) -> Optional[str]:
    """
    Extract phase encoding direction entity.

    Parameters
    ----------
    acq : Acquisition
        Acquisition to extract direction from

    Returns
    -------
    str or None
        Direction label (AP, PA, LR, RL, etc.) or None
    """
    # Use pre-computed direction if available
    if acq.direction:
        return acq.direction

    # Try to extract from description
    desc = acq.series_description.lower()
    proto = acq.protocol_name.lower()

    direction_patterns = [
        (r"[_-](ap)[_-]?", "AP"),
        (r"[_-](pa)[_-]?", "PA"),
        (r"[_-](lr)[_-]?", "LR"),
        (r"[_-](rl)[_-]?", "RL"),
        (r"[_-](si)[_-]?", "SI"),
        (r"[_-](is)[_-]?", "IS"),
    ]

    for pattern, direction in direction_patterns:
        if re.search(pattern, desc) or re.search(pattern, proto):
            return direction

    return None


def extract_acquisition_entity(acq: Acquisition) -> Optional[str]:
    """
    Extract acquisition label entity.

    Parameters
    ----------
    acq : Acquisition
        Acquisition to extract acq label from

    Returns
    -------
    str or None
        Acquisition label or None
    """
    desc = acq.series_description.lower()
    proto = acq.protocol_name.lower()

    # Common acquisition label patterns
    acq_patterns = [
        r"acq[_-]?(\w+)",
        r"(highres|lowres|hires|lores)",
        r"(mb\d+)",  # Multiband
        r"(norm|prenorm|postnorm)",
    ]

    for pattern in acq_patterns:
        match = re.search(pattern, desc) or re.search(pattern, proto)
        if match:
            label = match.group(1) if match.lastindex else match.group(0)
            label = re.sub(r"[^a-zA-Z0-9]", "", label)
            if label:
                return label

    return None


def extract_run_entity(acq: Acquisition) -> Optional[str]:
    """
    Extract run number entity.

    Parameters
    ----------
    acq : Acquisition
        Acquisition to extract run from

    Returns
    -------
    str or None
        Run number or None
    """
    desc = acq.series_description.lower()
    proto = acq.protocol_name.lower()
    path = str(acq.nifti_path).lower()

    # Run patterns - be specific to avoid matching other numbers like TI, TE, etc.
    run_patterns = [
        r"run[_-]?(\d+)",
        r"_r(\d+)_",
    ]

    for pattern in run_patterns:
        for text in [desc, proto, path]:
            match = re.search(pattern, text)
            if match:
                run_num = match.group(1)
                # Pad to 2 digits
                return run_num.zfill(2)

    return None


def extract_echo_entity(acq: Acquisition) -> Optional[str]:
    """
    Extract echo number entity.

    Parameters
    ----------
    acq : Acquisition
        Acquisition to extract echo from

    Returns
    -------
    str or None
        Echo number or None
    """
    # Use echo number from metadata
    if acq.echo_number is not None:
        return str(acq.echo_number)

    # Try to extract from description or path
    desc = acq.series_description.lower()
    path = str(acq.json_path).lower()

    echo_patterns = [
        r"echo[_-]?(\d+)",
        r"e(\d+)[_-]",
        r"_e(\d+)",
    ]

    for pattern in echo_patterns:
        for text in [desc, path]:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

    return None


def extract_part_entity(acq: Acquisition) -> Optional[str]:
    """
    Extract part entity (mag, phase, real, imag).

    Parameters
    ----------
    acq : Acquisition
        Acquisition to extract part from

    Returns
    -------
    str or None
        Part label or None
    """
    desc = acq.series_description.lower()
    path = str(acq.json_path).lower()
    image_type = [x.lower() for x in acq.image_type]

    # Check ImageType
    if "p" in image_type or "phase" in image_type:
        return "phase"
    if "m" in image_type or "magnitude" in image_type:
        return "mag"
    if "real" in image_type:
        return "real"
    if "imaginary" in image_type:
        return "imag"

    # Check description/path
    if "_ph" in path or "phase" in desc:
        return "phase"
    if "mag" in desc and "phase" not in desc:
        return "mag"

    return None


def extract_reconstruction_entity(acq: Acquisition) -> Optional[str]:
    """
    Extract reconstruction entity.

    Parameters
    ----------
    acq : Acquisition
        Acquisition to extract reconstruction from

    Returns
    -------
    str or None
        Reconstruction label or None
    """
    desc = acq.series_description.lower()
    proto = acq.protocol_name.lower()

    rec_patterns = [
        r"rec[_-]?(\w+)",
        r"(moco|nomoco)",
        r"(nd|filtered)",
    ]

    for pattern in rec_patterns:
        match = re.search(pattern, desc) or re.search(pattern, proto)
        if match:
            label = match.group(1) if match.lastindex else match.group(0)
            label = re.sub(r"[^a-zA-Z0-9]", "", label)
            if label:
                return label

    return None


def extract_entity_labels(acquisitions: list[Acquisition]) -> list[Acquisition]:
    """
    Extract entity labels for all acquisitions.

    Parameters
    ----------
    acquisitions : list[Acquisition]
        List of acquisitions

    Returns
    -------
    list[Acquisition]
        Updated acquisitions with entities extracted
    """
    for acq in acquisitions:
        if acq.exclude:
            continue

        entities: dict[str, str] = {}

        # Get required entities from schema
        required = get_required_entities(acq.datatype, acq.suffix)

        # Task entity (required for func)
        if "task" in required or acq.datatype == "func":
            task = extract_task_entity(acq)
            if task:
                entities["task"] = task

        # Direction entity (required for fmap/epi)
        if "direction" in required or acq.datatype == "fmap":
            direction = extract_direction_entity(acq)
            if direction:
                entities["direction"] = direction

        # Echo entity (required for multi-echo)
        if "echo" in required:
            echo = extract_echo_entity(acq)
            if echo:
                entities["echo"] = echo

        # Optional entities - always try to extract
        acq_label = extract_acquisition_entity(acq)
        if acq_label:
            entities["acquisition"] = acq_label

        run = extract_run_entity(acq)
        if run:
            entities["run"] = run

        # Echo if not already extracted
        if "echo" not in entities:
            echo = extract_echo_entity(acq)
            if echo:
                entities["echo"] = echo

        part = extract_part_entity(acq)
        if part:
            entities["part"] = part

        rec = extract_reconstruction_entity(acq)
        if rec:
            entities["reconstruction"] = rec

        acq.entities = entities

        # Validate entities against schema
        if acq.datatype and acq.suffix:
            errors = validate_entities_for_file(acq.datatype, acq.suffix, entities)
            if errors:
                # Filter to only show missing required entities as errors
                missing_required = [e for e in errors if "Missing required" in e]
                if missing_required:
                    acq.error = "; ".join(missing_required)

    return acquisitions


def order_entities(entities: dict[str, str]) -> dict[str, str]:
    """
    Order entities according to BIDS specification.

    Parameters
    ----------
    entities : dict[str, str]
        Unordered entities

    Returns
    -------
    dict[str, str]
        Ordered entities
    """
    entity_order = get_entity_order()
    ordered = {}

    for entity_name in entity_order:
        if entity_name in entities:
            ordered[entity_name] = entities[entity_name]

    # Add any remaining entities not in the standard order
    for key, value in entities.items():
        if key not in ordered:
            ordered[key] = value

    return ordered
