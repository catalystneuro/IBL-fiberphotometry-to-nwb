from copy import deepcopy
from pathlib import Path

from brainbox.io.one import PhotometrySessionLoader
from ibl_to_nwb.datainterfaces._base_ibl_interface import BaseIBLDataInterface
from neuroconv.tools.fiber_photometry import add_ophys_device, add_ophys_device_model
from neuroconv.utils import DeepDict, dict_deep_update, load_dict_from_file
from one.api import ONE
from pynwb import NWBFile


def add_fiberphotometry_table(nwbfile: NWBFile, metadata: dict):
    """
    Add all fiber photometry devices, indicators, and the FiberPhotometryTable to an NWB file.

    Reads hardware and indicator metadata from ``metadata["Ophys"]["FiberPhotometry"]``
    and creates the following NWB objects in order:

    1. **Device models** — ``OpticalFiberModel``, ``ExcitationSourceModel``,
       ``PhotodetectorModel``, ``BandOpticalFilterModel``, ``EdgeOpticalFilterModel``,
       ``DichroicMirrorModel`` (via :func:`neuroconv.tools.fiber_photometry.add_ophys_device_model`).
    2. **Devices** — ``ExcitationSource``, ``Photodetector``, ``BandOpticalFilter``,
       ``EdgeOpticalFilter``, ``DichroicMirror`` (via :func:`neuroconv.tools.fiber_photometry.add_ophys_device`).
    3. **OpticalFibers** — created from metadata with an associated :class:`FiberInsertion`
       object. Duplicates are skipped if the fiber name already exists in ``nwbfile.devices``.
    4. **Viral vectors and injections** — ``FiberPhotometryViruses`` and
       ``FiberPhotometryVirusInjections`` (optional; omitted if no entries in metadata).
    5. **Indicators** — ``FiberPhotometryIndicators`` (required; raises if empty).
    6. **FiberPhotometryTable** — one row per recording channel, referencing the
       devices and indicator objects created above.

    The resulting :class:`ndx_fiber_photometry.FiberPhotometry` container (which wraps
    the table, viruses, injections, and indicators) is added to ``nwbfile.lab_meta_data``
    under the key ``"fiber_photometry"``.

    Parameters
    ----------
    nwbfile : NWBFile
        The NWB file to populate. Devices and metadata objects are added in-place.
    metadata : dict
        Metadata dictionary following the structure defined in
        ``_metadata/fiber_photometry.yaml`` (accessed via the ``Ophys.FiberPhotometry``
        key path).

    Returns
    -------
    FiberPhotometryTable
        The newly created :class:`ndx_fiber_photometry.FiberPhotometryTable` instance.

    Raises
    ------
    AssertionError
        If an ``OpticalFiber``'s referenced model is not found in ``nwbfile.device_models``.
    AssertionError
        If a required row field is missing from a ``FiberPhotometryTable`` row entry.
    ValueError
        If no indicators are defined in the metadata.
    """
    from ndx_fiber_photometry import (
        FiberPhotometry,
        FiberPhotometryIndicators,
        FiberPhotometryTable,
        FiberPhotometryViruses,
        FiberPhotometryVirusInjections,
    )
    from ndx_ophys_devices import (
        FiberInsertion,
        Indicator,
        OpticalFiber,
        ViralVector,
        ViralVectorInjection,
    )

    device_model_types = [
        "OpticalFiberModel",
        "ExcitationSourceModel",
        "PhotodetectorModel",
        "BandOpticalFilterModel",
        "EdgeOpticalFilterModel",
        "DichroicMirrorModel",
    ]
    for device_type in device_model_types:
        device_models_metadata = metadata["Ophys"]["FiberPhotometry"].get(device_type + "s", [])
        for devices_metadata in device_models_metadata:
            add_ophys_device_model(
                nwbfile=nwbfile,
                device_metadata=devices_metadata,
                device_type=device_type,
            )
    device_types = [
        "ExcitationSource",
        "Photodetector",
        "BandOpticalFilter",
        "EdgeOpticalFilter",
        "DichroicMirror",
    ]
    for device_type in device_types:
        devices_metadata = metadata["Ophys"]["FiberPhotometry"].get(device_type + "s", [])
        for device_metadata in devices_metadata:
            add_ophys_device(
                nwbfile=nwbfile,
                device_metadata=device_metadata,
                device_type=device_type,
            )
    # Add Optical Fibers (special case bc they have additional FiberInsertion objects)
    optical_fibers_metadata = metadata["Ophys"]["FiberPhotometry"].get("OpticalFibers", [])
    for optical_fiber_metadata in optical_fibers_metadata:
        fiber_insertion_metadata = optical_fiber_metadata["fiber_insertion"]
        fiber_insertion = FiberInsertion(**fiber_insertion_metadata)
        optical_fiber_metadata = deepcopy(optical_fiber_metadata)
        optical_fiber_metadata["fiber_insertion"] = fiber_insertion
        assert (
            optical_fiber_metadata["model"] in nwbfile.device_models
        ), f"Device model {optical_fiber_metadata['model']} not found in NWBFile device_models for {optical_fiber_metadata['name']}."
        optical_fiber_metadata["model"] = nwbfile.device_models[optical_fiber_metadata["model"]]
        optical_fiber = OpticalFiber(**optical_fiber_metadata)
        # check if device already exists before adding to avoid duplicates
        if optical_fiber.name not in nwbfile.devices:
            nwbfile.add_device(optical_fiber)

    # Add Viral Vectors, Injections, and Indicators
    viral_vectors_metadata = metadata["Ophys"]["FiberPhotometry"].get("FiberPhotometryViruses", [])
    name_to_viral_vector = {}
    for viral_vector_metadata in viral_vectors_metadata:
        viral_vector = ViralVector(**viral_vector_metadata)
        name_to_viral_vector[viral_vector.name] = viral_vector
    if len(name_to_viral_vector) > 0:
        viruses = FiberPhotometryViruses(viral_vectors=list(name_to_viral_vector.values()))
    else:
        viruses = None

    viral_vector_injections_metadata = metadata["Ophys"]["FiberPhotometry"].get("FiberPhotometryVirusInjections", [])
    name_to_viral_vector_injection = {}
    for viral_vector_injection_metadata in viral_vector_injections_metadata:
        viral_vector = name_to_viral_vector[viral_vector_injection_metadata["viral_vector"]]
        viral_vector_injection_metadata = deepcopy(viral_vector_injection_metadata)
        viral_vector_injection_metadata["viral_vector"] = viral_vector
        viral_vector_injection = ViralVectorInjection(**viral_vector_injection_metadata)
        name_to_viral_vector_injection[viral_vector_injection.name] = viral_vector_injection
    if len(name_to_viral_vector_injection) > 0:
        virus_injections = FiberPhotometryVirusInjections(
            viral_vector_injections=list(name_to_viral_vector_injection.values())
        )
    else:
        virus_injections = None

    indicators_metadata = metadata["Ophys"]["FiberPhotometry"].get("FiberPhotometryIndicators", [])
    name_to_indicator = {}
    for indicator_metadata in indicators_metadata:
        if "viral_vector_injection" in indicator_metadata:
            viral_vector_injection = name_to_viral_vector_injection[indicator_metadata["viral_vector_injection"]]
            indicator_metadata = deepcopy(indicator_metadata)
            indicator_metadata["viral_vector_injection"] = viral_vector_injection
        indicator = Indicator(**indicator_metadata)
        name_to_indicator[indicator.name] = indicator
    if len(name_to_indicator) > 0:
        indicators = FiberPhotometryIndicators(indicators=list(name_to_indicator.values()))
    else:
        raise ValueError("At least one indicator must be specified in the metadata.")
    # Fiber Photometry Table
    fiber_photometry_table = FiberPhotometryTable(
        name=metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryTable"]["name"],
        description=metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryTable"]["description"],
    )
    required_fields = [
        "location",
        "excitation_wavelength_in_nm",
        "emission_wavelength_in_nm",
        "indicator",
        "optical_fiber",
        "excitation_source",
        "photodetector",
        "dichroic_mirror",
    ]
    device_fields = [
        "optical_fiber",
        "excitation_source",
        "photodetector",
        "dichroic_mirror",
        "excitation_filter",
        "emission_filter",
    ]
    for row_metadata in metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryTable"]["rows"]:
        for field in required_fields:
            assert (
                field in row_metadata
            ), f"FiberPhotometryTable metadata row {row_metadata['name']} is missing required field {field}."
        row_data = {field: nwbfile.devices[row_metadata[field]] for field in device_fields if field in row_metadata}
        row_data["location"] = row_metadata["location"]
        row_data["excitation_wavelength_in_nm"] = row_metadata["excitation_wavelength_in_nm"]
        row_data["emission_wavelength_in_nm"] = row_metadata["emission_wavelength_in_nm"]
        if "indicator" in row_metadata:
            row_data["indicator"] = name_to_indicator[row_metadata["indicator"]]
        if "coordinates" in row_metadata:
            row_data["coordinates"] = row_metadata["coordinates"]
        if "commanded_voltage_series" in row_metadata:
            row_data["commanded_voltage_series"] = nwbfile.acquisition[row_metadata["commanded_voltage_series"]]
        fiber_photometry_table.add_row(**row_data)
    fiber_photometry_table_metadata = FiberPhotometry(
        name="fiber_photometry",
        fiber_photometry_table=fiber_photometry_table,
        fiber_photometry_viruses=viruses,
        fiber_photometry_virus_injections=virus_injections,
        fiber_photometry_indicators=indicators,
    )
    nwbfile.add_lab_meta_data(fiber_photometry_table_metadata)

    return fiber_photometry_table


