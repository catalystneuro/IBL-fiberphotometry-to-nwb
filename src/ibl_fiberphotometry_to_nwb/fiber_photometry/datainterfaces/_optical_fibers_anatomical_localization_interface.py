from ibl_to_nwb.datainterfaces._base_ibl_interface import BaseIBLDataInterface
from ndx_anatomical_localization import (
    AllenCCFv3Space,
    AnatomicalCoordinatesTable,
    Localization,
    Space,
)
from ndx_ophys_devices import OpticalFiber
from one.api import ONE
from pynwb import NWBFile


class OpticalFibersAnatomicalLocalizationInterface(BaseIBLDataInterface):
    """
    Dummy interface for anatomical localization of optical fibers.

    This interface is a placeholder to guide future implementation once source data
    (fiber tip coordinates) becomes available from IBL.

    It creates two AnatomicalCoordinatesTable objects:
    - AnatomicalCoordinatesIBLBregmaOpticalFibers: fiber tip positions in IBL-Bregma space
    - AnatomicalCoordinatesCCFv3OpticalFibers: fiber tip positions in Allen CCFv3 space

    Both tables target the FiberPhotometryTable. Since multiple FiberPhotometryTable rows
    (e.g., GCaMP and Isosbestic channels) can share the same OpticalFiber, only one
    AnatomicalCoordinatesTable row is created per unique OpticalFiber. The localized_entity
    field is set to the first FiberPhotometryTable row index associated with that fiber.

    NOTE: The FiberPhotometryTable must already exist in the NWBFile.
    """

    interface_name = "OpticalFibersAnatomicalLocalizationInterface"
    REVISION: str | None = None

    def __init__(self, one: ONE, session: str):
        self.one = one
        self.session = session
        self.revision = self.REVISION

    @classmethod
    def get_data_requirements(cls) -> dict:
        """
        Declare exact data files required for anatomical localization of optical fibers.

        Note: This interface derives anatomical localization data from specific files.

        Returns
        -------
        dict
            Data requirements with exact file paths
        """
        return {  # TODO to be implemented by the user
            "exact_files_options": {
                "standard": [
                    "...",
                    "...",
                ]
            },
        }

    @classmethod
    def get_load_object_kwargs(cls) -> dict:
        """Return kwargs for one.load_object() call."""
        return {"obj": "...", "collection": "..."}  # TODO to be implemented by the user

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

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict | None = None,
        *,
        stub_test: bool = False,
    ):
        """
        Add anatomical localization of optical fibers to the NWB file.

        This method:
        1. Verifies that OpticalFiber devices have already been added to the NWBFile.
        2. Verifies that the FiberPhotometryTable has already been added to the NWBFile.
        3. Creates AnatomicalCoordinatesIBLBregmaOpticalFibers and
           AnatomicalCoordinatesCCFv3OpticalFibers tables, both targeting the
           FiberPhotometryTable.
        4. Adds one row per unique OpticalFiber (avoiding duplication across multiple
           FiberPhotometryTable rows that share the same fiber). The localized_entity
           field references the first FiberPhotometryTable row index for each fiber.

        NOTE: Coordinate values are set to float('nan') as placeholders. Replace with
        actual fiber tip coordinates once source data becomes available.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file to add data to. Must already contain OpticalFiber devices
            and a FiberPhotometryTable.
        metadata : dict, optional
            Metadata dictionary (not currently used).
        stub_test : bool, optional
            Not used; retained for interface consistency.

        Raises
        ------
        ValueError
            If no OpticalFiber devices are found in nwbfile.devices.
        ValueError
            If the FiberPhotometryTable is not found in nwbfile.lab_meta_data.
        """
        # --- 1. Check that OpticalFiber devices exist ---
        optical_fiber_devices = {
            name: device for name, device in nwbfile.devices.items() if isinstance(device, OpticalFiber)
        }
        if not optical_fiber_devices:
            raise ValueError(
                "No OpticalFiber devices found in nwbfile.devices. "
                "Add OpticalFiber objects (via FiberPhotometryInterface or add_fiberphotometry_table) "
                "before running OpicalFibersAnatomicalLocalizationInterface."
            )

        # --- 2. Check that FiberPhotometryTable exists ---
        fiber_photometry_lab_meta = nwbfile.lab_meta_data.get("fiber_photometry")
        if fiber_photometry_lab_meta is None:
            raise ValueError(
                "'fiber_photometry' not found in nwbfile.lab_meta_data. "
                "Add the FiberPhotometryTable (via FiberPhotometryInterface or add_fiberphotometry_table) "
                "before running OpicalFibersAnatomicalLocalizationInterface."
            )
        fiber_photometry_table = fiber_photometry_lab_meta.fiber_photometry_table

        # --- 3. Build mapping: optical_fiber_name -> first FiberPhotometryTable row index ---
        # Multiple rows in FiberPhotometryTable can reference the same OpticalFiber
        # (e.g., GCaMP and Isosbestic channels). We create one AnatomicalCoordinatesTable
        # row per unique OpticalFiber, using the first row index for localized_entity.
        fiber_name_to_first_row_index: dict[str, int] = {}
        for row_index in range(len(fiber_photometry_table)):
            optical_fiber = fiber_photometry_table["optical_fiber"][row_index]
            fiber_name = optical_fiber.name
            if fiber_name not in fiber_name_to_first_row_index:
                fiber_name_to_first_row_index[fiber_name] = row_index

        # --- 4. Create or retrieve the Localization container ---
        localization = nwbfile.lab_meta_data.get("localization")
        if localization is None:
            localization = Localization()
            nwbfile.add_lab_meta_data(localization)

        # --- 5. Create coordinate Space objects ---
        ibl_space = Space(
            name="IBLBregma",
            space_name="IBLBregma",
            origin="bregma",
            units="um",
            orientation="RAS",
        )
        ccf_space = AllenCCFv3Space(name="AllenCCFv3")

        if ibl_space.name not in localization.spaces:
            localization.add_spaces(spaces=[ibl_space])
        if ccf_space.name not in localization.spaces:
            localization.add_spaces(spaces=[ccf_space])

        # --- 6. Create AnatomicalCoordinatesTable for IBL-Bregma space ---
        ibl_table = AnatomicalCoordinatesTable(
            name="AnatomicalCoordinatesIBLBregmaOpticalFibers",
            description=(
                "Fiber tip positions in the IBL-Bregma coordinate system (origin at bregma, units: um, RAS). "
                "One row per unique OpticalFiber. The localized_entity column references the first "
                "FiberPhotometryTable row index associated with each fiber, since multiple rows "
                "(e.g., different excitation wavelengths) can share the same physical fiber."
            ),
            target=fiber_photometry_table,
            space=ibl_space,
            method="TODO: IBL histology / atlas registration pipeline for fiber photometry",
        )

        # --- 7. Create AnatomicalCoordinatesTable for Allen CCFv3 space ---
        ccf_table = AnatomicalCoordinatesTable(
            name="AnatomicalCoordinatesCCFv3OpticalFibers",
            description=(
                "Fiber tip positions in the Allen CCF v3 coordinate system (units: um). "
                "One row per unique OpticalFiber. The localized_entity column references the first "
                "FiberPhotometryTable row index associated with each fiber, since multiple rows "
                "(e.g., different excitation wavelengths) can share the same physical fiber."
            ),
            target=fiber_photometry_table,
            space=ccf_space,
            method="TODO: IBL histology / atlas registration pipeline for fiber photometry",
        )

        # --- 8. Populate tables: one row per unique OpticalFiber ---
        placeholder_coord = float("nan")  # TODO: replace with actual fiber tip coordinates
        placeholder_region = "TODO"  # TODO: replace with actual brain region acronym

        for fiber_name, first_row_index in fiber_name_to_first_row_index.items():
            # TODO: load actual x, y, z coordinates and brain region for fiber_name
            ibl_table.add_row(
                localized_entity=first_row_index,
                x=placeholder_coord,
                y=placeholder_coord,
                z=placeholder_coord,
                brain_region=placeholder_region,
            )
            ccf_table.add_row(
                localized_entity=first_row_index,
                x=placeholder_coord,
                y=placeholder_coord,
                z=placeholder_coord,
                brain_region=placeholder_region,
            )

        # --- 9. Add both tables to the Localization container ---
        localization.add_anatomical_coordinates_tables([ibl_table, ccf_table])
