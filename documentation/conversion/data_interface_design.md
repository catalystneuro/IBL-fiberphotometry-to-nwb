# Data Interface Design

This document specifies the interface contract used in the IBL fiber photometry to NWB conversion pipeline, based on the `BaseIBLDataInterface` pattern from [IBL-to-NWB](https://github.com/h-mayorquin/IBL-to-nwb/tree/heberto_conversion).

## Design Philosophy

Each interface follows a **single source of truth** principle: it declares exactly what data it needs via `get_data_requirements()`, and both availability checking and data loading use this declaration. This ensures:

- **Explicit contracts** — no hidden data dependencies
- **Fail-fast behavior** — missing data is detected early
- **Testability** — requirements can be validated without running full conversions

## The Three-Method Contract

Every interface inherits from `BaseIBLDataInterface` and implements three core methods:

```
get_data_requirements()  -- Declares exact files needed (source of truth)
        |
check_availability()     -- Calls check_quality() first (QC hook),
        |                   then reads requirements, queries ONE.
        |                   Returns: available, alternative_used.
        |                   NO downloads, read-only check.
        |
add_to_nwbfile()         -- Loads data from cache (same files),
                            writes to NWB file.
```

### Method Signatures

```python
class BaseIBLDataInterface:
    REVISION: str | None = None  # Class-level revision for reproducibility

    @classmethod
    def get_data_requirements(cls, **kwargs) -> dict:
        """Single source of truth for what data is needed."""
        ...

    @classmethod
    def check_availability(cls, one: ONE, eid: str, **kwargs) -> dict:
        """Read-only check without downloading."""
        ...

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, **kwargs) -> None:
        """Load cached data and write to NWB."""
        ...
```

## Data Requirements Format

`get_data_requirements()` returns a dictionary with `exact_files_options`:

```python
@classmethod
def get_data_requirements(cls) -> dict:
    return {
        "exact_files_options": {
            "standard": [
                "photometry/photometry.signal.pqt",
                "photometry/photometryROI.locations.pqt",
            ]
        },
    }
```

### Multiple Format Alternatives

When data can exist in different file structures, list multiple options. The system tries each in order until finding one where ALL files exist:

```python
"exact_files_options": {
    "standard": [
        "alf/_ibl_wheel.position.npy",
        "alf/_ibl_wheel.timestamps.npy",
    ],
    "task_00": [
        "alf/task_00/_ibl_wheel.position.npy",
        "alf/task_00/_ibl_wheel.timestamps.npy",
    ],
}
```

## How `check_availability()` Works

1. Calls `check_quality()` first (QC hook — returns early if rejected)
2. Calls `get_data_requirements()` to get `exact_files_options`
3. Queries ONE API for available datasets (no download)
4. Tries each option until finding one where ALL files exist
5. Returns availability status and which option was found

**Return format:**

```python
{
    "available": bool,              # True if any complete option found
    "missing_required": [str],      # Files not found (if unavailable)
    "found_files": [str],           # Files that were found
    "alternative_used": str,        # Option name that matched
    "requirements": dict,           # The full requirements dict
}
```

**Key behaviors:**

- **Never downloads data** — only queries the dataset index
- **Revision-agnostic** — queries the superset of all revisions
- **Multiple format support** — any complete option satisfies availability

## Interfaces in This Project

### FiberPhotometryInterface

The central interface for fiber photometry signals. Loads GCaMP and isosbestic data via `PhotometrySessionLoader`.

**Required files:**
```
photometry/photometry.signal.pqt
photometry/photometryROI.locations.pqt
```

**NWB output:**
- Creates all hardware device models and devices (optical fibers, excitation sources, photodetectors, filters, dichroic mirrors)
- Creates `FiberPhotometryTable` with one row per (brain area, signal type) combination
- Writes `FiberPhotometryResponseSeries` objects (GCaMP and isosbestic) with shape `(n_frames, n_brain_areas)`

**Session customization:**
`_update_fiber_photometry_metadata()` adapts the base `fiber_photometry.yaml` template for each session by:
1. Creating one `OpticalFiber` per unique brain area
2. Building `FiberPhotometryTable` rows: all GCaMP rows first, then all isosbestic rows
3. Setting `fiber_photometry_table_region` indices in each `FiberPhotometryResponseSeries`

### OpticalFibersAnatomicalLocalizationInterface

Placeholder interface that creates anatomical coordinate table structures. Currently populates coordinates with `NaN` values.

**Dependencies:** Must run after `FiberPhotometryInterface` (needs `OpticalFiber` devices and `FiberPhotometryTable`).

**Creates:**
- `Localization` container with two coordinate spaces (IBL-Bregma, Allen CCFv3)
- `AnatomicalCoordinatesIBLBregmaOpticalFibers` table
- `AnatomicalCoordinatesCCFv3OpticalFibers` table
- One row per unique `OpticalFiber` in each table

### FiberPhotometryWheel*Interface (x3)

Extends the standard IBL wheel interfaces with task-specific ALF collection support. Fiber photometry sessions can have multiple tasks per session (e.g. `task_00`, `task_01`), and wheel data lives in task-specific directories.

**Parameterized:** Each interface takes a `task` parameter that determines the ALF collection path.

**Fallback:** Checks both `alf/{task}/` (task-specific) and `alf/` (standard) locations.

## Adding a New Interface

1. Subclass `BaseIBLDataInterface`
2. Implement `get_data_requirements()` with exact file paths
3. Implement `check_availability()` (or use the base class default)
4. Implement `add_to_nwbfile()` to load data and write to NWB
5. Register the interface in `convert_session.py`

See [conversion_notes.md](../../src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md) for detailed extension examples.

## Related Documents

- [introduction_to_conversion.md](introduction_to_conversion.md) — Architecture overview
- [fiber_photometry_metadata_guide.md](fiber_photometry_metadata_guide.md) — Completing hardware metadata
- [IBL-to-NWB interface design](https://github.com/h-mayorquin/IBL-to-nwb/blob/heberto_conversion/documentation/conversion/ibl_data_interface_design.md) — Full specification from the parent project