class FiberPhotometryInterface(BaseIBLDataInterface):
    """
    Data interface for IBL fiber photometry signals.

    Loads GCaMP and isosbestic fluorescence signals from the IBL data store
    (files ``photometry/photometry.signal.pqt`` and
    ``photometry/photometryROI.locations.pqt``) using
    :class:`brainbox.io.one.PhotometrySessionLoader`.

    The interface writes two :class:`ndx_fiber_photometry.FiberPhotometryResponseSeries`
    objects to the NWB file — one for the GCaMP signal (470 nm excitation) and one for
    the isosbestic control signal (415 nm excitation). Each series has shape
    ``(n_frames, n_brain_areas)`` and uses the photometry timestamps as the time axis.

    The :meth:`get_metadata` method automatically customises ``fiber_photometry.yaml``
    for each session by:

    - Creating one ``OpticalFiber`` entry per unique brain area recorded.
    - Populating ``FiberPhotometryTable`` rows (all GCaMP rows first, then all
      isosbestic rows) to match the column order of the data arrays.
    - Setting the ``fiber_photometry_table_region`` index lists in each
      ``FiberPhotometryResponseSeries`` metadata entry.

    This interface must run **before**
    :class:`OpticalFibersAnatomicalLocalizationInterface`, which depends on the
    ``OpticalFiber`` devices and ``FiberPhotometryTable`` added here.
    """

    interface_name = "FiberPhotometryInterface"
    REVISION: str | None = None

    def __init__(self, one: ONE, session: str):
        """
        Parameters
        ----------
        one : ONE
            ONE API instance connected to Alyx.
        session : str
            Session UUID (experiment ID, ``eid``).
        """
        self.one = one
        self.session = session
        self.revision = self.REVISION
        photometry_session_loader = PhotometrySessionLoader(eid=session, one=one)
        photometry_session_loader.load_photometry()
        self.photometry = photometry_session_loader.photometry

    @classmethod
    def get_data_requirements(cls) -> dict:
        """
        Declare exact data files required for fiber photometry signals.

        Note: This interface derives fiber photometry signals from specific files.

        Returns
        -------
        dict
            Data requirements with exact file paths
        """
        return {
            "exact_files_options": {
                "standard": [
                    "photometry/photometry.signal.pqt",
                    "photometry/photometryROI.locations.pqt",
                ]
            },
        }

    @classmethod
    def get_load_object_kwargs(cls) -> dict:
        """Return kwargs for one.load_object() call."""
        return {"obj": "photometry", "collection": "alf/photometry"}

    @classmethod
    def check_availability(cls, one: ONE, eid: str, **kwargs) -> dict:
        """
        Check if required data is available for a specific session.

        This method NEVER downloads data - it only checks if files exist
        using one.list_datasets(). It's designed to be fast and read-only,
        suitable for scanning many sessions.

        NO try-except patterns that hide failures. If checking fails,
        let the exception propagate.

        NOTE: Does NOT use revision filtering in check_availability(). Queries for latest
        version of all files regardless of revision tags. This matches the smart fallback
        behavior of load_object() and download methods, which try requested revision first
        but fall back to latest if not found.

        Parameters
        ----------
        one : ONE
            ONE API instance
        eid : str
            Session ID (experiment ID)
        **kwargs : dict
            Interface-specific parameters

        Returns
        -------
        dict
            {
                "available": bool,              # Overall availability
                "missing_required": [str],      # Missing required files
                "found_files": [str],           # Files that exist
                "alternative_used": str,        # Which alternative was found (if applicable)
                "requirements": dict,           # Copy of get_data_requirements()
            }

        Examples
        --------
        >>> result = WheelInterface.check_availability(one, eid)
        >>> if not result["available"]:
        >>>     print(f"Missing: {result['missing_required']}")
        """
        # STEP 1: Check quality (QC filtering)
        quality_result = cls.check_quality(one=one, eid=eid, **kwargs)

        if quality_result is not None:
            # If quality check explicitly rejects, return immediately
            if quality_result.get("available") is False:
                return quality_result
            # Otherwise, save extra fields to merge later
            extra_fields = quality_result
        else:
            extra_fields = {}

        # STEP 2: Check file existence
        requirements = cls.get_data_requirements(**kwargs)

        # Query without revision filtering to get latest version of ALL files
        # This includes both revision-tagged files (spike sorting) and untagged files (behavioral)
        # The unfiltered query returns the superset of what any revision-specific query would return
        available_datasets = one.list_datasets(eid)
        available_files = set(str(d) for d in available_datasets)

        missing_required = []
        found_files = []
        alternative_used = None

        # Check file options - this is now REQUIRED (not optional)
        # Every interface must define exact_files_options dict
        exact_files_options = requirements.get("exact_files_options", {})

        if not exact_files_options:
            raise ValueError(
                f"{cls.__name__}.get_data_requirements() must return 'exact_files_options' dict. "
                f"Even for single-format interfaces, use: {{'standard': ['file1.npy', 'file2.npy']}}"
            )

        # Check each named option - ANY complete option = available
        for option_name, option_files in exact_files_options.items():
            all_files_found = True

            for exact_file in option_files:
                # Handle wildcards
                if "*" in exact_file:
                    import re

                    pattern = re.escape(exact_file).replace(r"\*", ".*")
                    found = any(re.search(pattern, avail) for avail in available_files)
                else:
                    found = any(exact_file in avail for avail in available_files)

                if not found:
                    all_files_found = False
                    break  # This option is incomplete

            # If this option has all files, mark as available
            if all_files_found:
                found_files.extend(option_files)
                alternative_used = option_name  # Report which option was found
                break  # Found one complete option, that's enough

        # If no options were complete, mark the first option as missing for reporting
        if not alternative_used:
            first_option_name = next(iter(exact_files_options.keys()))
            missing_required.extend(exact_files_options[first_option_name])

        # STEP 3: Build result and merge extra fields from quality check
        result = {
            "available": len(missing_required) == 0,
            "missing_required": missing_required,
            "found_files": found_files,
            "alternative_used": alternative_used,
            "requirements": requirements,
        }
        result.update(extra_fields)

        return result

    def get_metadata(self) -> DeepDict:
        """
        Return session-specific fiber photometry metadata.

        Loads the base metadata template from ``_metadata/fiber_photometry.yaml``
        and calls :meth:`_update_fiber_photometry_metadata` to customise it for
        this session (optical fibers per brain area, FiberPhotometryTable rows,
        and FiberPhotometryResponseSeries region indices). The result is
        deep-merged on top of the parent class metadata.

        Returns
        -------
        DeepDict
            Metadata dictionary with ``Ophys.FiberPhotometry`` fully populated
            for this session.
        """
        metadata = super().get_metadata()
        metadata_copy = deepcopy(metadata)  # To avoid modifying the parent class's metadata

        # Use single source of truth when updating metadata
        fp_metadata = load_dict_from_file(
            file_path=Path(__file__).parent.parent / "_metadata" / "fiber_photometry.yaml"
        )
        # The fiber_photometry.yaml can be used to define metadata common to all experimental sessions, e.g., excitation source, optical filters, photosensor, indicators, etc.
        # For metadata that varies from session to session, you can write a function that automatically updates the corresponding fields and call it here.
        # For example, if the optical fiber was implanted in a different brain area or multiple areas, you will need to update the list in OpticalFibers with the corresponding fiber insertion values.
        # Add a row to the FiberPhotometryTable and update the fiber_photometry_table_region to match the order of the FiberPhotometrySeries used to save the calcium and isosbestic signals.
        # NB: The dimensions of the FiberPhotometrySeries are time x n_areas.
        updated_fp_metadata = self._update_fiber_photometry_metadata(fp_metadata)
        fp_metadata = dict_deep_update(fp_metadata, updated_fp_metadata)

        metadata_copy = dict_deep_update(metadata_copy, fp_metadata)
        return metadata_copy

    def _update_fiber_photometry_metadata(self, fiber_photometry_metadata: dict) -> dict:
        """
        Customise the base fiber photometry metadata for this recording session.

        This method modifies ``fiber_photometry_metadata["Ophys"]["FiberPhotometry"]``
        in-place and returns the updated dictionary. It performs three main steps:

        1. **OpticalFibers** — clears the template list and adds one
           ``OpticalFiber`` entry per unique brain area found in
           ``self.photometry`` (e.g. ``optical_fiber_DMS``, ``optical_fiber_NAc``).
           Fiber insertion coordinates are set to placeholder values (``0.0`` and
           ``"<reference point>"``); replace these with actual values once the
           histology pipeline provides them.

        2. **FiberPhotometryTable rows** — rebuilds the row list so that all GCaMP
           rows come first (one per brain area) followed by all isosbestic rows.
           This order matches the column layout of the ``FiberPhotometryResponseSeries``
           data arrays (``n_frames × n_areas``).

        3. **FiberPhotometryResponseSeries region indices** — updates the
           ``fiber_photometry_table_region`` list in each series metadata entry to
           reference the correct row indices from step 2.

        Parameters
        ----------
        fiber_photometry_metadata : dict
            Base metadata dictionary loaded from ``fiber_photometry.yaml``.

        Returns
        -------
        dict
            Updated ``fiber_photometry_metadata`` with session-specific
            ``OpticalFibers``, ``FiberPhotometryTable.rows``, and
            ``FiberPhotometryResponseSeries`` entries.

        Raises
        ------
        NotImplementedError
            If the photometry data contains signal types other than
            ``"GCaMP"`` and ``"Isosbestic"``.

        Notes
        -----
        To add support for a new brain area or a new excitation wavelength,
        update ``fiber_photometry.yaml`` and extend
        ``signal_type_to_excitation_nm`` in this method accordingly.
        """
        fp_metadata = fiber_photometry_metadata["Ophys"]["FiberPhotometry"]

        # Save template rows keyed by excitation wavelength before clearing defaults
        default_rows = fp_metadata["FiberPhotometryTable"]["rows"]
        row_templates = {row["excitation_wavelength_in_nm"]: row for row in default_rows}

        # Pop default optical_fiber and default FiberPhotometryTable rows
        fp_metadata["OpticalFibers"] = []
        fp_metadata["FiberPhotometryTable"]["rows"] = []

        signal_types = list(self.photometry.keys())

        # Check signal types are only "GCaMP" and "Isosbestic"
        supported_signal_types = {"GCaMP", "Isosbestic"}
        unsupported = set(signal_types) - supported_signal_types
        if unsupported:
            raise NotImplementedError(
                f"Signal types {unsupported} are not supported. Only {supported_signal_types} are implemented."
            )

        # Extract target brain areas from photometry DataFrame columns (exclude "times")
        first_signal_type = signal_types[0]
        target_areas = [col for col in self.photometry[first_signal_type].columns if col != "times"]

        # Map each signal type to its excitation wavelength and template row
        signal_type_to_excitation_nm = {"GCaMP": 470.0, "Isosbestic": 415.0}

        # Add one OpticalFiber per unique target area (with dummy fiber_insertion values)
        existing_fiber_names = set()
        for target_area in target_areas:
            optical_fiber_name = f"optical_fiber_{target_area}"
            if optical_fiber_name not in existing_fiber_names:
                fp_metadata["OpticalFibers"].append(
                    {
                        "name": optical_fiber_name,
                        "description": f"Chronically implanted optic fiber in {target_area}.",
                        "model": "optical_fiber_model",
                        "serial_number": "<serial number of the optical fiber>",
                        "fiber_insertion": {
                            "insertion_position_ap_in_mm": 0.0,
                            "insertion_position_ml_in_mm": 0.0,
                            "insertion_position_dv_in_mm": 0.0,
                            "position_reference": "<reference point>",
                            "hemisphere": "<hemisphere>",
                        },
                    }
                )
                existing_fiber_names.add(optical_fiber_name)

        # Add FiberPhotometryTable rows: all GCaMP rows first, then all Isosbestic rows.
        # This matches the data layout (n_areas x time) per FiberPhotometryResponseSeries.
        row_index = 0
        signal_type_to_row_indices: dict[str, list[int]] = {st: [] for st in signal_types}

        for signal_type in ["GCaMP", "Isosbestic"]:
            if signal_type not in signal_types:
                continue
            excitation_nm = signal_type_to_excitation_nm[signal_type]
            template = row_templates.get(excitation_nm, {})
            for target_area in target_areas:
                row = {
                    **template,  # carry over all template fields (devices, wavelengths, indicator, etc.)
                    "name": str(row_index),
                    "location": target_area,
                    "optical_fiber": f"optical_fiber_{target_area}",
                }
                fp_metadata["FiberPhotometryTable"]["rows"].append(row)
                signal_type_to_row_indices[signal_type].append(row_index)
                row_index += 1

        # Map FiberPhotometryResponseSeries names to their signal type
        series_name_to_signal_type = {
            "gcamp_signal": "GCaMP",
            "isosbestic_signal": "Isosbestic",
        }

        # Update fiber_photometry_table_region in each FiberPhotometryResponseSeries
        for series_metadata in fp_metadata["FiberPhotometryResponseSeries"]:
            signal_type = series_name_to_signal_type.get(series_metadata["name"])
            if signal_type is not None and signal_type in signal_type_to_row_indices:
                series_metadata["fiber_photometry_table_region"] = signal_type_to_row_indices[signal_type]

        return fp_metadata

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict | None = None,
        *,
        stub_test: bool = False,
    ):
        """
        Add fiber photometry devices and response series to the NWB file.

        If the ``"fiber_photometry"`` lab metadata container does not yet exist,
        this method calls :func:`add_fiberphotometry_table` to create all device
        models, devices, indicators, and the :class:`FiberPhotometryTable`.

        It then iterates over every ``FiberPhotometryResponseSeries`` entry in
        ``metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"]``
        and adds a :class:`ndx_fiber_photometry.FiberPhotometryResponseSeries`
        to ``nwbfile.acquisition`` for each one. The data shape is
        ``(n_frames, n_brain_areas)``; when ``stub_test=True`` only the first
        1000 frames are written.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file to add data to.
        metadata : dict
            Metadata dictionary produced by :meth:`get_metadata`. Must contain
            the ``Ophys.FiberPhotometry.FiberPhotometryResponseSeries`` key.
        stub_test : bool, optional
            If ``True``, truncate each series to the first 1000 frames to
            create a lightweight test file, by default False.

        Raises
        ------
        ValueError
            If ``metadata`` is ``None``.
        """
        from ndx_fiber_photometry import FiberPhotometryResponseSeries

        if metadata is None:
            raise ValueError("metadata must be provided to add_to_nwbfile.")

        if stub_test:
            stub_frames = 1000
        else:
            stub_frames = None

        # Add Fiber Photometry metadata if not already added
        if "fiber_photometry" not in nwbfile.lab_meta_data:
            fiber_photometry_table = add_fiberphotometry_table(nwbfile=nwbfile, metadata=metadata)
        else:
            fiber_photometry_table = nwbfile.lab_meta_data["fiber_photometry"].fiber_photometry_table

        # Fiber Photometry Response Series
        all_series_metadata = metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"]
        signal_types = self.photometry.keys()

        for fiber_photometry_response_series_metadata in all_series_metadata:

            fiber_photometry_table_region = fiber_photometry_table.create_fiber_photometry_table_region(
                description=fiber_photometry_response_series_metadata["fiber_photometry_table_region_description"],
                region=fiber_photometry_response_series_metadata["fiber_photometry_table_region"],
            )

            # Get the data
            for signal_type in signal_types:
                if signal_type.lower() in fiber_photometry_response_series_metadata["name"]:
                    break
            signal_df = self.photometry[signal_type]
            data = signal_df.drop(columns=["times"], errors="ignore").iloc[:stub_frames].to_numpy()
            timestamps = signal_df["times"] if "times" in signal_df.columns else signal_df.index.to_numpy()
            timestamps = timestamps[:stub_frames]

            fiber_photometry_response_series = FiberPhotometryResponseSeries(
                name=fiber_photometry_response_series_metadata["name"],
                description=fiber_photometry_response_series_metadata["description"],
                data=data,
                unit=fiber_photometry_response_series_metadata["unit"],
                fiber_photometry_table_region=fiber_photometry_table_region,
                timestamps=timestamps,
            )
            nwbfile.add_acquisition(fiber_photometry_response_series)
