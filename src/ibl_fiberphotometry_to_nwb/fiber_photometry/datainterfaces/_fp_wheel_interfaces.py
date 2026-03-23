import logging
from typing import Optional

from ibl_to_nwb.datainterfaces import (
    WheelKinematicsInterface,
    WheelMovementsInterface,
    WheelPositionInterface,
)
from one.api import ONE

from ibl_fiberphotometry_to_nwb.fiber_photometry.utils import get_available_tasks


class FiberPhotometryWheelKinematicsInterface(WheelKinematicsInterface):
    """
    Data interface for wheel kinematics data in IBL fiber photometry sessions.

    Extends :class:`ibl_to_nwb.datainterfaces.WheelKinematicsInterface` to
    support task-specific ALF collections (e.g. ``alf/task_00/``) used in
    fiber photometry sessions where multiple tasks may be recorded per session.

    Derives wheel velocity and acceleration from the raw wheel position and
    timestamp files. Uses revision ``"2025-05-06"`` (the BWM standard).

    Required files (either the ``standard`` or the task-specific option):

    - ``alf/_ibl_wheel.position.npy`` / ``alf/{task}/_ibl_wheel.position.npy``
    - ``alf/_ibl_wheel.timestamps.npy`` / ``alf/{task}/_ibl_wheel.timestamps.npy``
    """

    # Wheel data uses BWM standard revision
    REVISION: str | None = "2025-05-06"

    def __init__(self, one: ONE, session: str, task: str = "task_00"):
        """
        Parameters
        ----------
        one : ONE
            ONE API instance connected to Alyx.
        session : str
            Session UUID (experiment ID, ``eid``).
        task : str, optional
            Task name to load wheel data from (e.g. ``"task_00"``),
            by default ``"task_00"``. Must be one of the tasks returned by
            :func:`~ibl_fiberphotometry_to_nwb.fiber_photometry.utils.get_available_tasks`.

        Raises
        ------
        ValueError
            If ``task`` is not found among the available tasks for this session.
        """
        self.one = one
        self.session = session
        self.revision = self.REVISION
        # Check if task exists
        tasks = get_available_tasks(one, session)
        if task not in tasks:
            raise ValueError(f"Task '{task}' not found for session '{session}'. " f"Available tasks: {tasks}.'")
        self.task = task

    @classmethod
    def get_data_requirements(cls, task: str) -> dict:
        """
        Declare exact data files required for wheel kinematics.

        Supports two options: a ``"standard"`` collection (``alf/``) and a
        task-specific collection (``alf/{task}/``). Either complete option
        satisfies the availability check.

        Parameters
        ----------
        task : str
            Task name used to build the task-specific file paths.

        Returns
        -------
        dict
            Data requirements mapping with ``exact_files_options``.
        """
        return {
            "exact_files_options": {
                "standard": [
                    f"alf/_ibl_wheel.position.npy",
                    f"alf/_ibl_wheel.timestamps.npy",
                ],
                task: [
                    f"alf/{task}/_ibl_wheel.position.npy",
                    f"alf/{task}/_ibl_wheel.timestamps.npy",
                ],
            },
        }

    # WARNING: The following method cannot be staticmethod due to self.task usage
    def get_load_object_kwargs(self) -> dict:
        """Return kwargs for one.load_object() call."""
        return {"obj": "wheel", "collection": f"alf/{self.task}"}

    @classmethod
    def check_availability(cls, one: ONE, eid: str, logger: Optional[logging.Logger] = None, **kwargs) -> dict:
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
        logger : logging.Logger, optional
            Logger for progress/warning messages
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
        quality_result = cls.check_quality(one=one, eid=eid, logger=logger, **kwargs)

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


