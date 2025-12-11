"""CLI entry point for ezBIDS."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from ezbids_cli import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="ezbids")
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
@click.pass_context
def main(ctx: click.Context, verbose: int) -> None:
    """ezBIDS CLI - Convert neuroimaging data to BIDS format."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory for analysis results",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Configuration file (YAML)",
)
@click.pass_context
def analyze(
    ctx: click.Context,
    input_dir: Path,
    output_dir: Optional[Path],
    config: Optional[Path],
) -> None:
    """Analyze DICOM/NIfTI data and generate BIDS mapping.

    INPUT_DIR is the directory containing DICOM or NIfTI files.
    """
    from ezbids_cli.core.analyzer import Analyzer

    if output_dir is None:
        output_dir = input_dir / "ezbids_work"

    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold blue]Analyzing:[/] {input_dir}")
    console.print(f"[bold blue]Output:[/] {output_dir}")

    analyzer = Analyzer(input_dir, output_dir, config_path=config)
    result = analyzer.analyze()

    output_file = output_dir / "ezBIDS_core.json"
    console.print(f"[bold green]Analysis complete:[/] {output_file}")


@main.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="Output directory for BIDS dataset",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Configuration file (YAML)",
)
@click.option(
    "--link-mode",
    type=click.Choice(["hardlink", "symlink", "copy"]),
    default="hardlink",
    help="File linking strategy",
)
@click.option("--skip-validation", is_flag=True, help="Skip BIDS validation")
@click.pass_context
def convert(
    ctx: click.Context,
    input_dir: Path,
    output_dir: Path,
    config: Optional[Path],
    link_mode: str,
    skip_validation: bool,
) -> None:
    """Convert DICOM/NIfTI data to BIDS format.

    INPUT_DIR is the directory containing DICOM or NIfTI files.
    """
    from ezbids_cli.core.analyzer import Analyzer
    from ezbids_cli.convert.converter import BIDSConverter

    work_dir = output_dir / ".ezbids_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold blue]Converting:[/] {input_dir}")
    console.print(f"[bold blue]Output:[/] {output_dir}")

    # Step 1: Analyze
    console.print("[bold]Step 1/2:[/] Analyzing data...")
    analyzer = Analyzer(input_dir, work_dir, config_path=config)
    analysis_result = analyzer.analyze()

    # Step 2: Convert
    console.print("[bold]Step 2/2:[/] Converting to BIDS...")
    converter = BIDSConverter(
        analysis_result,
        output_dir,
        link_mode=link_mode,
    )
    converter.convert()

    if not skip_validation:
        console.print("[bold]Validating BIDS output...")
        # TODO: Run bids-validator

    console.print(f"[bold green]Conversion complete:[/] {output_dir}")


@main.command()
@click.argument("analysis_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Configuration file (YAML)",
)
@click.pass_context
def review(
    ctx: click.Context,
    analysis_file: Path,
    config: Optional[Path],
) -> None:
    """Launch interactive TUI to review and edit BIDS mappings.

    ANALYSIS_FILE is the ezBIDS_core.json file from the analyze command.
    """
    from ezbids_cli.tui.app import EzbidsTUI

    app = EzbidsTUI(analysis_file, config_path=config)
    app.run()


@main.command()
@click.argument("finalized_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option(
    "--link-mode",
    type=click.Choice(["hardlink", "symlink", "copy"]),
    default="hardlink",
    help="File linking strategy",
)
@click.pass_context
def apply(
    ctx: click.Context,
    finalized_file: Path,
    output_dir: Path,
    link_mode: str,
) -> None:
    """Apply finalized BIDS mappings to create dataset.

    FINALIZED_FILE is the finalized.json file from the review command.
    OUTPUT_DIR is the directory where the BIDS dataset will be created.
    """
    import json

    from ezbids_cli.convert.converter import BIDSConverter

    console.print(f"[bold blue]Applying:[/] {finalized_file}")
    console.print(f"[bold blue]Output:[/] {output_dir}")

    with open(finalized_file) as f:
        data = json.load(f)

    converter = BIDSConverter(data, output_dir, link_mode=link_mode)
    converter.convert()

    console.print(f"[bold green]BIDS dataset created:[/] {output_dir}")


@main.command("init-config")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("ezbids_config.yaml"),
    help="Output config file",
)
@click.pass_context
def init_config(
    ctx: click.Context,
    input_dir: Path,
    output: Path,
) -> None:
    """Generate a configuration template from analyzed data.

    INPUT_DIR is the directory containing DICOM or NIfTI files.
    """
    from ezbids_cli.config.exporter import export_config
    from ezbids_cli.core.analyzer import Analyzer

    console.print(f"[bold blue]Analyzing:[/] {input_dir}")

    work_dir = input_dir / ".ezbids_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    analyzer = Analyzer(input_dir, work_dir)
    analysis_result = analyzer.analyze()

    export_config(analysis_result, output)
    console.print(f"[bold green]Config template created:[/] {output}")


@main.command()
@click.argument("bids_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def validate(ctx: click.Context, bids_dir: Path) -> None:
    """Run BIDS validator on a dataset.

    BIDS_DIR is the root directory of the BIDS dataset.
    """
    from ezbids_cli.validation.validator import run_validator

    console.print(f"[bold blue]Validating:[/] {bids_dir}")
    result = run_validator(bids_dir)

    if result["valid"]:
        console.print("[bold green]Dataset is valid BIDS!")
    else:
        console.print("[bold red]Validation errors found:")
        for error in result.get("errors", []):
            console.print(f"  - {error}")


if __name__ == "__main__":
    main()
