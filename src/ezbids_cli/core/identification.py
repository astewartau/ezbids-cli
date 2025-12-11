"""Datatype and suffix identification for ezBIDS CLI.

This module contains the logic for identifying BIDS datatypes and suffixes
from imaging metadata.

Note: The SEARCH_TERMS heuristics must stay - they detect datatype from
metadata (series description, protocol name, etc.) which cannot come from
the BIDS schema. The schema only defines valid combinations, not detection rules.
"""

import re
from typing import Any, Optional

from ezbids_cli.core.models import Acquisition
from ezbids_cli.schema import validate_suffix_for_datatype


# Search terms for different datatypes/suffixes
SEARCH_TERMS: dict[str, dict[str, list[str]]] = {
    "exclude": {
        "localizer": ["localizer", "scout", "survey", "loc_"],
        "derived": ["trace", "_fa_", "adc", "colfa", "tensor"],
    },
    "anat": {
        "T1w": [
            "t1w", "t1_w", "tfl3d", "tfl_3d", "mprage", "mp_rage", "spgr",
            "tflmgh", "tfl_mgh", "t1mpr", "t1_mpr", "anatt1", "anat_t1",
            "3dt1", "3d_t1", "t1_", "_t1",
        ],
        "T2w": [
            "t2w", "t2_w", "anatt2", "anat_t2", "3dt2", "3d_t2",
            "t2spc", "t2_spc", "t2_", "_t2",
        ],
        "FLAIR": [
            "flair", "t2spacedafl", "t2_space_da_fl", "t2space_da_fl",
            "t2space_dafl", "t2_space_dafl", "dark_fluid",
        ],
        "T2starw": ["t2starw", "t2star_w", "t2star", "qsm", "swi"],
        "PDw": ["pdw", "pd_w", "proton_density"],
        "inplaneT1": ["inplanet1", "inplane_t1"],
        "inplaneT2": ["inplanet2", "inplane_t2"],
        "angio": ["angio", "tof", "mra"],
        "MEGRE": ["megre", "multi_echo_gre"],
        "MESE": ["mese", "multi_echo_se"],
        "UNIT1": ["uni", "unit1"],
        "MP2RAGE": ["mp2rage"],
        "T1map": ["t1map", "t1_map"],
        "T2map": ["t2map", "t2_map"],
        "T2starmap": ["t2starmap", "t2star_map", "r2starmap"],
        "PDmap": ["pdmap", "pd_map"],
        "Chimap": ["chimap", "chi_map", "susceptibility"],
    },
    "func": {
        "bold": [
            "bold", "func", "fmri", "f_mri", "fcmri", "fcfmri",
            "rsfmri", "rs_fmri", "rsmri", "task", "rest",
        ],
        "sbref": ["sbref", "sb_ref", "singleband"],
    },
    "dwi": {
        "dwi": ["dwi", "dti", "dmri", "d_mri", "diffusion", "hardi"],
        "sbref": ["sbref", "sb_ref", "b0", "bzero", "b_zero"],
    },
    "fmap": {
        "epi": [
            "fmap_spin", "fmap_se", "fmap_ap", "fmap_pa",
            "fieldmap_spin", "fieldmap_ap", "fieldmap_pa", "fieldmap_se",
            "spinecho", "spin_echo", "sefmri", "semri", "pepolar", "topup",
            "distortion", "b0map", "b0_map",
        ],
        "phasediff": ["phasediff", "phase_diff", "phdiff"],
        "phase1": ["phase1", "phase_1", "_e1_ph"],
        "phase2": ["phase2", "phase_2", "_e2_ph"],
        "magnitude1": ["magnitude1", "mag1", "mag_1", "_e1"],
        "magnitude2": ["magnitude2", "mag2", "mag_2", "_e2"],
        "magnitude": ["magnitude", "mag"],
        "fieldmap": ["fieldmap", "field_map", "grefieldmap", "gre_field_map"],
    },
}


def _normalize_description(text: str) -> str:
    """Normalize series description for matching."""
    return text.lower().replace(" ", "_").replace("-", "_")


def _check_search_terms(description: str, terms: list[str]) -> bool:
    """Check if any search terms match the description."""
    desc_normalized = _normalize_description(description)
    return any(term in desc_normalized for term in terms)


