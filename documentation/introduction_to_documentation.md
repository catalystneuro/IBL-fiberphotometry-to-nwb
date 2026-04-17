# Documentation Guide

IBL-fiberphotometry-to-NWB is a data conversion pipeline that transforms International Brain Laboratory (IBL) fiber photometry experimental data into [Neurodata Without Borders (NWB)](https://nwb-overview.readthedocs.io/) format using [NeuroConv](https://neuroconv.readthedocs.io/). This documentation is organized into four sections by topic.

## Documentation Sections

### [Conversion](conversion/)
Converting IBL fiber photometry data to NWB format.

- [introduction_to_conversion.md](conversion/introduction_to_conversion.md) — Architecture overview: interfaces, converters, and the metadata pipeline
- [conversion_overview.md](conversion/conversion_overview.md) — How to run conversions: single session, batch, stub mode, and output structure
- [data_interface_design.md](conversion/data_interface_design.md) — Interface contract specification (`get_data_requirements`, `check_availability`, `add_to_nwbfile`)
- [fiber_photometry_metadata_guide.md](conversion/fiber_photometry_metadata_guide.md) — **Step-by-step guide for completing fiber photometry hardware metadata** (optical fibers, excitation sources, photodetectors, filters, indicators, coordinates)

### [ONE API Data Access](one_api_data_access/)
Loading IBL fiber photometry data using the ONE API.

- [introduction_to_one_api.md](one_api_data_access/introduction_to_one_api.md) — How data is accessed, `PhotometrySessionLoader`, and task collections

### [IBL Science](ibl_science/)
Experimental and scientific foundations of the fiber photometry dataset.

- [introduction_to_ibl_science.md](ibl_science/introduction_to_ibl_science.md) — Experiment overview: neuromodulators, decision-making task, and recorded data modalities

### [Development](development/)
Environment setup, dependency management, and development workflow.

- [environment.md](development/environment.md) — **Full environment specification**: conda environment, installed packages, key dependencies, and version pinning
- [introduction_to_development.md](development/introduction_to_development.md) — Development workflow, code style, and project structure

## Related Resources

- [README.md](../README.md) — Project overview, installation, and quick start
- [conversion_notes.md](../src/ibl_fiberphotometry_to_nwb/fiber_photometry/conversion_notes.md) — Design decisions, known limitations, and extension instructions
- [IBL-to-NWB documentation](https://github.com/h-mayorquin/IBL-to-nwb/tree/heberto_conversion/documentation) — Documentation for the parent IBL-to-NWB project (Neuropixels / Brain Wide Map)
