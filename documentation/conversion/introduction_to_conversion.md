# NWB Conversion

This section documents how to convert IBL fiber photometry data to NWB format.

## Architecture

IBL-fiberphotometry-to-NWB uses [NeuroConv](https://neuroconv.readthedocs.io/), a flexible data conversion framework. The system is organized around **Interfaces** (data readers) and **Converters** (orchestrators):

```
IBL Data (ONE API)
    |
  [Interface 1]  [Interface 2]  [Interface 3]  ...
    |             |             |
  [FiberPhotometryNWBConverter] <-- orchestrates all interfaces
    |
  NWB File (Standardized Output)
```

- **Interfaces** (`src/ibl_fiberphotometry_to_nwb/fiber_photometry/datainterfaces/`) — Specialized readers for individual data modalities (fiber photometry signals, wheel, anatomical localization)
- **Converters** (`src/ibl_fiberphotometry_to_nwb/fiber_photometry/nwbconverter.py`) — Orchestrate multiple interfaces to create complete NWB files
- **Shared interfaces** (from `ibl_to_nwb`) — Trials, session epochs, pose estimation, pupil tracking, licks, video, and motion energy

## Conversion Pipeline

```
session_to_nwb(eid)
|
+-- FiberPhotometryInterface              (custom: fiber photometry signals)
+-- OpticalFibersAnatomicalLocalizationInterface  (custom: fiber tip coordinates)
+-- BrainwideMapTrialsInterface           (from ibl_to_nwb)
+-- FiberPhotometryWheelPositionInterface  (custom: task-aware wheel)
+-- FiberPhotometryWheelKinematicsInterface
+-- FiberPhotometryWheelMovementsInterface
+-- SessionEpochsInterface                (from ibl_to_nwb)
+-- PassiveIntervalsInterface             (from ibl_to_nwb)
+-- PassiveReplayStimInterface            (from ibl_to_nwb)
+-- LickInterface                         (from ibl_to_nwb)
+-- IblPoseEstimationInterface x 3        (left/right/body cameras, from ibl_to_nwb)
+-- PupilTrackingInterface x 2            (left/right cameras, from ibl_to_nwb)
+-- RoiMotionEnergyInterface x 3          (from ibl_to_nwb)
+-- RawVideoInterface x 3                 (from ibl_to_nwb)
        |
        v
FiberPhotometryNWBConverter
        |
        v
NWBFile (written to disk)
```

Each interface:

1. Declares required files via `get_data_requirements()`.
2. Reports availability via `check_availability()` (no downloads).
3. Adds data to the NWB file via `add_to_nwbfile()`.
4. Optionally contributes metadata via `get_metadata()`.

**Order matters**: `FiberPhotometryInterface` must run before `OpticalFibersAnatomicalLocalizationInterface` because it creates the `OpticalFiber` devices and the `FiberPhotometryTable` that the localization interface depends on.

## Custom vs Inherited Interfaces

This project defines three custom interfaces that extend the base IBL-to-NWB pipeline:

| Interface | Purpose |
|-----------|---------|
| `FiberPhotometryInterface` | Loads GCaMP and isosbestic signals via `PhotometrySessionLoader`, creates all hardware devices and `FiberPhotometryTable`, writes `FiberPhotometryResponseSeries` |
| `OpticalFibersAnatomicalLocalizationInterface` | Placeholder for fiber tip coordinates in IBL-Bregma and Allen CCFv3 spaces (currently NaN) |
| `FiberPhotometryWheel*Interface` (x3) | Extends standard IBL wheel interfaces with task-specific ALF collection support (`alf/task_00/`, `alf/task_01/`, etc.) |

All other interfaces (trials, licks, pose, pupil, video, motion energy, session epochs, passive stimuli) are reused directly from [IBL-to-NWB](https://github.com/h-mayorquin/IBL-to-nwb/tree/heberto_conversion).

## Metadata Pipeline

Metadata is assembled in layers and deep-merged:

```
BaseDataInterface.get_metadata()          (per interface)
        |
ConverterPipe.get_metadata()              (aggregates all interfaces)
        |
IblConverter.get_metadata()               (adds session/lab/subject from ONE API)
        |
FiberPhotometryNWBConverter.get_metadata() (merges general_metadata.yaml)
        |
session_to_nwb()                          (merges general_metadata.yaml as override)
```

`FiberPhotometryInterface.get_metadata()` additionally loads `fiber_photometry.yaml` and calls `_update_fiber_photometry_metadata()` to customize hardware metadata for each session (one `OpticalFiber` per brain area, correct `FiberPhotometryTable` rows, etc.).

The `Subject` block uses `IblSubject` (from `ndx_ibl`) which extends the standard NWB `Subject` type with IBL-specific fields. It is created explicitly in `session_to_nwb()` and assigned to `nwbfile.subject` before calling `run_conversion()`.

## Documents in This Section

- [conversion_overview.md](conversion_overview.md) — How to run conversions: scripts, Python API, pipeline stages
- [data_interface_design.md](data_interface_design.md) — Interface contract specification for writing new interfaces
- [fiber_photometry_metadata_guide.md](fiber_photometry_metadata_guide.md) — Step-by-step guide for completing fiber photometry hardware metadata

## Related Sections

- [ONE API Data Access](../one_api_data_access/) — How data is loaded from the IBL data store
- [Development](../development/) — Environment setup and dependency management
- [conversion_notes.md](../../src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md) — Design decisions and known limitations
