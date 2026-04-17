# Environment

This document specifies the Python environment used for the IBL fiber photometry to NWB conversion, including all installed packages, key dependencies, and version pinning.

## Creating the Environment

### Using conda (recommended)

```bash
git clone https://github.com/catalystneuro/IBL-fiberphotometry-to-nwb.git
cd IBL-fiberphotometry-to-nwb
conda env create --file make_env.yml
conda activate ibl_fiberphotometry_to_nwb_env
pip install --editable .
```

The `make_env.yml` file creates a conda environment named `ibl_fiberphotometry_to_nwb_env` with Python 3.13 and installs the package in editable mode.

### Using pip only

```bash
git clone https://github.com/catalystneuro/IBL-fiberphotometry-to-nwb.git
cd IBL-fiberphotometry-to-nwb
pip install --editable .
```

## Python Version

- **Python 3.13** (conda-forge `cpython 3.13.12`)
- Supported: Python 3.10, 3.11, 3.12, 3.13

## Key Dependencies

These are the core libraries that the conversion pipeline directly depends on:

### NWB Ecosystem

| Package | Version | Description |
|---------|---------|-------------|
| `pynwb` | 3.1.4.dev14 | Python API for NWB files (development build) |
| `hdmf` | 5.1.0 | Hierarchical Data Modeling Framework (NWB backend) |
| `hdmf-zarr` | 0.12.0 | Zarr backend for HDMF |
| `neuroconv` | 0.9.2 | Data conversion framework for NWB (pinned to `0.7.0` in `[fiber_photometry]` extras) |
| `nwbinspector` | 0.6.5 | NWB file validation tool |

### NWB Extensions (ndx)

| Package | Version | Description |
|---------|---------|-------------|
| `ndx-fiber-photometry` | 0.2.3 | Fiber photometry data types (`FiberPhotometryTable`, `FiberPhotometryResponseSeries`) |
| `ndx-ophys-devices` | 0.3.1 | Optical physiology device types (`OpticalFiber`, `ExcitationSource`, etc.) |
| `ndx-anatomical-localization` | 0.1.0 | Anatomical coordinate tables (`Localization`, `AnatomicalCoordinatesTable`) |
| `ndx-ibl` | 0.3.0 | IBL-specific NWB extensions (`IblSubject`) |
| `ndx-ibl-bwm` | 0.1.0 | IBL Brain Wide Map extensions |
| `ndx-events` | 0.2.1 | Event data types |
| `ndx-pose` | 0.2.2 | Pose estimation data types |

### IBL Ecosystem

| Package | Version | Description |
|---------|---------|-------------|
| `ibllib` | 3.4.3 | IBL core library (photometry branch) |
| `one-api` | 3.4.2 | ONE API client for IBL data access |
| `ibl-to-nwb` | 0.3.0 | Parent IBL-to-NWB pipeline (heberto_conversion branch) |
| `iblatlas` | 0.10.0 | IBL brain atlas tools |
| `iblutil` | 1.20.0 | IBL shared utilities |
| `ibl-neuropixel` | 1.10.0 | IBL Neuropixels tools |
| `ibl-photometry` | 0.2.0 | IBL fiber photometry analysis |
| `ibl-style` | 0.1.0 | IBL plotting styles |

### Scientific Computing

| Package | Version | Description |
|---------|---------|-------------|
| `numpy` | 2.2.0 | Array computing |
| `scipy` | 1.17.0 | Scientific algorithms |
| `pandas` | 2.3.3 | DataFrames and tabular data |
| `h5py` | 3.15.1 | HDF5 file I/O |
| `matplotlib` | 3.10.8 | Plotting |
| `scikit-learn` | 1.8.0 | Machine learning |
| `scikit-image` | 0.26.0 | Image processing |
| `xarray` | 2026.2.0 | Labeled multi-dimensional arrays |
| `dask` | 2026.1.2 | Parallel computing |
| `statsmodels` | 0.14.6 | Statistical models |
| `numba` | 0.63.1 | JIT compilation for numerical code |

### Neuroscience Tools

