# Development

This section covers the development environment, code style, and project structure for contributing to the IBL fiber photometry to NWB conversion pipeline.

## Project Structure

```text
IBL-fiberphotometry-to-nwb/
+-- LICENSE
+-- make_env.yml                         # Conda environment definition
+-- pyproject.toml                       # Project metadata and dependencies
+-- README.md                            # Project overview and quick start
+-- documentation/                       # This documentation
|   +-- introduction_to_documentation.md
|   +-- conversion/
|   +-- development/
|   +-- ibl_science/
|   +-- one_api_data_access/
+-- src/
    +-- ibl_fiberphotometry_to_nwb/
        +-- __init__.py
        +-- another_conversion/          # Placeholder for additional conversion types
        +-- fiber_photometry/
            +-- __init__.py
            +-- nwbconverter.py          # IblConverter and FiberPhotometryNWBConverter
            +-- convert_session.py       # session_to_nwb() -- single-session entry point
            +-- convert_all_sessions.py  # dataset_to_nwb() -- batch entry point
            +-- conversion_notes.md      # Design notes and extension guide
            +-- _metadata/
            |   +-- general_metadata.yaml     # Experiment-level NWB metadata
            |   +-- fiber_photometry.yaml     # Hardware specifications
            |   +-- pupils.yml                # Pupil tracking metadata
            |   +-- trials.yml                # Trials metadata
            |   +-- wheel.yml                 # Wheel metadata
            +-- datainterfaces/
            |   +-- __init__.py
            |   +-- _fiber_photometry_interfaces.py
            |   +-- _fp_wheel_interfaces.py
            |   +-- _optical_fibers_anatomical_localization_interface.py
            +-- tutorials/
            |   +-- fiber_photometry.ipynb    # Tutorial notebook
            +-- utils/
                +-- __init__.py
                +-- tasks.py                  # Task discovery and protocol mapping
```

## Code Style

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and import sorting:

```toml
[tool.ruff.lint]
select = [
    "F401",   # Unused import
    "I",      # All isort rules
    "UP006",  # non-pep585 annotation
    "UP007",  # non-pep604 annotation
    "UP045",  # non-pep604 annotation (Optional)
]
```

Line length is 120 characters (configured in `[tool.black]`).

Run the linter:

```bash
ruff check src/
ruff format src/
```

## Development Installation

```bash
git clone https://github.com/catalystneuro/IBL-fiberphotometry-to-nwb.git
cd IBL-fiberphotometry-to-nwb
conda env create --file make_env.yml
conda activate ibl_fiberphotometry_to_nwb_env
pip install --editable .
```

The `--editable` flag ensures that changes to the source code take effect immediately without reinstalling.

## Adding a New Conversion

The `another_conversion/` directory is a placeholder for additional conversion types. To add a new modality:

1. Create a new directory under `src/ibl_fiberphotometry_to_nwb/`.
2. Implement data interfaces inheriting from `BaseIBLDataInterface` or existing interfaces.
3. Create an `NWBConverter` subclass combining all interfaces.
4. Write `convert_session.py` and `convert_all_sessions.py` scripts.
5. Add metadata YAML files for experiment-level and hardware metadata.

See [conversion_notes.md](../../src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md) for detailed instructions.

## Documents in This Section

- [environment.md](environment.md) — Full environment specification: installed packages, key dependencies, version pinning

## Related Sections

- [Conversion](../conversion/) — NWB conversion architecture and how-to guides
- [conversion_notes.md](../../src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md) — Design decisions and extension instructions