def _should_exclude(acq: Acquisition) -> tuple[bool, Optional[str]]:
    """Check if acquisition should be excluded."""
    desc = _normalize_description(acq.series_description)
    proto = _normalize_description(acq.protocol_name)

    # Check localizer patterns
    for term in SEARCH_TERMS["exclude"]["localizer"]:
        if term in desc or term in proto:
            return True, f"Excluded: matches localizer pattern '{term}'"

    # Check derived image patterns
    for term in SEARCH_TERMS["exclude"]["derived"]:
        if term in desc or term in proto:
            return True, f"Excluded: matches derived image pattern '{term}'"

    # Check for localizer indicator in path
    if "_i0000" in str(acq.nifti_path):
        return True, "Excluded: localizer indicator in filename"

    return False, None


def identify_anat(acq: Acquisition) -> tuple[Optional[str], Optional[str]]:
    """Identify anatomical datatype and suffix."""
    desc = _normalize_description(acq.series_description)
    proto = _normalize_description(acq.protocol_name)

    # Must be 3D
    if acq.ndim != 3:
        return None, None

    # Check for specific suffixes in order of specificity
    suffix_order = [
        "MP2RAGE", "UNIT1", "MEGRE", "MESE",
        "T1map", "T2map", "T2starmap", "PDmap", "Chimap",
        "T1w", "T2w", "FLAIR", "T2starw", "PDw",
        "inplaneT1", "inplaneT2", "angio",
    ]

    for suffix in suffix_order:
        if suffix not in SEARCH_TERMS["anat"]:
            continue

        terms = SEARCH_TERMS["anat"][suffix]
        if _check_search_terms(desc, terms) or _check_search_terms(proto, terms):
            # Additional checks for certain suffixes
            if suffix == "T1w":
                # Exclude if MP2RAGE-related terms present
                if any(x in desc for x in ["inv1", "inv2", "uni_images"]):
                    continue
            elif suffix == "T2w":
                # T2w typically has longer echo time
                if acq.echo_time > 0 and acq.echo_time < 50:
                    continue
            elif suffix == "MEGRE":
                # Multi-echo GRE requires echo number
                if acq.echo_number is None:
                    continue
            elif suffix == "MESE":
                # Multi-echo SE requires echo number
                if acq.echo_number is None:
                    continue
            elif suffix == "UNIT1":
                # UNIT1 should have UNI in ImageType
                if "UNI" not in acq.image_type:
                    continue
            elif suffix == "MP2RAGE":
                # MP2RAGE requires InversionTime
                if "InversionTime" not in acq.sidecar:
                    continue

            return "anat", suffix

    return None, None


def identify_func(acq: Acquisition) -> tuple[Optional[str], Optional[str]]:
    """Identify functional datatype and suffix."""
    desc = _normalize_description(acq.series_description)
    proto = _normalize_description(acq.protocol_name)

    # Check for exclusion patterns in ImageType
    excluded_types = ["DERIVED", "PERFUSION", "DIFFUSION", "ASL", "UNI"]
    if any(x in acq.image_type for x in excluded_types):
        return None, None

    # Check for bold
    if _check_search_terms(desc, SEARCH_TERMS["func"]["bold"]) or \
       _check_search_terms(proto, SEARCH_TERMS["func"]["bold"]):

        # BOLD should be 4D with multiple volumes
        if acq.ndim == 4 and acq.num_volumes > 1 and acq.repetition_time > 0:
            return "func", "bold"

        # SBRef is 3D with single volume
        if acq.ndim == 3 and acq.num_volumes == 1:
            if _check_search_terms(desc, SEARCH_TERMS["func"]["sbref"]):
                return "func", "sbref"

    return None, None


def identify_dwi(acq: Acquisition) -> tuple[Optional[str], Optional[str]]:
    """Identify diffusion datatype and suffix."""
    desc = _normalize_description(acq.series_description)
    proto = _normalize_description(acq.protocol_name)

    # Check for derived images
    if any(x in desc for x in ["trace", "_fa_", "adc"]):
        return None, None

    # Check if bvec file exists
    has_bvec = any(str(p).endswith(".bvec") for p in acq.paths)

    if _check_search_terms(desc, SEARCH_TERMS["dwi"]["dwi"]) or \
       _check_search_terms(proto, SEARCH_TERMS["dwi"]["dwi"]) or has_bvec:

        # DWI should have multiple volumes or bvec
        if has_bvec and acq.num_volumes > 1:
            return "dwi", "dwi"

        # SBRef or B0
        if acq.ndim == 3 and acq.num_volumes == 1:
            if _check_search_terms(desc, SEARCH_TERMS["dwi"]["sbref"]):
                return "dwi", "sbref"

    return None, None


