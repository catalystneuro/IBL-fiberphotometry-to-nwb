# Notes concerning the fiber_photometry conversion

This document describes design decisions, known limitations, and step-by-step
instructions for extending the IBL fiber photometry → NWB conversion pipeline.

---

## Table of Contents

1. [Architecture overview](#architecture-overview)
2. [Data modalities and NWB mapping](#data-modalities-and-nwb-mapping)
3. [Metadata files](#metadata-files)
4. [Known limitations and TODOs](#known-limitations-and-todos)
5. [How to modify FiberPhotometryInterface](#how-to-modify-fiberphotometryinterface)
6. [How to modify OpticalFibersAnatomicalLocalizationInterface](#how-to-modify-opticalfibersanatomicallocalizationinterface)
7. [Wheel interfaces and task collections](#wheel-interfaces-and-task-collections)
8. [Availability checking pattern](#availability-checking-pattern)
9. [Converter and metadata pipeline](#converter-and-metadata-pipeline)

---

## Architecture overview

The conversion pipeline is structured as a set of **data interfaces** combined
by a **NWB converter**:

```text
session_to_nwb()
│
├── FiberPhotometryInterface           (fiber_photometry/datainterfaces/)
├── OpticalFibersAnatomicalLocalizationInterface
├── BrainwideMapTrialsInterface        (from ibl_to_nwb)
├── FiberPhotometryWheelPositionInterface
├── FiberPhotometryWheelKinematicsInterface
├── FiberPhotometryWheelMovementsInterface
├── SessionEpochsInterface             (from ibl_to_nwb)
├── PassiveIntervalsInterface          (from ibl_to_nwb)
├── PassiveReplayStimInterface         (from ibl_to_nwb)
├── LickInterface                      (from ibl_to_nwb)
├── IblPoseEstimationInterface × 3     (left/right/body cameras)
├── PupilTrackingInterface × 2         (left/right cameras)
├── RoiMotionEnergyInterface × 3
└── RawVideoInterface × 3
        │
        ▼
FiberPhotometryNWBConverter
        │
        ▼
NWBFile (written to disk)
```

Each interface:

1. Declares required files via `get_data_requirements()`.
2. Reports availability via `check_availability()` (no downloads).
3. Adds data to the NWB file via `add_to_nwbfile()`.
4. Optionally contributes metadata via `get_metadata()`.

**Order matters**: `FiberPhotometryInterface` must run before
`OpticalFibersAnatomicalLocalizationInterface` because it creates the
`OpticalFiber` devices and the `FiberPhotometryTable` that the localization
interface depends on.

---

## Data modalities and NWB mapping

| Interface | NWB container | NWB type |
| --- | --- | --- |
| `FiberPhotometryInterface` | `acquisition/gcamp_signal`, `acquisition/isosbestic_signal` | `FiberPhotometryResponseSeries` |
| `FiberPhotometryInterface` | `lab_meta_data/fiber_photometry` | `FiberPhotometry` (table + devices) |
| `OpticalFibersAnatomicalLocalizationInterface` | `lab_meta_data/localization` | `Localization` with `AnatomicalCoordinatesTable` objects |
| Wheel interfaces | `processing/behavior/Wheel*` | `TimeSeries`, `IntervalSeries` |
| `BrainwideMapTrialsInterface` | `intervals/trials` | `TimeIntervals` |
| `SessionEpochsInterface` | `intervals/epochs` | `TimeIntervals` |
| Camera interfaces | `processing/behavior/PoseEstimation*` etc. | various |

---

## Metadata files

### `_metadata/general_metadata.yaml`

Experiment-level NWB metadata (keywords, experiment description). Applied to
every session in the dataset.

### `_metadata/fiber_photometry.yaml`

Hardware specification template. Contains `# TODO` markers for fields that
need to be filled in:

- Optical fiber: manufacturer, model number, numerical aperture, core diameter,
  active length, ferrule diameter and name, serial number.
- Excitation source models: manufacturer, model number, confirmed wavelength
  ranges.
- Photodetector model: description, manufacturer, model number, detector type,
  gain, gain unit.
- Optical filters: confirmed centre wavelengths and bandwidths.
- Dichroic mirror: description, manufacturer, model number.
- GCaMP indicator: manufacturer.
- Fiber insertion: AP/ML/DV coordinates, position reference, hemisphere.

Fill in these values once the hardware information is available.

---

## Known limitations and TODOs

1. **Fiber tip coordinates are placeholders.** Both
   `AnatomicalCoordinatesIBLBregmaOpticalFibers` and
   `AnatomicalCoordinatesCCFv3OpticalFibers` tables are populated with
   `float("nan")` for x/y/z and `"TODO"` for the brain region. These must be
   replaced once the IBL histology / atlas registration pipeline provides
   the coordinates. See
   [How to modify OpticalFibersAnatomicalLocalizationInterface](#how-to-modify-opticalfibersanatomicallocalizationinterface).

2. **Hardware metadata is incomplete.** Most fields in
   `fiber_photometry.yaml` are marked `# TODO`. The conversion pipeline
   runs correctly with placeholder values, but the metadata should be
   completed before DANDI upload.

3. **`PassiveRFMInterface` is temporarily disabled.** It is commented out in
   `convert_session.py` pending an upstream fix for data quality issues.

4. **`IblConverter.get_metadata()` does not include `session_metadata['number']`.**
   This field is noted with a `# TODO` comment and could be added to an NWB
   extension attribute in a future update.

5. **Only `GCaMP` and `Isosbestic` signal types are supported.** If the
   photometry data contains other signal types the conversion raises
   `NotImplementedError`. See
   [Adding new signal types](#how-to-modify-fiberphotometryinterface).

---

## How to modify FiberPhotometryInterface

`FiberPhotometryInterface` (in
`datainterfaces/_fiber_photometry_interfaces.py`) is the central interface for
fiber photometry signals. Below are the most common extension scenarios.

### Updating hardware metadata in `fiber_photometry.yaml`

All device specifications are read from
`_metadata/fiber_photometry.yaml`. To update hardware values:

1. Open `_metadata/fiber_photometry.yaml`.
2. Find the section you want to update (e.g. `OpticalFiberModels`,
   `ExcitationSourceModels`, `PhotodetectorModels`, etc.).
3. Replace the `<placeholder>` or `0.0` values and remove the `# TODO` comment.
4. No code changes are needed — `add_fiberphotometry_table()` reads the file
   dynamically.

Example: setting the optical fiber numerical aperture:

```yaml
# Before
OpticalFiberModels:
  - name: optical_fiber_model
    numerical_aperture: 0.0  # TODO add numerical aperture

# After
OpticalFiberModels:
  - name: optical_fiber_model
    numerical_aperture: 0.37
```

### Adding fiber insertion coordinates per session

`FiberPhotometryInterface._update_fiber_photometry_metadata()` creates one
`OpticalFiber` entry per brain area with zeroed placeholder insertion
coordinates. To supply real coordinates:

**Option A — hard-code a lookup table in the method:**

```python
# In _update_fiber_photometry_metadata(), replace the placeholder block:
AREA_COORDINATES = {
    "DMS": dict(ap=-0.5, ml=1.5, dv=-3.0, reference="bregma", hemisphere="right"),
    "NAc": dict(ap=1.2, ml=0.9, dv=-4.5, reference="bregma", hemisphere="right"),
}

for target_area in target_areas:
    coords = AREA_COORDINATES.get(target_area, {})
    fp_metadata["OpticalFibers"].append(
        {
            "name": f"optical_fiber_{target_area}",
            "description": f"Chronically implanted optic fiber in {target_area}.",
            "model": "optical_fiber_model",
            "serial_number": "<serial number>",
            "fiber_insertion": {
                "insertion_position_ap_in_mm": coords.get("ap", 0.0),
                "insertion_position_ml_in_mm": coords.get("ml", 0.0),
                "insertion_position_dv_in_mm": coords.get("dv", 0.0),
                "position_reference": coords.get("reference", "<reference point>"),
                "hemisphere": coords.get("hemisphere", "<hemisphere>"),
            },
        }
    )
```

**Option B — load from a per-session CSV/JSON:**

```python
import json

def _update_fiber_photometry_metadata(self, fiber_photometry_metadata):
    coordinates_path = Path(__file__).parent.parent / "_metadata" / "fiber_coordinates.json"
    with open(coordinates_path) as f:
        all_coords = json.load(f)   # {eid: {area: {ap, ml, dv, ...}}}
    session_coords = all_coords.get(self.session, {})
    # ... use session_coords when building OpticalFibers entries
```

### Supporting a new signal type

The method currently maps `"GCaMP"` → 470 nm and `"Isosbestic"` → 415 nm.
To support a third signal type (e.g. `"rCaMP"` at 561 nm):

1. Add the new excitation source model and device to `fiber_photometry.yaml`.
2. Add a new `FiberPhotometryResponseSeries` entry (e.g. `rcamp_signal`) to
   `fiber_photometry.yaml`.
3. Extend the mapping in `_update_fiber_photometry_metadata()`:

```python
signal_type_to_excitation_nm = {
    "GCaMP": 470.0,
    "Isosbestic": 415.0,
    "rCaMP": 561.0,   # new entry
}
```

1. Update `series_name_to_signal_type`:

```python
series_name_to_signal_type = {
    "gcamp_signal": "GCaMP",
    "isosbestic_signal": "Isosbestic",
    "rcamp_signal": "rCaMP",   # new entry
}
```

1. Remove the `NotImplementedError` guard or extend `supported_signal_types`.

### Changing which files are required

`get_data_requirements()` declares the exact files that must exist for the
interface to be considered available. To add an alternative file format:

```python
@classmethod
def get_data_requirements(cls) -> dict:
    return {
        "exact_files_options": {
            "standard": [
                "photometry/photometry.signal.pqt",
                "photometry/photometryROI.locations.pqt",
            ],
            "legacy": [            # add alternative format
                "alf/photometry/photometry.signal.pqt",
                "alf/photometry/photometryROI.locations.pqt",
            ],
        },
    }
```

`check_availability()` returns `available=True` as soon as any one complete
option is found.

---

## How to modify OpticalFibersAnatomicalLocalizationInterface

`OpticalFibersAnatomicalLocalizationInterface` (in
`datainterfaces/_optical_fibers_anatomical_localization_interface.py`) is a
**placeholder interface** that creates the anatomical coordinate tables
structure in the NWB file, pre-populated with `NaN` values.

### Current state

The interface:

1. Reads the `OpticalFiber` devices that `FiberPhotometryInterface` already
   added to `nwbfile.devices`.
2. Creates a `Localization` lab metadata container with two coordinate spaces:
   - `IBLBregma` — bregma origin, µm units, RAS orientation.
   - `AllenCCFv3` — Allen Mouse Brain Atlas CCF v3.
3. Creates two `AnatomicalCoordinatesTable` objects:
   - `AnatomicalCoordinatesIBLBregmaOpticalFibers`
   - `AnatomicalCoordinatesCCFv3OpticalFibers`
4. Adds one row per unique `OpticalFiber` with `x=y=z=NaN` and
   `brain_region="TODO"`.

The `localized_entity` column in each table row references the **first**
`FiberPhotometryTable` row index for that fiber. This is correct because
multiple table rows (e.g. GCaMP and isosbestic channels) share the same
physical fiber.

### Supplying real fiber tip coordinates

Once the IBL histology pipeline provides fiber tip coordinates, modify
`add_to_nwbfile()` in the following section:

```python
# --- 8. Populate tables: one row per unique OpticalFiber ---
placeholder_coord = float("nan")  # TODO: replace with actual fiber tip coordinates
placeholder_region = "TODO"       # TODO: replace with actual brain region acronym

for fiber_name, first_row_index in fiber_name_to_first_row_index.items():
    # TODO: load actual x, y, z coordinates and brain region for fiber_name
    ibl_table.add_row(...)
    ccf_table.add_row(...)
```

Replace the `# TODO` block with actual coordinate loading. For example, using
a lookup dict:

```python
FIBER_COORDINATES_IBL = {
    "optical_fiber_DMS": dict(x=1500.0, y=-500.0, z=-3000.0, region="DMS"),
    "optical_fiber_NAc": dict(x=900.0,  y=1200.0, z=-4500.0, region="ACB"),
}
FIBER_COORDINATES_CCF = {
    "optical_fiber_DMS": dict(x=4800.0, y=3200.0, z=2400.0, region="DMS"),
    "optical_fiber_NAc": dict(x=5200.0, y=4100.0, z=1100.0, region="ACB"),
}

for fiber_name, first_row_index in fiber_name_to_first_row_index.items():
    ibl_coords = FIBER_COORDINATES_IBL.get(fiber_name, {})
    ccf_coords = FIBER_COORDINATES_CCF.get(fiber_name, {})

    ibl_table.add_row(
        localized_entity=first_row_index,
        x=ibl_coords.get("x", float("nan")),
        y=ibl_coords.get("y", float("nan")),
        z=ibl_coords.get("z", float("nan")),
        brain_region=ibl_coords.get("region", "TODO"),
    )
    ccf_table.add_row(
        localized_entity=first_row_index,
        x=ccf_coords.get("x", float("nan")),
        y=ccf_coords.get("y", float("nan")),
        z=ccf_coords.get("z", float("nan")),
        brain_region=ccf_coords.get("region", "TODO"),
    )
```

Alternatively, load coordinates at session-load time in `__init__()` by
querying the ONE API or reading a local file, and store the result in `self`:

```python
def __init__(self, one: ONE, session: str):
    self.one = one
    self.session = session
    self.revision = self.REVISION
    # Load coordinates now so add_to_nwbfile() can use them
    self.fiber_coordinates = self._load_fiber_coordinates()

def _load_fiber_coordinates(self) -> dict:
    """Load fiber tip coordinates from IBL data store or local file."""
    # e.g. self.one.load_object(...) or read from a local JSON/CSV
    ...
```

### Implementing `get_data_requirements()` for real data

When source data files become available (e.g. from the IBL histology
pipeline), update `get_data_requirements()` and `get_load_object_kwargs()`:

```python
@classmethod
def get_data_requirements(cls) -> dict:
    return {
        "exact_files_options": {
            "standard": [
                "histology/electrode.trajectory.json",
                "histology/fiber.tipCoordinates.json",
            ]
        },
    }

@classmethod
def get_load_object_kwargs(cls) -> dict:
    return {"obj": "fiber", "collection": "histology"}
```

---

## Wheel interfaces and task collections

Fiber photometry sessions can contain multiple tasks per session
(e.g. `task_00`, `task_01`). The three wheel interfaces
(`FiberPhotometryWheelPositionInterface`,
`FiberPhotometryWheelKinematicsInterface`,
`FiberPhotometryWheelMovementsInterface`) all accept a `task` parameter.

In `convert_session.py`, all available tasks are discovered via
`get_available_tasks()` and each wheel interface is instantiated per task:

```python
available_tasks = get_available_tasks(one=one, session=eid)
for task in available_tasks:
    if FiberPhotometryWheelPositionInterface.check_availability(one, eid, task=task)["available"]:
        data_interfaces[f"{task.replace('task_', 'Task')}WheelPosition"] = \
            FiberPhotometryWheelPositionInterface(one=one, session=eid, task=task)
```

Wheel data files are looked up first in the task-specific collection
(e.g. `alf/task_00/`) and fall back to the standard `alf/` collection if not
found there.

---

## Availability checking pattern

All interfaces implement `check_availability()` following this pattern:

```text
1. Run quality check (check_quality) — if it explicitly rejects, return early.
2. List datasets without revision filtering (one.list_datasets(eid)).
3. For each option in exact_files_options:
   - If ALL files in the option are present → mark available, stop.
4. If no complete option found → list first option files as missing.
5. Return result dict merged with any extra fields from the quality check.
```

Key properties of this design:

- **Never downloads data** — only queries the dataset index.
- **Revision-agnostic** — queries the superset of all revisions so that
  both revision-tagged (e.g. spike sorting) and untagged (e.g. behavioral)
  files are found.
- **Multiple format support** — any complete `exact_files_options` option
  satisfies availability.
- **Transparent failures** — no `try/except` wrappers; exceptions propagate.

---

## Converter and metadata pipeline

Metadata is assembled in layers and deep-merged:

```text
BaseDataInterface.get_metadata()   (per interface)
        ↓
ConverterPipe.get_metadata()       (aggregates all interfaces)
        ↓
IblConverter.get_metadata()        (adds session/lab/subject from ONE API)
        ↓
FiberPhotometryNWBConverter.get_metadata()   (merges general_metadata.yaml)
        ↓
session_to_nwb()                   (merges general_metadata.yaml again as override)
```

`FiberPhotometryInterface.get_metadata()` additionally merges
`fiber_photometry.yaml` after calling
`_update_fiber_photometry_metadata()` to customise it for the session.

The `Subject` block uses `IblSubject` (from `ndx_ibl`) which extends the
standard NWB `Subject` type with IBL-specific fields. It is created
explicitly in `session_to_nwb()` and assigned to `nwbfile.subject` before
calling `run_conversion()`.
