"""dcm2niix wrapper for DICOM to NIfTI conversion."""

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def find_dcm2niix() -> Optional[str]:
    """Find dcm2niix executable."""
    import shutil

    # First try shutil.which (respects PATH)
    path = shutil.which("dcm2niix")
    if path:
        return path

    # Try common locations
    common_paths = [
        "/usr/bin/dcm2niix",
        "/usr/local/bin/dcm2niix",
        "/opt/dcm2niix/bin/dcm2niix",
    ]

    for p in common_paths:
        if Path(p).exists():
            return p

    return None


def check_dcm2niix() -> bool:
    """Check if dcm2niix is available."""
    return find_dcm2niix() is not None


def run_dcm2niix(
    input_dir: Path,
    output_dir: Path,
    filename_format: str = "time-%t-sn-%s",
    compress: bool = True,
    verbose: bool = False,
    timeout: int = 3600,
) -> dict:
    """
    Run dcm2niix to convert DICOM to NIfTI.

    Parameters
    ----------
    input_dir : Path
        Directory containing DICOM files
    output_dir : Path
        Output directory for NIfTI files
    filename_format : str
        Output filename format (dcm2niix -f option)
    compress : bool
        Compress output to .nii.gz
    verbose : bool
        Show detailed output
    timeout : int
        Timeout in seconds

    Returns
    -------
    dict
        Result with 'success', 'output_files', 'stdout', 'stderr'
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    dcm2niix_path = find_dcm2niix()
    if not dcm2niix_path:
        return {
            "success": False,
            "returncode": -1,
            "output_files": [],
            "json_files": [],
            "stdout": "",
            "stderr": "dcm2niix not found",
        }

    cmd = [
        dcm2niix_path,
        "-z", "y" if compress else "n",  # Compress output
        "-f", filename_format,            # Filename format
        "-o", str(output_dir),            # Output directory
        "-d", "9",                         # Search depth
        "-ba", "n",                        # Don't anonymize
    ]

    if verbose:
        cmd.extend(["-v", "1"])

    cmd.append(str(input_dir))

    console.print(f"[dim]Running: {' '.join(cmd)}[/]")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Find output files
        nifti_files = list(output_dir.glob("*.nii.gz")) + list(output_dir.glob("*.nii"))
        json_files = list(output_dir.glob("*.json"))

        success = result.returncode == 0 and len(nifti_files) > 0

        if verbose or not success:
            if result.stdout:
                console.print(f"[dim]{result.stdout}[/]")
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/]")

        return {
            "success": success,
            "returncode": result.returncode,
            "output_files": nifti_files,
            "json_files": json_files,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "output_files": [],
            "json_files": [],
            "stdout": "",
            "stderr": f"dcm2niix timed out after {timeout} seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "output_files": [],
            "json_files": [],
            "stdout": "",
            "stderr": str(e),
        }


def is_dicom_directory(path: Path) -> bool:
    """
    Check if a directory contains DICOM files.

    Parameters
    ----------
    path : Path
        Directory to check

    Returns
    -------
    bool
        True if DICOM files found
    """
    # Common DICOM file patterns
    dicom_patterns = ["*.dcm", "*.DCM", "*.ima", "*.IMA"]

    for pattern in dicom_patterns:
        if list(path.rglob(pattern)):
            return True

    # Check for files without extension that might be DICOM
    # DICOM files often have no extension
    for f in path.rglob("*"):
        if f.is_file() and not f.suffix:
            # Quick check for DICOM magic bytes
            try:
                with open(f, "rb") as fp:
                    fp.seek(128)
                    magic = fp.read(4)
                    if magic == b"DICM":
                        return True
            except (IOError, OSError):
                pass
            break  # Only check first file

    return False


def preprocess_input(
    input_dir: Path,
    work_dir: Path,
    verbose: bool = False,
) -> tuple[Path, bool]:
    """
    Preprocess input directory - run dcm2niix if needed.

    Parameters
    ----------
    input_dir : Path
        Input directory (may contain DICOM or NIfTI)
    work_dir : Path
        Working directory for intermediate files
    verbose : bool
        Show detailed output

    Returns
    -------
    tuple[Path, bool]
        (Path to NIfTI files, whether preprocessing was run)
    """
    # Check if already has NIfTI files
    nifti_files = list(input_dir.rglob("*.nii.gz")) + list(input_dir.rglob("*.nii"))
    if nifti_files:
        console.print(f"[dim]Found {len(nifti_files)} NIfTI files[/]")
        return input_dir, False

    # Check for DICOM
    if is_dicom_directory(input_dir):
        console.print("[dim]DICOM files detected, running dcm2niix...[/]")

        if not check_dcm2niix():
            console.print("[red]Error: dcm2niix not found. Please install it first.[/]")
            console.print("[dim]Install with: apt install dcm2niix (Linux) or brew install dcm2niix (macOS)[/]")
            return input_dir, False

        nifti_dir = work_dir / "nifti"
        result = run_dcm2niix(input_dir, nifti_dir, verbose=verbose)

        if result["success"]:
            console.print(f"[green]Converted {len(result['output_files'])} files[/]")
            return nifti_dir, True
        else:
            console.print(f"[red]dcm2niix failed: {result['stderr']}[/]")
            return input_dir, False

    console.print("[yellow]No DICOM or NIfTI files found in input directory[/]")
    return input_dir, False