class FiberPhotometryWheelMovementsInterface(WheelMovementsInterface):
    """
    Data interface for wheel movement segmentation data in IBL fiber photometry sessions.

    Extends :class:`ibl_to_nwb.datainterfaces.WheelMovementsInterface` to
    support task-specific ALF collections (e.g. ``alf/task_00/``) used in
    fiber photometry sessions where multiple tasks may be recorded per session.

    Loads pre-computed movement intervals and peak amplitudes from the ALF
    ``wheelMoves`` object. Uses revision ``"2025-05-06"`` (the BWM standard).

    Required files (either the ``standard`` or the task-specific option):

    - ``alf/_ibl_wheelMoves.intervals.npy`` / ``alf/{task}/_ibl_wheelMoves.intervals.npy``
    - ``alf/_ibl_wheelMoves.peakAmplitude.npy`` / ``alf/{task}/_ibl_wheelMoves.peakAmplitude.npy``
    """

    # Wheel data uses BWM standard revision
    REVISION: str | None = "2025-05-06"

    def __init__(self, one: ONE, session: str, task: str = "task_00"):
        """
        Parameters
        ----------
        one : ONE
            ONE API instance connected to Alyx.
        session : str
            Session UUID (experiment ID, ``eid``).
        task : str, optional
            Task name to load wheel movement data from (e.g. ``"task_00"``),
            by default ``"task_00"``. Issues a warning if the task is not found
            (does not raise, to allow graceful degradation in batch conversions).
        """
        self.one = one
        self.session = session
        self.revision = self.REVISION
        # Check if task exists
        tasks = get_available_tasks(one, session)
        if task not in tasks:
            logging.warning(f"Task '{task}' not found for session '{session}'. " f"Available tasks: {tasks}.'")
        self.task = task

    @classmethod
    def get_data_requirements(cls, task: str) -> dict:
        """
        Declare exact data files required for wheel movement segmentation.

        Supports two options: a ``"standard"`` collection (``alf/``) and a
        task-specific collection (``alf/{task}/``). Either complete option
        satisfies the availability check.

        Parameters
        ----------
        task : str
            Task name used to build the task-specific file paths.

        Returns
        -------
        dict
            Data requirements mapping with ``exact_files_options``.
        """
        return {
            "exact_files_options": {
                "standard": [
                    f"alf/_ibl_wheelMoves.intervals.npy",
                    f"alf/_ibl_wheelMoves.peakAmplitude.npy",
                ],
                task: [
                    f"alf/{task}/_ibl_wheelMoves.intervals.npy",
                    f"alf/{task}/_ibl_wheelMoves.peakAmplitude.npy",
                ],
            },
        }

    # WARNING: The following method cannot be staticmethod due to self.task usage
    def get_load_object_kwargs(self) -> dict:
        """Return kwargs for one.load_object() call."""
        return {"obj": "wheelMoves", "collection": f"alf/{self.task}"}

    @classmethod
    def check_availability(cls, one: ONE, eid: str, logger: Optional[logging.Logger] = None, **kwargs) -> dict:
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
        logger : logging.Logger, optional
            Logger for progress/warning messages
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
        quality_result = cls.check_quality(one=one, eid=eid, logger=logger, **kwargs)

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


class FiberPhotometryWheelPositionInterface(WheelPositionInterface):
    """
    Data interface for raw wheel position data in IBL fiber photometry sessions.

    Extends :class:`ibl_to_nwb.datainterfaces.WheelPositionInterface` to
    support task-specific ALF collections (e.g. ``alf/task_00/``) used in
    fiber photometry sessions where multiple tasks may be recorded per session.

    Loads the raw wheel position and timestamp arrays from the ALF ``wheel``
    object. Uses revision ``"2025-05-06"`` (the BWM standard).

    Required files (either the ``standard`` or the task-specific option):

    - ``alf/_ibl_wheel.position.npy`` / ``alf/{task}/_ibl_wheel.position.npy``
    - ``alf/_ibl_wheel.timestamps.npy`` / ``alf/{task}/_ibl_wheel.timestamps.npy``
    """

    # Wheel data uses BWM standard revision
    REVISION: str | None = "2025-05-06"

    def __init__(self, one: ONE, session: str, task: str = "task_00"):
        """
        Parameters
        ----------
        one : ONE
            ONE API instance connected to Alyx.
        session : str
            Session UUID (experiment ID, ``eid``).
        task : str, optional
            Task name to load wheel position data from (e.g. ``"task_00"``),
            by default ``"task_00"``. Issues a warning if the task is not found
            (does not raise, to allow graceful degradation in batch conversions).
        """
        self.one = one
        self.session = session
        self.revision = self.REVISION
        # Check if task exists
        tasks = get_available_tasks(one, session)
        if task not in tasks:
            logging.warning(f"Task '{task}' not found for session '{session}'. " f"Available tasks: {tasks}.'")
        self.task = task

    @classmethod
    def get_data_requirements(cls, task: str) -> dict:
        """
        Declare exact data files required for wheel position.

        Supports two options: a ``"standard"`` collection (``alf/``) and a
        task-specific collection (``alf/{task}/``). Either complete option
        satisfies the availability check.

        Parameters
        ----------
        task : str
            Task name used to build the task-specific file paths.

        Returns
        -------
        dict
            Data requirements mapping with ``exact_files_options``.
        """
        return {
            "exact_files_options": {
                "standard": [
                    f"alf/_ibl_wheel.position.npy",
                    f"alf/_ibl_wheel.timestamps.npy",
                ],
                task: [
                    f"alf/{task}/_ibl_wheel.position.npy",
                    f"alf/{task}/_ibl_wheel.timestamps.npy",
                ],
            },
        }

    # WARNING: The following method cannot be staticmethod due to self.task usage
    def get_load_object_kwargs(self) -> dict:
        """Return kwargs for one.load_object() call."""
        return {"obj": "wheel", "collection": f"alf/{self.task}"}

    @classmethod
    def check_availability(cls, one: ONE, eid: str, logger: Optional[logging.Logger] = None, **kwargs) -> dict:
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
        logger : logging.Logger, optional
            Logger for progress/warning messages
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
        quality_result = cls.check_quality(one=one, eid=eid, logger=logger, **kwargs)

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