| Package | Version | Description |
|---------|---------|-------------|
| `pynapple` | 0.10.3 | Neurophysiology data analysis |
| `neo` | 0.14.3 | Electrophysiology data I/O |
| `spikeinterface` | 0.103.2 | Spike sorting framework |
| `probeinterface` | 0.3.1 | Electrode probe handling |
| `brainglobe-atlasapi` | 2.3.0 | Brain atlas API |
| `brainrender` | 2.1.17 | 3D brain visualization |

### DANDI Archive

| Package | Version | Description |
|---------|---------|-------------|
| `dandi` | 0.74.3 | DANDI Archive client |
| `dandischema` | 0.12.1 | DANDI metadata schemas |
| `zarr` | 2.18.7 | Zarr array storage |
| `remfile` | 0.1.13 | Remote file streaming (for DANDI) |

### Visualization

| Package | Version | Description |
|---------|---------|-------------|
| `seaborn` | 0.13.2 | Statistical data visualization |
| `vedo` | 2026.6.1 | 3D visualization |
| `vtk` | 9.6.0 | 3D rendering backend |
| `ipywidgets` | 8.1.8 | Jupyter interactive widgets |

### Development Tools

| Package | Version | Description |
|---------|---------|-------------|
| `ruff` | 0.15.1 | Fast Python linter and formatter |
| `flake8` | 7.3.0 | Python linter |
| `pytest` | 9.0.2 | Testing framework |
| `ipython` | 9.10.0 | Interactive Python shell |
| `ipykernel` | 7.2.0 | Jupyter kernel |

## Version Pinning

The `pyproject.toml` declares all dependencies in the `[project] dependencies` list. `neuroconv` is pinned to a specific version for reproducibility:

```toml
dependencies = [
  "neuroconv==0.9.2",
  "nwbinspector",
  "ONE-api",
  "ibllib@git+https://github.com/int-brain-lab/ibllib.git@photometry",
  "ndx-ibl-bwm@git+https://github.com/int-brain-lab/ndx-ibl-bwm.git",
  "ibl-to-nwb@git+https://github.com/h-mayorquin/IBL-to-nwb.git@heberto_conversion",
  "ndx-ibl@git+https://github.com/catalystneuro/ndx-ibl.git",
  "ndx-fiber-photometry",
]
```

### Git Dependencies

Several packages are installed from specific Git branches:

| Package | Repository | Branch |
|---------|-----------|--------|
| `ibllib` | `int-brain-lab/ibllib` | `photometry` |
| `ndx-ibl-bwm` | `int-brain-lab/ndx-ibl-bwm` | default |
| `ibl-to-nwb` | `h-mayorquin/IBL-to-nwb` | `heberto_conversion` |
| `ndx-ibl` | `catalystneuro/ndx-ibl` | default |

## Frozen Requirements

A complete `pip freeze` snapshot of the environment is available at
[requirements_freeze.txt](../../requirements_freeze.txt). This file pins every
installed package (including transitive dependencies) and can be used to
reproduce the exact environment:

```bash
pip install -r requirements_freeze.txt
```

---

## Reproducing the Environment

To reproduce the exact environment on a different machine:

1. Create a fresh conda environment with Python 3.13:
   ```bash
   conda create -n ibl_fiberphotometry_to_nwb_env python=3.13 -c conda-forge
   conda activate ibl_fiberphotometry_to_nwb_env
   ```

2. Install the package with the fiber photometry extras:
   ```bash
   pip install --editable .
   ```

3. For additional analysis tools (pynapple, brainrender, etc.), install them separately:
   ```bash
   pip install pynapple brainrender brainglobe-atlasapi seaborn
   ```

## Platform Notes

- The current environment was built and tested on **Windows 11 Pro** (10.0.26200)
- The pipeline uses standard cross-platform Python libraries and should work on Linux and macOS
- HDF5 file I/O is handled by `h5py` which has platform-specific binary wheels

## Related Documents

- [introduction_to_development.md](introduction_to_development.md) — Development workflow and code style
- [pyproject.toml](../../pyproject.toml) — Project metadata and dependency declarations
- [make_env.yml](../../make_env.yml) — Conda environment definition
