# IBL Fiber Photometry → NWB: Usage Guide

This guide explains how to install, configure, and run the IBL fiber photometry
NWB conversion pipeline, both for single sessions and for entire datasets.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick start — single session](#quick-start--single-session)
3. [Batch conversion — multiple sessions](#batch-conversion--multiple-sessions)
4. [Stub (test) mode](#stub-test-mode)
5. [Output file structure](#output-file-structure)
6. [What gets converted](#what-gets-converted)
7. [Metadata files](#metadata-files)
8. [Customising the conversion](#customising-the-conversion)
9. [Checking data availability before conversion](#checking-data-availability-before-conversion)
10. [Troubleshooting](#troubleshooting)

---

## Installation

### Using conda (recommended)

```bash
git clone https://github.com/catalystneuro/IBL-fiberphotometry-to-nwb.git
cd IBL-fiberphotometry-to-nwb
conda env create --file make_env.yml
conda activate ibl-fp-to-nwb
pip install --editable ".[fiber_photometry]"
```

### Using pip only

```bash
git clone https://github.com/catalystneuro/IBL-fiberphotometry-to-nwb.git
cd IBL-fiberphotometry-to-nwb
pip install --editable ".[fiber_photometry]"
```

### From PyPI

```bash
pip install IBL-fiberphotometry-to-nwb
```

---

## Quick start — single session

```python
from pathlib import Path
from one.api import ONE
from ibl_fiberphotometry_to_nwb.fiber_photometry.convert_session import session_to_nwb

# Connect to the IBL data server
one = ONE()  # uses default Alyx URL; pass base_url= to override

# Session experiment ID (UUID)
eid = "fd688232-0dd8-400b-aa66-dc23460d9f98"

result = session_to_nwb(
    eid=eid,
    one=one,
    output_path=Path("E:/IBL-fiberphotometry-nwbfiles"),
    stub_test=False,   # set True for a quick test (see below)
    verbose=True,
)

print(f"NWB file written to: {result['nwbfile_path']}")
print(f"File size:           {result['nwb_size_gb']:.2f} GB")
print(f"Write time:          {result['write_time']:.1f} s")
```

You can also run the script directly:

```bash
python src/ibl_fiberphotometry_to_nwb/fiber_photometry/convert_session.py
```

Edit the `eid`, `output_path`, and `stub_test` variables at the bottom of
`convert_session.py` before running.

---

## Batch conversion — multiple sessions

```python
from pathlib import Path
from ibl_fiberphotometry_to_nwb.fiber_photometry.convert_all_sessions import dataset_to_nwb

eids = [
    "fd688232-0dd8-400b-aa66-dc23460d9f98",
    "another-session-uuid-here",
]

dataset_to_nwb(
    eids=eids,
    output_dir_path=Path("E:/IBL-fiberphotometry-nwbfiles"),
    stub_test=False,
    max_workers=4,   # number of parallel worker processes
    verbose=True,
)
```

If a session fails, the full traceback is saved to
`output_dir_path/ERROR_{eid}_{mode}.txt` and the remaining sessions continue.

---

## Stub (test) mode

Pass `stub_test=True` to run a fast, lightweight conversion without downloading
large video files:

```python
result = session_to_nwb(
    eid=eid,
    one=one,
    output_path=Path("/tmp/nwb_test"),
    stub_test=True,
)
```

In stub mode:
- Fiber photometry data is truncated to the first **1 000 frames**.
- Trial tables are truncated to **10 trials**.
- Video files are included only if they are already present in the local ONE
  cache (no downloads are triggered).
- Output goes to `output_path/stub/sub-{subject}/` instead of `full/`.

---

## Output file structure

```
output_path/
├── full/
│   └── sub-{subject_id}/
│       └── sub-{subject_id}_ses-{eid}_behavior+ophys.nwb
└── stub/
    └── sub-{subject_id}/
        └── sub-{subject_id}_ses-{eid}_behavior+ophys.nwb
```

Subject IDs are sanitised for DANDI compliance (underscores replaced with
hyphens).

---

## What gets converted

Each NWB file can contain the following data, depending on availability for
the session:

| Modality | NWB location | Source files |
|---|---|---|
| GCaMP fluorescence signal | `acquisition/gcamp_signal` | `photometry/photometry.signal.pqt` |
| Isosbestic control signal | `acquisition/isosbestic_signal` | `photometry/photometry.signal.pqt` |
| Optical fiber metadata | `lab_meta_data/fiber_photometry` | derived from above |
| Fiber tip coordinates | `lab_meta_data/localization` | placeholder (NaN) until data available |
| Wheel position | `processing/behavior/WheelPosition` | `alf/{task}/_ibl_wheel.*` |
| Wheel kinematics | `processing/behavior/WheelKinematics` | derived from wheel position |
| Wheel movements | `processing/behavior/WheelMovements` | `alf/{task}/_ibl_wheelMoves.*` |
| Behavioral trials | `intervals/trials` | `alf/_ibl_trials.*` |
| Session epochs | `intervals/epochs` | `alf/task.*` |
| Passive intervals | `intervals/passive_*` | `alf/passiveGabor.*` |
| Passive replay stimuli | `intervals/passiveReplay*` | `alf/passiveStims.*` |
| Lick times | `processing/behavior/Licks` | `alf/licks.*` |
| Pose estimation (left/right/body camera) | `processing/behavior/PoseEstimation*` | Lightning Pose → DLC fallback |
| Pupil tracking (left/right camera) | `processing/behavior/PupilTracking*` | `alf/*Camera.features.*` |
| ROI motion energy | `processing/behavior/MotionEnergy*` | `alf/*Camera.ROIMotionEnergy.*` |
| Raw behavioral video | external `.mp4` files linked in NWB | `raw_video_data/_iblrig_*Camera.raw.mp4` |

---

## Metadata files

Two YAML files control experiment-level metadata. Edit these before running
the conversion:

### `_metadata/general_metadata.yaml`

Defines NWB-level keywords and the experiment description common to all
sessions in this dataset.

```yaml
NWBFile:
  keywords: [International Brain Laboratory, Fiber photometry, ...]
  experiment_description: |
    ...
```

### `_metadata/fiber_photometry.yaml`

Defines all hardware components of the fiber photometry rig. Most fields
contain `# TODO` comments indicating values that need to be filled in:

- Optical fiber model (manufacturer, numerical aperture, core diameter, etc.)
- Excitation source models (LED wavelength ranges, manufacturer)
- Photodetector model (type, wavelength range, gain)
- Optical filter models (bandpass centre and bandwidth)
- Dichroic mirror model
- GCaMP indicator metadata (manufacturer)
- Template rows for the `FiberPhotometryTable`

The `FiberPhotometryInterface._update_fiber_photometry_metadata()` method
reads this file and automatically customises it for each session (see
[Customising the conversion](#customising-the-conversion) below).

---

## Customising the conversion

### Adding new brain areas

Brain areas are read automatically from the photometry data columns. No
manual configuration is needed — one `OpticalFiber` device and the
corresponding `FiberPhotometryTable` rows are created per area.

### Adding fiber insertion coordinates

The `_update_fiber_photometry_metadata()` method in `FiberPhotometryInterface`
creates placeholder `fiber_insertion` objects with zeroed coordinates. To add
real stereotaxic coordinates, either:

1. **Hard-code them per session** — override `_update_fiber_photometry_metadata()`
   in a subclass and look up coordinates from a dictionary keyed by session
   ID or brain area.
2. **Load from a file** — read a CSV / JSON containing
   `{eid: {area: {AP, ML, DV}}}` and populate the fields programmatically.

### Adding new signal types

Currently only `GCaMP` (470 nm excitation) and `Isosbestic` (415 nm
excitation) are supported. To add a new signal type (e.g. a red indicator):

1. Add a new `ExcitationSourceModel` and `ExcitationSource` entry in
   `fiber_photometry.yaml`.
2. Add a new `FiberPhotometryResponseSeries` entry in `fiber_photometry.yaml`.
3. Extend `signal_type_to_excitation_nm` in
   `FiberPhotometryInterface._update_fiber_photometry_metadata()`.

### Providing real fiber tip coordinates

See the dedicated section in `conversion_notes.md` —
[Modifying OpticalFibersAnatomicalLocalizationInterface](conversion_notes.md).

---

## Checking data availability before conversion

To check whether a session has all the required files without downloading
anything:

```python
from one.api import ONE
from ibl_fiberphotometry_to_nwb.fiber_photometry.datainterfaces import (
    FiberPhotometryInterface,
    OpticalFibersAnatomicalLocalizationInterface,
    FiberPhotometryWheelPositionInterface,
)

one = ONE()
eid = "fd688232-0dd8-400b-aa66-dc23460d9f98"

# Check fiber photometry data
fp_result = FiberPhotometryInterface.check_availability(one, eid)
print(f"FiberPhotometry available: {fp_result['available']}")
if not fp_result['available']:
    print(f"  Missing: {fp_result['missing_required']}")

# Check wheel data for a specific task
wheel_result = FiberPhotometryWheelPositionInterface.check_availability(
    one, eid, task="task_00"
)
print(f"Wheel (task_00) available: {wheel_result['available']}")
```

The `check_availability()` method:
- Never downloads data (read-only, fast).
- Returns `{"available": bool, "missing_required": [...], "found_files": [...], ...}`.
- Supports multiple file format options (`exact_files_options`); any complete
  option marks the interface as available.

---

## Troubleshooting

### `ValueError: No OpticalFiber devices found`
`OpticalFibersAnatomicalLocalizationInterface.add_to_nwbfile()` requires that
`FiberPhotometryInterface` runs first (it adds the `OpticalFiber` devices).
Make sure `FiberPhotometry` comes before `OpticalFibersAnatomicalLocalizationInterface`
in `data_interfaces`.

### `AssertionError: Device model ... not found`
The `OpticalFiber` in `fiber_photometry.yaml` references a model name that
does not match any `OpticalFiberModel` name in the same file. Check that the
`model:` field in `OpticalFibers` matches the `name:` field of one of the
`OpticalFiberModels` entries.

### `NotImplementedError: Signal types {...} are not supported`
The photometry data contains a signal type other than `GCaMP` or `Isosbestic`.
See [Adding new signal types](#adding-new-signal-types) above.

### Session fails in batch mode
Check the `ERROR_{eid}_{mode}.txt` file in the output directory for the full
traceback and the kwargs that were used for that session.

### Stub mode still downloads large files
Video files are downloaded only if they are already in the local ONE cache.
If the cache path cannot be resolved (`one.eid2path(eid)` returns `None`),
the video interface is skipped. Make sure the session has been at least
partially downloaded before running in stub mode if you want videos included.
