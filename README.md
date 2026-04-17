# IBL-fiberphotometry-to-nwb

NWB conversion scripts for IBL fiber photometry data to the
[Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.

**See [documentation/introduction_to_documentation.md](documentation/introduction_to_documentation.md) for complete documentation including system architecture, concepts, and how-tos.**

---

## Installation

### From PyPI

```bash
pip install IBL-fiberphotometry-to-nwb
```

### From GitHub with conda (recommended)

```bash
git clone https://github.com/catalystneuro/IBL-fiberphotometry-to-nwb
cd IBL-fiberphotometry-to-nwb
conda env create --file make_env.yml
conda activate ibl-fp-to-nwb
pip install --editable .
```

### From GitHub with pip only

```bash
git clone https://github.com/catalystneuro/IBL-fiberphotometry-to-nwb
cd IBL-fiberphotometry-to-nwb
pip install --editable .
```

Both GitHub options install the package in
[editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs),
so you can modify the source code and have the changes take effect immediately.

---

## Quick start

```python
from pathlib import Path
from one.api import ONE
from ibl_fiberphotometry_to_nwb.fiber_photometry.convert_session import session_to_nwb

one = ONE()
result = session_to_nwb(
    eid="fd688232-0dd8-400b-aa66-dc23460d9f98",
    one=one,
    output_path=Path("E:/IBL-fiberphotometry-nwbfiles"),
    stub_test=False,
    verbose=True,
)
print(f"NWB written to: {result['nwbfile_path']}")
```

Or run the conversion script directly:

```bash
python src/ibl_fiberphotometry_to_nwb/fiber_photometry/convert_session.py
```

For detailed usage including batch conversion, stub mode, and customisation,
see [conversion_overview.md](documentation/conversion/conversion_overview.md).

---

## What gets converted

Each NWB file contains the following data modalities (subject to per-session availability):

| Modality | Source |
| --- | --- |
| GCaMP fluorescence signal | `photometry/photometry.signal.pqt` |
| Isosbestic control signal | `photometry/photometry.signal.pqt` |
| Fiber photometry hardware metadata | `fiber_photometry.yaml` + session data |
| Fiber tip anatomical coordinates | placeholder (NaN) until histology data available |
| Wheel position, kinematics, and movements | `alf/{task}/_ibl_wheel*` |
| Behavioral trials | `alf/_ibl_trials.*` |
| Session epochs (task vs passive) | `alf/task.*` |
| Passive replay stimuli and intervals | `alf/passiveStims.*`, `alf/passiveGabor.*` |
| Lick times | `alf/licks.*` |
| Pose estimation (left / right / body cameras) | Lightning Pose → DLC fallback |
| Pupil tracking (left / right cameras) | `alf/*Camera.features.*` |
| ROI motion energy | `alf/*Camera.ROIMotionEnergy.*` |
| Raw behavioral video | `raw_video_data/_iblrig_*Camera.raw.mp4` |

---

## Repository structure

```text
IBL-fiberphotometry-to-nwb/
├── LICENSE
├── make_env.yml
├── pyproject.toml
├── README.md
├── documentation/                           # project documentation
│   ├── introduction_to_documentation.md     # documentation index
│   ├── conversion/                          # NWB conversion docs
│   │   ├── introduction_to_conversion.md
│   │   ├── conversion_overview.md
│   │   ├── data_interface_design.md
│   │   └── fiber_photometry_metadata_guide.md
│   ├── development/                         # environment and dev workflow
│   │   ├── environment.md
│   │   └── introduction_to_development.md
│   ├── ibl_science/                         # scientific context
│   │   └── introduction_to_ibl_science.md
│   └── one_api_data_access/                 # data loading
│       └── introduction_to_one_api.md
└── src/
    └── ibl_fiberphotometry_to_nwb/
        └── fiber_photometry/
            ├── __init__.py
            ├── nwbconverter.py          # IblConverter and FiberPhotometryNWBConverter
            ├── convert_session.py       # session_to_nwb() — single-session entry point
            ├── convert_all_sessions.py  # dataset_to_nwb() — batch entry point
            ├── conversion_notes.md      # design notes and extension guide
            ├── _metadata/
            │   ├── general_metadata.yaml    # experiment-level NWB metadata
            │   └── fiber_photometry.yaml    # hardware specifications
            ├── datainterfaces/
            │   ├── __init__.py
            │   ├── _fiber_photometry_interfaces.py
            │   ├── _fp_wheel_interfaces.py
            │   └── _optical_fibers_anatomical_localization_interface.py
            ├── tutorials/
            │   └── fiber_photometry.ipynb
            └── utils/
                ├── __init__.py
                └── tasks.py
```

---

## Key concepts

### DataInterface

A [DataInterface](https://neuroconv.readthedocs.io/en/main/user_guide/datainterfaces.html)
converts a single data modality to NWB. Each interface in this project:

1. Declares the files it needs via `get_data_requirements()`.
2. Reports availability (without downloading) via `check_availability()`.
3. Adds data to the NWB file via `add_to_nwbfile()`.
4. Optionally provides metadata via `get_metadata()`.

This project defines three custom interfaces:

- **`FiberPhotometryInterface`** — loads GCaMP and isosbestic signals using
  `PhotometrySessionLoader`, creates all hardware devices and the
  `FiberPhotometryTable`, and writes `FiberPhotometryResponseSeries` objects.
- **`OpticalFibersAnatomicalLocalizationInterface`** — placeholder that creates
  the anatomical coordinate table structure; coordinate values are `NaN` until
  the IBL histology pipeline provides fiber tip locations.
- **`FiberPhotometryWheelPosition/Kinematics/MovementsInterface`** — extend
  the standard IBL wheel interfaces with support for task-specific ALF
  collections (e.g. `alf/task_00/`).

### NWBConverter

A [NWBConverter](https://neuroconv.readthedocs.io/en/main/user_guide/nwbconverter.html)
combines multiple data interfaces and coordinates metadata. This project uses:

- **`IblConverter`** — base class that fetches session, lab, and subject
  metadata from the ONE / Alyx API.
- **`FiberPhotometryNWBConverter`** — extends `IblConverter` with
  experiment-level metadata from `general_metadata.yaml`.

### Conversion scripts

- **`convert_session.py`** — `session_to_nwb()` converts a single session
  identified by its experiment ID (`eid`).
- **`convert_all_sessions.py`** — `dataset_to_nwb()` converts a list of
  sessions in parallel using `ProcessPoolExecutor`.

---

## Extending the conversion

### Completing hardware metadata

Fill in the `# TODO` fields in
[`_metadata/fiber_photometry.yaml`](src/ibl_fiberphotometry_to_nwb/fiber_photometry/_metadata/fiber_photometry.yaml)
(optical fiber model, excitation source, photodetector, filters, dichroic mirror).
No code changes are required — the file is read dynamically.

**See the [Fiber Photometry Metadata Guide](documentation/conversion/fiber_photometry_metadata_guide.md) for step-by-step instructions with examples for every hardware component.**

### Adding real fiber tip coordinates

`OpticalFibersAnatomicalLocalizationInterface` currently writes `NaN`
placeholders. Once the IBL histology pipeline provides data, update the
`add_to_nwbfile()` method — see the step-by-step guide in
[conversion_notes.md](src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md#how-to-modify-opticalfibersanatomicallocalizationinterface)
or the [metadata guide](documentation/conversion/fiber_photometry_metadata_guide.md#adding-fiber-tip-coordinates-anatomical-localization).

### Modifying the FiberPhotometryInterface

To add new brain areas, new signal types, or alternative source files, see
[conversion_notes.md](src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md#how-to-modify-fiberphotometryinterface)
or the [metadata guide](documentation/conversion/fiber_photometry_metadata_guide.md#supporting-a-new-signal-type).

### Adding a new conversion

1. Create a new directory under `src/ibl_fiberphotometry_to_nwb/`.
2. Implement data interfaces inheriting from `BaseIBLDataInterface` or existing
   interfaces.
3. Create an `NWBConverter` subclass combining all interfaces.
4. Write `convert_session.py` and `convert_all_sessions.py` scripts.
5. Add metadata YAML files for experiment-level and hardware metadata.

---

## Environment

- Python 3.10+ (tested on 3.10, 3.12, 3.13)
- Uses `conda` for environment management
- See [documentation/development/environment.md](documentation/development/environment.md) for the full list of installed packages and version details

---

## License

BSD 3-Clause License. See [LICENSE](LICENSE) file for details.
