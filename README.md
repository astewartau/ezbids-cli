# ezBIDS CLI

A command-line tool for converting neuroimaging data to BIDS format.

## Features

- **Schema-driven** - Uses [bidsschematools](https://github.com/bids-standard/bids-specification) as the source of truth for BIDS compliance
- **Automated BIDS conversion** - Analyzes NIfTI/JSON files and infers BIDS structure
- **Validation** - Validates datatype/suffix/entity combinations against the official BIDS schema
- **Multiple workflows** - Fully automated or interactive review modes
- **Configurable** - Use YAML config files for reproducible conversions
- **MRI support** - Supports anat, func, dwi, and fmap modalities

## Installation

```bash
pip install ezbids-cli
```

### Requirements

- Python 3.10+
- dcm2niix (for DICOM conversion)
- bids-validator (optional, for validation)

## Quick Start

### Basic Usage

Convert DICOM or NIfTI data to BIDS in one step:

```bash
ezbids convert ./my_data --output-dir ./bids_output
```

### Two-Stage Workflow

For more control, use the analyze → review → apply workflow:

```bash
# 1. Analyze data and generate mappings
ezbids analyze ./my_data --output-dir ./work

# 2. Review mappings interactively (optional)
ezbids review ./work/ezBIDS_core.json

# 3. Apply mappings to create BIDS dataset
ezbids apply ./work/ezBIDS_core.json ./bids_output
```

### Using Configuration Files

Generate a config template from your data:

```bash
ezbids init-config ./my_data --output my_config.yaml
```

Edit the config, then apply to new datasets:

```bash
ezbids convert ./new_data --config my_config.yaml --output-dir ./bids_output
```

## Commands

| Command | Description |
|---------|-------------|
| `analyze` | Analyze data and generate BIDS mappings |
| `convert` | Full pipeline: analyze + convert to BIDS |
| `review` | Interactive TUI for reviewing mappings |
| `apply` | Apply mappings to create BIDS dataset |
| `init-config` | Generate configuration template |
| `validate` | Run BIDS validator |

## Schema Integration

ezbids-cli uses `bidsschematools` to access the official BIDS specification schema. This ensures:

- **Correct entity ordering** - Filenames follow the canonical BIDS entity order
- **Valid suffix/entity combinations** - Only schema-valid combinations are allowed
- **Dynamic BIDS version** - Uses the current BIDS version from the schema
- **Required entity validation** - Warns when required entities are missing (e.g., `task` for func/bold)

```python
from ezbids_cli.schema import get_bids_version, get_required_entities

print(get_bids_version())  # e.g., "1.10.1"
print(get_required_entities("func", "bold"))  # ["task"]
print(get_required_entities("anat", "MEGRE"))  # ["echo"]
```

## Configuration

Example `ezbids_config.yaml`:

```yaml
version: "1.0"

dataset:
  name: "My Study"
  authors: ["Jane Doe"]

series:
  - match:
      series_description: ".*MPRAGE.*"
    datatype: anat
    suffix: T1w

  - match:
      series_description: ".*fMRI.*REST.*"
    datatype: func
    suffix: bold
    entities:
      task: rest

  - match:
      series_description: ".*localizer.*"
    exclude: true

output:
  link_mode: hardlink
  validate: true
```

## Development

```bash
# Clone the repository
git clone https://github.com/astewartau/ezbids-cli.git
cd ezbids-cli

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License

## Acknowledgments

Based on [ezBIDS](https://github.com/brainlife/ezbids) by the Brainlife team.
