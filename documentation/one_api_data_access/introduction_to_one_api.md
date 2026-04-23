# ONE API Data Access

This document explains how IBL fiber photometry data is accessed using the ONE API and related loaders.

## Overview

The [ONE API](https://int-brain-lab.github.io/ONE/) (Open Neurophysiology Environment) is the primary interface for accessing IBL experimental data stored on the Alyx server. All data loading in this pipeline goes through ONE.

## Initial Setup

```python
from one.api import ONE

# First time: prompts for Alyx credentials
one = ONE()

# Or specify the server explicitly
one = ONE(base_url="https://alyx.internationalbrainlab.org")
```

Credentials are cached locally after the first authentication.

## Loading Fiber Photometry Data

Fiber photometry signals are loaded via `PhotometrySessionLoader` from `ibllib`:

```python
from brainbox.io.one import PhotometrySessionLoader

loader = PhotometrySessionLoader(eid="fd688232-0dd8-400b-aa66-dc23460d9f98", one=one)
loader.load_photometry()

# Returns a dict of DataFrames keyed by signal type
photometry = loader.photometry
# photometry["GCaMP"]       -> DataFrame with columns: times, DMS, NAc, ...
# photometry["Isosbestic"]  -> DataFrame with columns: times, DMS, NAc, ...
```

The underlying files are:
- `photometry/photometry.signal.pqt` — Signal values (parquet format)
- `photometry/photometryROI.locations.pqt` — ROI brain area labels

## Task Collections

Fiber photometry sessions can contain multiple tasks per session. Data for each task is stored in a separate ALF collection directory:

```
alf/
+-- task_00/     # First task (e.g. biasedChoiceWorld)
|   +-- _ibl_wheel.position.npy
|   +-- _ibl_wheel.timestamps.npy
|   +-- _ibl_wheelMoves.intervals.npy
|   +-- _ibl_wheelMoves.peakAmplitude.npy
+-- task_01/     # Second task (e.g. passiveChoiceWorld)
|   +-- _ibl_wheel.position.npy
|   +-- ...
```

Discover available tasks:

```python
from ibl_fiberphotometry_to_nwb.fiber_photometry.utils import get_available_tasks

tasks = get_available_tasks(one=one, session="fd688232-0dd8-400b-aa66-dc23460d9f98")
# ['task_00']
```

Load task-specific data:

```python
wheel = one.load_object(
    id="fd688232-0dd8-400b-aa66-dc23460d9f98",
    obj="wheel",
    collection="alf/task_00",
)
```

## Listing Available Datasets

To check what data exists for a session without downloading:

```python
datasets = one.list_datasets(eid="fd688232-0dd8-400b-aa66-dc23460d9f98")
# Returns a list of all available file paths

# Filter by pattern
photometry_files = one.list_datasets(eid=eid, filename="photometry*")
```

This is what `check_availability()` uses internally — it never downloads data.

## Session and Subject Metadata

Session and subject metadata come from the Alyx REST API:

```python
# Session record
session_info = one.alyx.rest("sessions", "read", id=eid)
# Contains: subject, lab, start_time, task_protocol, etc.

# Lab record
lab_info = one.alyx.rest("labs", "list", name=session_info["lab"])
# Contains: institution, timezone, etc.

# Subject record (used by IblConverter.get_metadata())
subject_info = one.alyx.rest("subjects", "read", id=session_info["subject"])
# Contains: species, sex, date_of_birth, etc.
```

The `IblConverter` base class handles all of this automatically when building NWB metadata.

## Key Data Patterns

| Data Type | ONE Method | Collection |
|-----------|-----------|------------|
| Fiber photometry signals | `PhotometrySessionLoader` | `photometry/` |
| Wheel position | `one.load_object(obj="wheel")` | `alf/task_00/` |
| Wheel movements | `one.load_object(obj="wheelMoves")` | `alf/task_00/` |
| Trials | `one.load_object(obj="trials")` | `alf/` |
| Lick times | `one.load_dataset(dataset="licks.times")` | `alf/` |
| Pose estimation | `SessionLoader.load_pose()` | `alf/` |
| Camera timestamps | `one.load_dataset(...)` | `alf/` |
| Raw video | `one.load_dataset(...)` | `raw_video_data/` |

## Related Documents

- [IBL ONE API documentation](https://int-brain-lab.github.io/ONE/)
- [data_interface_design.md](../conversion/data_interface_design.md) — How interfaces use ONE for data access
- [conversion_overview.md](../conversion/conversion_overview.md) — How sessions are converted
