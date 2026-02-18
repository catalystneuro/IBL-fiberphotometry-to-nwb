from copy import deepcopy
from pathlib import Path
from typing import Optional

from ibl_to_nwb.datainterfaces._base_ibl_interface import BaseIBLDataInterface
from neuroconv.tools.fiber_photometry import add_ophys_device, add_ophys_device_model
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict, dict_deep_update, load_dict_from_file
from one.api import ONE
from pynwb import NWBFile


def add_fiberphotometry_table(nwbfile: NWBFile, metadata: dict):
    """Add fiber photometry devices to the NWB file based on the provided metadata."""
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


class RawFiberPhotometryInterface(BaseIBLDataInterface):
    """An interface for raw IBL fiber photometry signals."""

    interface_name = "RawFiberPhotometryInterface"
    REVISION: str | None = None

    def __init__(self, one: ONE, session: str):
        self.one = one
        self.session = session
        self.revision = self.REVISION

    @classmethod
    def get_data_requirements(cls) -> dict:
        """
        Declare exact data files required for raw fiber photometry signals.

        Note: This interface derives raw fiber photometry signals from specific files.

        Returns
        -------
        dict
            Data requirements with exact file paths
        """
        return {
            "exact_files_options": {
                "standard": [
                    "raw_photometry_data/_neurophotometrics_fpData.channels.csv",
                    "raw_photometry_data/_neurophotometrics_fpData.digitalInputs.pqt",
                    "raw_photometry_data/_neurophotometrics_fpData.raw.pqt",
                ]
            },
        }

    @classmethod
    def get_load_object_kwargs(cls) -> dict:
        """Return kwargs for one.load_object() call."""
        return {"obj": "fpData", "collection": "raw_photometry_data"}

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
        Get metadata for the Meso segmentation data.

        Returns
        -------
        DeepDict
            Dictionary containing metadata including plane segmentation details,
            fluorescence data, and segmentation images.
        """
        metadata = super().get_metadata()
        metadata_copy = deepcopy(metadata)  # To avoid modifying the parent class's metadata

        # Use single source of truth when updating metadata
        fp_metadata = load_dict_from_file(
            file_path=Path(__file__).parent.parent / "_metadata" / "fiber_photometry.yaml"
        )

        # Create Device entry
        metadata_copy = dict_deep_update(metadata_copy, fp_metadata)
        return metadata_copy

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: Optional[dict] = None,
        *,
        stub_test: bool = False,
    ):
        """
        Add raw fiber photometry data to the NWB file.

        This method ONLY adds raw fiber photometry data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file to add data to
        metadata : dict, optional
            Metadata dictionary (not currently used)
        """
        from ndx_fiber_photometry import (
            CommandedVoltageSeries,
            FiberPhotometry,
            FiberPhotometryIndicators,
            FiberPhotometryResponseSeries,
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

        raw_fp_data = self.one.load_object(self.session, **self.get_load_object_kwargs())

        # Load Data
        if stub_test:
            stub_frames = 1000  # TODO add stubbing interval
        else:
            stub_frames = None

        # Add Fiber Photometry metadata if not already added
        if "fiber_photometry" not in nwbfile.lab_meta_data:
            fiber_photometry_table = add_fiberphotometry_table(nwbfile=nwbfile, metadata=metadata)
        else:
            fiber_photometry_table = nwbfile.lab_meta_data["fiber_photometry"].fiber_photometry_table

        # TODO is there a commanded voltage series to add?
        # Commanded Voltage Series
        # for commanded_voltage_series_metadata in metadata["Ophys"]["FiberPhotometry"].get("CommandedVoltageSeries", []):
        #     commanded_voltage_series = CommandedVoltageSeries(
        #         name=commanded_voltage_series_metadata["name"],
        #         description=commanded_voltage_series_metadata["description"],
        #         data=data,
        #         unit=commanded_voltage_series_metadata["unit"],
        #         frequency=commanded_voltage_series_metadata["frequency"],
        #         **timing_kwargs,
        #     )
        #     nwbfile.add_acquisition(commanded_voltage_series)

        # Fiber Photometry Response Series
        all_series_metadata = metadata["Ophys"]["FiberPhotometry"]["FiberPhotometryResponseSeries"]
        for fiber_photometry_response_series_metadata in all_series_metadata:
            # TODO add function to select the correct LedState for now I'm hardcoding it in the metadata
            stream_name = fiber_photometry_response_series_metadata["stream_name"]
            led_state = fiber_photometry_response_series_metadata["led_state"]
            # Get the data
            data = raw_fp_data["raw"][stream_name][raw_fp_data["raw"]["LedState"] == led_state]
            data = data[:stub_frames].to_numpy()
            timestamps = raw_fp_data["raw"]["SystemTimestamp"][raw_fp_data["raw"]["LedState"] == led_state]
            timestamps = timestamps[:stub_frames].to_numpy()

            fiber_photometry_table_region = fiber_photometry_table.create_fiber_photometry_table_region(
                description=fiber_photometry_response_series_metadata["fiber_photometry_table_region_description"],
                region=fiber_photometry_response_series_metadata["fiber_photometry_table_region"],
            )

            fiber_photometry_response_series = FiberPhotometryResponseSeries(
                name=fiber_photometry_response_series_metadata["name"],
                description=fiber_photometry_response_series_metadata["description"],
                data=data,
                unit=fiber_photometry_response_series_metadata["unit"],
                fiber_photometry_table_region=fiber_photometry_table_region,
                timestamps=timestamps,
            )
            nwbfile.add_acquisition(fiber_photometry_response_series)


class ProcessedFiberPhotometryInterface(BaseIBLDataInterface):
    """An interface for processed IBL fiber photometry signals."""

    interface_name = "ProcessedFiberPhotometryInterface"
    REVISION: str | None = None

    def __init__(self, one: ONE, session: str):
        self.one = one
        self.session = session
        self.revision = self.REVISION

    @classmethod
    def get_data_requirements(cls) -> dict:
        """
        Declare exact data files required for processed fiber photometry signals.

        Note: This interface derives processed fiber photometry signals from specific files.

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
        Get metadata for the Meso segmentation data.

        Returns
        -------
        DeepDict
            Dictionary containing metadata including plane segmentation details,
            fluorescence data, and segmentation images.
        """
        metadata = super().get_metadata()
        metadata_copy = deepcopy(metadata)  # To avoid modifying the parent class's metadata

        # Use single source of truth when updating metadata
        fp_metadata = load_dict_from_file(
            file_path=Path(__file__).parent.parent / "_metadata" / "fiber_photometry.yaml"
        )

        # Create Device entry
        metadata_copy = dict_deep_update(metadata_copy, fp_metadata)
        return metadata_copy

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: Optional[dict] = None,
        *,
        stub_test: bool = False,
    ):
        """
        Add raw fiber photometry data to the NWB file.

        This method ONLY adds raw fiber photometry data to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file to add data to
        metadata : dict, optional
            Metadata dictionary (not currently used)
        """
        from ndx_fiber_photometry import (
            CommandedVoltageSeries,
            FiberPhotometryResponseSeries,
        )

        processed_fp_data = self.one.load_object(self.session, **self.get_load_object_kwargs())

        if stub_test:
            stub_frames = 1000  # TODO add stubbing interval
        else:
            stub_frames = None

        # TODO is there a commanded voltage series to add?
        # Commanded Voltage Series
        # for commanded_voltage_series_metadata in metadata["Ophys"]["FiberPhotometry"].get("CommandedVoltageSeries", []):
        #     commanded_voltage_series = CommandedVoltageSeries(
        #         name=commanded_voltage_series_metadata["name"],
        #         description=commanded_voltage_series_metadata["description"],
        #         data=data,
        #         unit=commanded_voltage_series_metadata["unit"],
        #         frequency=commanded_voltage_series_metadata["frequency"],
        #         **timing_kwargs,
        #     )
        #     nwbfile.add_acquisition(commanded_voltage_series)

        # Add Fiber Photometry metadata if not already added
        if "fiber_photometry" not in nwbfile.lab_meta_data:
            fiber_photometry_table = add_fiberphotometry_table(nwbfile=nwbfile, metadata=metadata)
        else:
            fiber_photometry_table = nwbfile.lab_meta_data["fiber_photometry"].fiber_photometry_table
        # Fiber Photometry Response Series
        all_series_metadata = metadata["Ophys"]["FiberPhotometry"]["ProcessedFiberPhotometryResponseSeries"]
        ophys_module = get_module(nwbfile=nwbfile, name="ophys", description="Processed fiber photometry signals")

        for fiber_photometry_response_series_metadata in all_series_metadata:

            fiber_photometry_table_region = fiber_photometry_table.create_fiber_photometry_table_region(
                description=fiber_photometry_response_series_metadata["fiber_photometry_table_region_description"],
                region=fiber_photometry_response_series_metadata["fiber_photometry_table_region"],
            )
            stream_name = fiber_photometry_response_series_metadata["stream_name"]
            wavelength = fiber_photometry_table[fiber_photometry_table_region.data][
                "excitation_wavelength_in_nm"
            ].to_numpy()[0]
            # Get the data
            data = processed_fp_data.signal[stream_name][processed_fp_data.signal["wavelength"] == wavelength]
            data = data[:stub_frames].to_numpy()
            timestamps = processed_fp_data.signal["times"][processed_fp_data.signal["wavelength"] == wavelength]
            timestamps = timestamps[:stub_frames].to_numpy()

            fiber_photometry_response_series = FiberPhotometryResponseSeries(
                name=fiber_photometry_response_series_metadata["name"],
                description=fiber_photometry_response_series_metadata["description"],
                data=data,
                unit=fiber_photometry_response_series_metadata["unit"],
                fiber_photometry_table_region=fiber_photometry_table_region,
                timestamps=timestamps,
            )
            ophys_module.add(fiber_photometry_response_series)
