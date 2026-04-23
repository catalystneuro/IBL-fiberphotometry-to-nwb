# Conversion Overview

This document explains how to run IBL fiber photometry to NWB conversions: single sessions, batch conversions, and the pipeline stages involved.

## Prerequisites

1. **Environment**: Install the package following the [README installation instructions](../../README.md#installation).
2. **ONE API credentials**: You need access to the IBL Alyx server. On first use, `ONE()` will prompt you for credentials.

## Convert a Single Session

### Python API

```python
from pathlib import Path
from one.api import ONE
from ibl_fiberphotometry_to_nwb.fiber_photometry.convert_session import session_to_nwb

one = ONE()  # uses default Alyx URL; pass base_url= to override

result = session_to_nwb(
    eid="fd688232-0dd8-400b-aa66-dc23460d9f98",
    one=one,
    output_path=Path("E:/IBL-fiberphotometry-nwbfiles"),
    stub_test=False,   # True for quick test
    verbose=True,
)

print(f"NWB written to: {result['nwbfile_path']}")
print(f"File size:       {result['nwb_size_gb']:.2f} GB")
print(f"Write time:      {result['write_time']:.1f} s")
```

### Command Line

```bash
python src/ibl_fiberphotometry_to_nwb/fiber_photometry/convert_session.py
```

Edit the `eid`, `output_path`, and `stub_test` variables at the bottom of `convert_session.py` before running.

## Convert Multiple Sessions (Batch)

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
    max_workers=4,   # parallel worker processes
    verbose=True,
)
```

If a session fails, the full traceback is saved to `output_dir_path/ERROR_{eid}_{mode}.txt` and the remaining sessions continue.

## Stub (Test) Mode

Pass `stub_test=True` for a fast, lightweight conversion:

- Fiber photometry data truncated to the first **1,000 frames**
- Trial tables truncated to **10 trials**
- Video files included only if already in the local ONE cache (no downloads triggered)
- Output goes to `output_path/stub/sub-{subject}/` instead of `full/`

## Pipeline Stages

`session_to_nwb()` executes the following stages:

### Stage 1: Interface Discovery

For each data modality, the script calls `check_availability()` to determine what data exists for the session without downloading anything. Only interfaces with available data are included.

- `FiberPhotometryInterface` and `OpticalFibersAnatomicalLocalizationInterface` are always included (core data)
- `BrainwideMapTrialsInterface` is always included
- Wheel interfaces are discovered per task (e.g. `task_00`, `task_01`) via `get_available_tasks()`
- Camera interfaces are checked per camera view (`left`, `right`, `body`)
- Session epochs, passive stimuli, and licks are included if available

### Stage 2: Converter Creation

All discovered interfaces are passed to `FiberPhotometryNWBConverter`, which orchestrates the conversion.

### Stage 3: Metadata Assembly

Metadata is merged from multiple sources:
1. Each interface contributes its own metadata via `get_metadata()`
2. `IblConverter` adds session, lab, and subject information from the ONE API
3. `FiberPhotometryNWBConverter` merges `general_metadata.yaml`
4. `session_to_nwb()` applies `general_metadata.yaml` as a final override
5. `IblSubject` (from `ndx_ibl`) is created with IBL-specific subject fields

### Stage 4: NWB Write

The converter calls `add_to_nwbfile()` on each interface in order, then writes the complete NWB file to disk.

## Output File Structure

```
output_path/
+-- full/
|   +-- sub-{subject_id}/
|       +-- sub-{subject_id}_ses-{eid}_behavior+ophys.nwb
+-- stub/
    +-- sub-{subject_id}/
        +-- sub-{subject_id}_ses-{eid}_behavior+ophys.nwb
```

Subject IDs are sanitized for DANDI compliance (underscores replaced with hyphens).

## Data Modalities and NWB Mapping

| Interface | NWB Container | NWB Type |
|-----------|---------------|----------|
| `FiberPhotometryInterface` | `acquisition/gcamp_signal`, `acquisition/isosbestic_signal` | `FiberPhotometryResponseSeries` |
| `FiberPhotometryInterface` | `lab_meta_data/fiber_photometry` | `FiberPhotometry` (table + devices) |
| `OpticalFibersAnatomicalLocalizationInterface` | `lab_meta_data/localization` | `Localization` with `AnatomicalCoordinatesTable` |
| Wheel interfaces | `processing/behavior/Wheel*` | `TimeSeries`, `IntervalSeries` |
| `BrainwideMapTrialsInterface` | `intervals/trials` | `TimeIntervals` |
| `SessionEpochsInterface` | `intervals/epochs` | `TimeIntervals` |
| Camera interfaces | `processing/behavior/PoseEstimation*`, `PupilTracking*`, `MotionEnergy*` | Various |
| `RawVideoInterface` | External `.mp4` files linked in NWB | `ImageSeries` |

## Checking Data Availability Before Conversion

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
See [fiber_photometry_metadata_guide.md](fiber_photometry_metadata_guide.md#supporting-a-new-signal-type).

### Session fails in batch mode

Check the `ERROR_{eid}_{mode}.txt` file in the output directory for the full
traceback and the kwargs that were used for that session.

### Stub mode still downloads large files

Video files are downloaded only if they are already in the local ONE cache.
If the cache path cannot be resolved (`one.eid2path(eid)` returns `None`),
the video interface is skipped. Make sure the session has been at least
partially downloaded before running in stub mode if you want videos included.

---

## Related Documents

- [fiber_photometry_metadata_guide.md](fiber_photometry_metadata_guide.md) — How to complete hardware metadata
- [data_interface_design.md](data_interface_design.md) — Interface contract specification