def identify_fmap(acq: Acquisition) -> tuple[Optional[str], Optional[str]]:
    """Identify fieldmap datatype and suffix."""
    desc = _normalize_description(acq.series_description)
    proto = _normalize_description(acq.protocol_name)
    json_path = str(acq.json_path).lower()
    manufacturer = acq.sidecar.get("Manufacturer", "").upper()

    # Check for EPI fieldmaps (spin echo, PEPOLAR)
    if _check_search_terms(desc, SEARCH_TERMS["fmap"]["epi"]) or \
       _check_search_terms(proto, SEARCH_TERMS["fmap"]["epi"]):
        # EPI fmaps typically have few volumes
        if acq.num_volumes <= 10 and acq.echo_number is None:
            if manufacturer != "GE":
                return "fmap", "epi"

    # Check for GRE fieldmaps
    is_gre_fmap = _check_search_terms(desc, ["fieldmap", "gre"]) or \
                  _check_search_terms(proto, ["fieldmap", "gre"])

    if is_gre_fmap or acq.echo_number is not None:
        # Check echo number for multi-echo GRE fieldmaps
        if acq.echo_number == 1:
            if "_e1_ph" in json_path or "phase" in desc:
                return "fmap", "phase1"
            else:
                return "fmap", "magnitude1"
        elif acq.echo_number == 2:
            if "_e2_ph" in json_path or "phase" in desc:
                # Could be phasediff or phase2 - need context
                return "fmap", "phasediff"
            else:
                return "fmap", "magnitude2"

    # GE-specific fieldmaps
    if manufacturer == "GE" and is_gre_fmap:
        if "phase" in desc or "ph" in desc:
            return "fmap", "fieldmap"
        else:
            return "fmap", "magnitude"

    return None, None


def identify_acquisition(acq: Acquisition) -> Acquisition:
    """
    Identify the BIDS datatype and suffix for an acquisition.

    Parameters
    ----------
    acq : Acquisition
        Acquisition to identify

    Returns
    -------
    Acquisition
        Updated acquisition with datatype, suffix, and type set
    """
    # Check for exclusion first
    should_exclude, message = _should_exclude(acq)
    if should_exclude:
        acq.exclude = True
        acq.type = "exclude"
        acq.message = message
        return acq

    # Try each modality in order
    datatype, suffix = None, None

    # Order matters - more specific checks first
    if datatype is None:
        datatype, suffix = identify_dwi(acq)

    if datatype is None:
        datatype, suffix = identify_fmap(acq)

    if datatype is None:
        datatype, suffix = identify_func(acq)

    if datatype is None:
        datatype, suffix = identify_anat(acq)

    # Set results
    if datatype and suffix:
        # Validate against schema
        is_valid, error = validate_suffix_for_datatype(datatype, suffix)
        if is_valid:
            acq.datatype = datatype
            acq.suffix = suffix
            acq.type = f"{datatype}/{suffix}"
            acq.message = f"Identified as {datatype}/{suffix}"
        else:
            # Heuristics found something but schema doesn't recognize it
            acq.datatype = datatype
            acq.suffix = suffix
            acq.type = f"{datatype}/{suffix}"
            acq.message = f"Identified as {datatype}/{suffix} (validation warning: {error})"
    else:
        # Unknown - don't exclude, but mark as unidentified
        acq.type = ""
        acq.message = "Could not automatically identify datatype/suffix"
        acq.error = "Unidentified acquisition - please set datatype and suffix manually"

    return acq


def identify_all_acquisitions(acquisitions: list[Acquisition]) -> list[Acquisition]:
    """
    Identify datatype and suffix for all acquisitions.

    Parameters
    ----------
    acquisitions : list[Acquisition]
        List of acquisitions to identify

    Returns
    -------
    list[Acquisition]
        Updated acquisitions with identification results
    """
    for acq in acquisitions:
        identify_acquisition(acq)

    # Post-processing: Check for DWI b0 maps that should be fmap/epi
    _check_dwi_b0maps(acquisitions)

    return acquisitions


def _check_dwi_b0maps(acquisitions: list[Acquisition]) -> None:
    """
    Check for DWI sequences that are actually B0 fieldmaps.

    DWI sequences with very few volumes (<10) and no actual diffusion
    weighting might be intended as fieldmaps.
    """
    for acq in acquisitions:
        if acq.datatype == "dwi" and acq.suffix == "dwi":
            # If very few volumes and has direction entity, might be fmap
            if acq.num_volumes < 10 and acq.direction:
                # Check if there are other DWI sequences with more volumes
                other_dwi = [
                    a for a in acquisitions
                    if a.datatype == "dwi" and a.suffix == "dwi"
                    and a.num_volumes > 10 and a is not acq
                ]
                if other_dwi:
                    acq.datatype = "fmap"
                    acq.suffix = "epi"
                    acq.type = "fmap/epi"
                    acq.message = "Reclassified from dwi to fmap/epi (low volume count)"
