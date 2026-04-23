# Fiber Photometry Metadata Guide

This document provides step-by-step instructions for completing the fiber photometry hardware metadata and customizing the conversion for your specific experimental setup.

All hardware specifications are read from a single YAML file:
`src/ibl_fiberphotometry_to_nwb/fiber_photometry/_metadata/fiber_photometry.yaml`

**No code changes are needed to update hardware values** — the file is read dynamically at conversion time by `FiberPhotometryInterface.get_metadata()`.

---

## Table of Contents

1. [Overview of fiber_photometry.yaml](#overview-of-fiber_photometryyaml)
2. [Completing optical fiber metadata](#completing-optical-fiber-metadata)
3. [Completing excitation source metadata](#completing-excitation-source-metadata)
4. [Completing photodetector metadata](#completing-photodetector-metadata)
5. [Completing optical filter metadata](#completing-optical-filter-metadata)
6. [Completing dichroic mirror metadata](#completing-dichroic-mirror-metadata)
7. [Completing indicator metadata](#completing-indicator-metadata)
8. [Adding fiber insertion coordinates per session](#adding-fiber-insertion-coordinates-per-session)
9. [Adding fiber tip coordinates (anatomical localization)](#adding-fiber-tip-coordinates-anatomical-localization)
10. [Supporting a new signal type](#supporting-a-new-signal-type)
11. [FiberPhotometryTable and FiberPhotometryResponseSeries](#fiberphotometrytable-and-fiberphotometryresponseseries)

---

## Overview of fiber_photometry.yaml

The metadata file is structured as a hierarchy under `Ophys > FiberPhotometry`:

```yaml
Ophys:
  FiberPhotometry:
    OpticalFiberModels:       # Physical fiber specifications
    OpticalFibers:            # Fiber instances (one per implant)
    ExcitationSourceModels:   # LED/laser specifications
    ExcitationSources:        # LED/laser instances
    PhotodetectorModels:      # Detector specifications
    Photodetectors:           # Detector instances
    BandOpticalFilterModels:  # Bandpass filter specifications
    BandOpticalFilters:       # Filter instances
    DichroicMirrorModels:     # Dichroic mirror specifications
    DichroicMirrors:          # Mirror instances
    FiberPhotometryIndicators: # Fluorescent indicators (GCaMP, etc.)
    FiberPhotometryTable:     # Recording channel configuration
    FiberPhotometryResponseSeries: # Signal output definitions
```

Fields marked with `# TODO` are placeholders that need to be filled in with your actual hardware specifications. The conversion runs correctly with placeholder values, but the metadata should be completed before DANDI upload.

---

## Completing optical fiber metadata

Open `_metadata/fiber_photometry.yaml` and find the `OpticalFiberModels` section:

```yaml
# Before (placeholder)
OpticalFiberModels:
  - name: optical_fiber_model
    description: Chronically implantable optic fiber.
    manufacturer: <manufacturer of the optical fiber>  # TODO
    model_number: <model of the optical fiber>          # TODO
    numerical_aperture: 0.0                             # TODO
    core_diameter_in_um: 0.0                            # TODO
    active_length_in_mm: 0.0                            # TODO
    ferrule_diameter_in_mm: 0.0                         # TODO
    ferrule_name: <ferrule name of the optical fiber>   # TODO
```

```yaml
# After (example: Thorlabs fiber)
OpticalFiberModels:
  - name: optical_fiber_model
    description: Chronically implantable optic fiber.
    manufacturer: Thorlabs
    model_number: FT200UMT
    numerical_aperture: 0.39
    core_diameter_in_um: 200.0
    active_length_in_mm: 5.0
    ferrule_diameter_in_mm: 1.25
    ferrule_name: LC/PC ceramic ferrule
```

If your experiment uses **multiple fiber models** (e.g. different core diameters for different brain regions), add additional entries to the list:

```yaml
OpticalFiberModels:
  - name: optical_fiber_model_200um
    description: 200um core fiber for deep structures.
    manufacturer: Thorlabs
    model_number: FT200UMT
    numerical_aperture: 0.39
    core_diameter_in_um: 200.0
    # ...
  - name: optical_fiber_model_400um
    description: 400um core fiber for cortical regions.
    manufacturer: Thorlabs
    model_number: FT400UMT
    numerical_aperture: 0.39
    core_diameter_in_um: 400.0
    # ...
```

Then update the `model:` field in the `OpticalFibers` section to reference the correct model name.

---

## Completing excitation source metadata

Find the `ExcitationSourceModels` section. There are two entries — one for the calcium-dependent signal (470 nm) and one for the isosbestic control (415 nm):

```yaml
# Before
ExcitationSourceModels:
  - name: excitation_source_model_calcium
    description: excitation source for the sensor's fluorescence signal.
    manufacturer: <manufacturer>  # TODO
    model_number: <model number>  # TODO
    source_type: LED              # TODO confirm
    excitation_mode: one-photon
    wavelength_range_in_nm: [460.0, 490.0]  # TODO confirm

  - name: excitation_source_model_isosbestic
    description: excitation source for the sensor's isosbestic control.
    manufacturer: <manufacturer>  # TODO
    model_number: <model number>  # TODO
    source_type: LED              # TODO confirm
    excitation_mode: one-photon
    wavelength_range_in_nm: [400.0, 410.0]  # TODO confirm
```

```yaml
# After (example: Doric Lenses LEDs)
ExcitationSourceModels:
  - name: excitation_source_model_calcium
    description: 470nm LED for GCaMP calcium-dependent fluorescence excitation.
    manufacturer: Doric Lenses
    model_number: CLED_465
    source_type: LED
    excitation_mode: one-photon
    wavelength_range_in_nm: [460.0, 480.0]

  - name: excitation_source_model_isosbestic
    description: 415nm LED for GCaMP isosbestic control excitation.
    manufacturer: Doric Lenses
    model_number: CLED_405
    source_type: LED
    excitation_mode: one-photon
    wavelength_range_in_nm: [405.0, 420.0]
```

---

## Completing photodetector metadata

```yaml
# Before
PhotodetectorModels:
  - name: photodetector_model
    description: <description>       # TODO
    manufacturer: <manufacturer>     # TODO
    model_number: <model>            # TODO
    detector_type: <type>            # TODO
    wavelength_range_in_nm: [500.0, 540.0]  # TODO
    gain: 0.0                        # TODO
    gain_unit: n.a                   # TODO
```

```yaml
# After (example: femtonics photomultiplier)
PhotodetectorModels:
  - name: photodetector_model
    description: Silicon photomultiplier for GCaMP emission detection.
    manufacturer: Doric Lenses
    model_number: FPC_2
    detector_type: SiPM
    wavelength_range_in_nm: [500.0, 550.0]
    gain: 1.0
    gain_unit: V/nW
```

---

## Completing optical filter metadata

Two filter models are defined: an emission filter and an excitation filter.

```yaml
# Before
BandOpticalFilterModels:
  - name: emission_filter_model
    description: emission filter model for GCaMP fluorescence signal.
    manufacturer: <manufacturer>  # TODO
    model_number: <model>         # TODO
    filter_type: Bandpass
    center_wavelength_in_nm: 520.0  # TODO confirm
    bandwidth_in_nm: 40.0

  - name: excitation_filter_model
    description: excitation filter model for GCaMP fluorescence signal.
    manufacturer: <manufacturer>  # TODO
    model_number: <model>         # TODO
    filter_type: Bandpass
    center_wavelength_in_nm: 445.0  # TODO confirm
    bandwidth_in_nm: 90.0           # TODO confirm
```

```yaml
# After (example: Semrock filters)
BandOpticalFilterModels:
  - name: emission_filter_model
    description: GCaMP emission bandpass filter (500-540 nm).
    manufacturer: Semrock
    model_number: FF01-520/40
    filter_type: Bandpass
    center_wavelength_in_nm: 520.0
    bandwidth_in_nm: 40.0

  - name: excitation_filter_model
    description: GCaMP excitation bandpass filter (400-490 nm).
    manufacturer: Semrock
    model_number: FF01-445/90
    filter_type: Bandpass
    center_wavelength_in_nm: 445.0
    bandwidth_in_nm: 90.0
```

---

## Completing dichroic mirror metadata

```yaml
# Before
DichroicMirrorModels:
  - name: dichroic_mirror_model
    description: <description>    # TODO
    manufacturer: <manufacturer>  # TODO
    model_number: <model>         # TODO
```

```yaml
# After (example)
DichroicMirrorModels:
  - name: dichroic_mirror_model
    description: Dichroic mirror separating excitation (reflected) and emission (transmitted) light.
    manufacturer: Semrock
    model_number: FF495-Di03
```

---

## Completing indicator metadata

```yaml
# Before
FiberPhotometryIndicators:
  - name: GCaMP
    description: GCaMP calcium sensor in <location>.
    manufacturer: <manufacturer>  # TODO
    label: GCaMP
```

```yaml
# After (example)
FiberPhotometryIndicators:
  - name: GCaMP
    description: GCaMP8s calcium sensor expressed via AAV injection.
    manufacturer: Addgene
    label: GCaMP8s
```

---

## Adding fiber insertion coordinates per session

`FiberPhotometryInterface._update_fiber_photometry_metadata()` (in `datainterfaces/_fiber_photometry_interfaces.py`) creates one `OpticalFiber` entry per brain area with zeroed placeholder insertion coordinates. To supply real coordinates:

### Option A: Hard-code a lookup table

In `_update_fiber_photometry_metadata()`, replace the placeholder block:

```python
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

### Option B: Load from a per-session file

Create `_metadata/fiber_coordinates.json`:

```json
{
    "fd688232-0dd8-400b-aa66-dc23460d9f98": {
        "DMS": {"ap": -0.5, "ml": 1.5, "dv": -3.0, "reference": "bregma", "hemisphere": "right"},
        "NAc": {"ap": 1.2, "ml": 0.9, "dv": -4.5, "reference": "bregma", "hemisphere": "right"}
    }
}
```

Then in `_update_fiber_photometry_metadata()`:

```python
import json

coordinates_path = Path(__file__).parent.parent / "_metadata" / "fiber_coordinates.json"
with open(coordinates_path) as f:
    all_coords = json.load(f)
session_coords = all_coords.get(self.session, {})

for target_area in target_areas:
    coords = session_coords.get(target_area, {})
    fp_metadata["OpticalFibers"].append({
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
    })
```

---

## Adding fiber tip coordinates (anatomical localization)

`OpticalFibersAnatomicalLocalizationInterface` (in `datainterfaces/_optical_fibers_anatomical_localization_interface.py`) currently writes `NaN` placeholders for fiber tip positions in both IBL-Bregma and Allen CCFv3 coordinate spaces.

Once the IBL histology pipeline provides fiber tip coordinates, modify `add_to_nwbfile()` in the following section:

```python
# --- 8. Populate tables: one row per unique OpticalFiber ---
placeholder_coord = float("nan")  # <-- REPLACE with actual values
placeholder_region = "TODO"       # <-- REPLACE with actual brain region acronym
```

### Example: using a lookup dictionary

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

### Alternative: load at init time

```python
def __init__(self, one: ONE, session: str):
    self.one = one
    self.session = session
    self.revision = self.REVISION
    self.fiber_coordinates = self._load_fiber_coordinates()

def _load_fiber_coordinates(self) -> dict:
    """Load fiber tip coordinates from IBL data store or local file."""
    # e.g. self.one.load_object(...) or read from a local JSON/CSV
    ...
```

### Implementing `get_data_requirements()` for real data

When source data files become available (e.g. from the IBL histology pipeline), update `get_data_requirements()`:

```python
@classmethod
def get_data_requirements(cls) -> dict:
    return {
        "exact_files_options": {
            "standard": [
                "histology/fiber.tipCoordinates.json",
            ]
        },
    }
```

---

## Supporting a new signal type

Currently only `GCaMP` (470 nm excitation) and `Isosbestic` (415 nm excitation) are supported. To add a new signal type (e.g. `rCaMP` at 561 nm):

### Step 1: Add hardware entries to `fiber_photometry.yaml`

Add a new excitation source model and device:

```yaml
ExcitationSourceModels:
  # ... existing entries ...
  - name: excitation_source_model_red
    description: excitation source for rCaMP fluorescence signal.
    manufacturer: <manufacturer>
    model_number: <model>
    source_type: LED
    excitation_mode: one-photon
    wavelength_range_in_nm: [550.0, 570.0]

ExcitationSources:
  # ... existing entries ...
  - name: excitation_source_rcamp_signal
    description: excitation source for rCaMP fluorescence signal (561nm).
    model: excitation_source_model_red
```

### Step 2: Add a new `FiberPhotometryResponseSeries` entry

```yaml
FiberPhotometryResponseSeries:
  # ... existing entries ...
  - name: rcamp_signal
    description: The fluorescence signal from rCaMP emission.
    unit: a.u.
    fiber_photometry_table_region: []  # auto-populated by _update_fiber_photometry_metadata
    fiber_photometry_table_region_description: The region of the FiberPhotometryTable corresponding to the rcamp_signal.
```

### Step 3: Extend the signal type mapping in code

In `FiberPhotometryInterface._update_fiber_photometry_metadata()` (file `_fiber_photometry_interfaces.py`):

```python
signal_type_to_excitation_nm = {
    "GCaMP": 470.0,
    "Isosbestic": 415.0,
    "rCaMP": 561.0,   # new entry
}
```

Update `series_name_to_signal_type`:

```python
series_name_to_signal_type = {
    "gcamp_signal": "GCaMP",
    "isosbestic_signal": "Isosbestic",
    "rcamp_signal": "rCaMP",   # new entry
}
```

Update `supported_signal_types`:

```python
supported_signal_types = {"GCaMP", "Isosbestic", "rCaMP"}
```

---

## FiberPhotometryTable and FiberPhotometryResponseSeries

The `FiberPhotometryTable` in the NWB file contains one row per (brain area, excitation wavelength) combination. Each row references:

- An `OpticalFiber` device (one per brain area)
- An `ExcitationSource` device (one per wavelength)
- A `Photodetector`, `EmissionFilter`, `ExcitationFilter`, and `DichroicMirror`
- An `Indicator` (e.g. GCaMP)
- The brain area name (`location`)

The `FiberPhotometryResponseSeries` objects reference subsets of the table via `fiber_photometry_table_region`. For example, if there are 2 brain areas (DMS, NAc):

```
Row 0: DMS, GCaMP (470nm)
Row 1: NAc, GCaMP (470nm)
Row 2: DMS, Isosbestic (415nm)
Row 3: NAc, Isosbestic (415nm)
```

Then:
- `gcamp_signal.fiber_photometry_table_region = [0, 1]`
- `isosbestic_signal.fiber_photometry_table_region = [2, 3]`

This mapping is handled automatically by `_update_fiber_photometry_metadata()` — you do not need to set these indices manually.

---

## Summary: What to Modify and Where

| What to change | Where to change it | Code changes needed? |
|---|---|---|
| Optical fiber specs (manufacturer, NA, core diameter, etc.) | `_metadata/fiber_photometry.yaml` | No |
| Excitation source specs (LED manufacturer, wavelength) | `_metadata/fiber_photometry.yaml` | No |
| Photodetector specs | `_metadata/fiber_photometry.yaml` | No |
| Optical filter specs | `_metadata/fiber_photometry.yaml` | No |
| Dichroic mirror specs | `_metadata/fiber_photometry.yaml` | No |
| Indicator metadata (manufacturer, label) | `_metadata/fiber_photometry.yaml` | No |
| Experiment description, keywords | `_metadata/general_metadata.yaml` | No |
| Fiber insertion coordinates per session | `_fiber_photometry_interfaces.py` | Yes |
| Fiber tip coordinates (anatomical localization) | `_optical_fibers_anatomical_localization_interface.py` | Yes |
| New signal type (e.g. rCaMP) | `fiber_photometry.yaml` + `_fiber_photometry_interfaces.py` | Yes |
| New brain areas | Automatic (read from data columns) | No |

## Related Documents

- [conversion_notes.md](../../src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md) — Full design notes and known limitations
- [conversion_overview.md](conversion_overview.md) — Usage guide with troubleshooting
- [introduction_to_conversion.md](introduction_to_conversion.md) — Architecture overview
