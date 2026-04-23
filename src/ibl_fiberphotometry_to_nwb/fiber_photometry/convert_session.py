"""Primary script to run to convert an entire session for of data using the NWBConverter."""

import time
from pathlib import Path

from ibl_to_nwb.datainterfaces import (
    BrainwideMapTrialsInterface,
    IblPoseEstimationInterface,
    LickInterface,
    PassiveIntervalsInterface,
    PassiveReplayStimInterface,
    PupilTrackingInterface,
    RawVideoInterface,
    RoiMotionEnergyInterface,
    SessionEpochsInterface,
)
from ndx_ibl import IblSubject
from neuroconv.utils import dict_deep_update, load_dict_from_file
from one.api import ONE
from pynwb import NWBFile

from ibl_fiberphotometry_to_nwb.fiber_photometry import FiberPhotometryNWBConverter
from ibl_fiberphotometry_to_nwb.fiber_photometry.datainterfaces import (
    FiberPhotometryInterface,
    FiberPhotometryWheelKinematicsInterface,
    FiberPhotometryWheelMovementsInterface,
    FiberPhotometryWheelPositionInterface,
    OpticalFibersAnatomicalLocalizationInterface,
)
from ibl_fiberphotometry_to_nwb.fiber_photometry.utils import (
    get_available_tasks,
    sanitize_subject_id_for_dandi,
)


def session_to_nwb(
    eid: str,
    one: ONE,
    output_path: Path,
    stub_test: bool = False,
    append_on_disk_nwbfile: bool = False,
    verbose: bool = True,
) -> dict:
    """Convert IBL fiber-photometry session to NWB.

    Parameters
    ----------
    eid : str
        Experiment ID (session UUID)
    one : ONE
        ONE API instance
    stub_test : bool, optional
        If True, creates minimal NWB for testing without downloading large files.
        In stub mode, spike properties (spike_amplitudes, spike_distances_from_probe_tip)
        are automatically skipped to reduce memory usage.
    output_path : Path, optional
        Base output directory for NWB files.
    append_on_disk_nwbfile: bool, optional
        If True, append to an existing on-disk NWB file instead of creating a new one.
    Returns
    -------
    dict
        Conversion result information including NWB file path and timing
    """
    if verbose:
        print(f"Starting conversion for session {eid}...")
    start_time = time.time()

    # Setup paths
    session_info = one.alyx.rest("sessions", "read", id=eid)
    subject_nickname = session_info.get("subject")
    if isinstance(subject_nickname, dict):
        subject_nickname = subject_nickname.get("nickname") or subject_nickname.get("name")
    if not subject_nickname:
        subject_nickname = "unknown"

    # Sanitize subject nickname for DANDI compliance (replace underscores with hyphens)
    subject_id_for_filenames = sanitize_subject_id_for_dandi(subject_nickname)

    # New structure: nwbfiles/{full|stub}/sub-{subject}/*.nwb
    conversion_mode = "stub" if stub_test else "full"
    output_dir = output_path / conversion_mode / f"sub-{subject_id_for_filenames}"
    output_dir.mkdir(parents=True, exist_ok=True)
    nwbfile_path = output_dir / f"sub-{subject_id_for_filenames}_ses-{eid}_behavior+ophys.nwb"

    # ========================================================================
    # STEP 1: Define data interfaces
    # ========================================================================

    if verbose:
        print(f"Creating data interfaces...")
    interface_creation_start = time.time()

    data_interfaces = dict()
    conversion_options = dict()
    interface_kwargs = dict(one=one, session=eid)

    # Fiber Photometry data
    data_interfaces["FiberPhotometry"] = FiberPhotometryInterface(**interface_kwargs)
    conversion_options.update({"FiberPhotometry": dict(stub_test=stub_test)})

    # Anatomical Localization of OpticalFibers
    data_interfaces["OpticalFibersAnatomicalLocalizationInterface"] = OpticalFibersAnatomicalLocalizationInterface(
        **interface_kwargs
    )
    conversion_options.update({"OpticalFibersAnatomicalLocalizationInterface": dict()})

    # Behavioral data
    data_interfaces["BrainwideMapTrials"] = BrainwideMapTrialsInterface(**interface_kwargs)
    conversion_options.update({"BrainwideMapTrials": dict(stub_test=stub_test, stub_trials=10)})

    # Wheel data - add each interface if its data is available
    available_tasks = get_available_tasks(**interface_kwargs)
    for task in available_tasks:
        if FiberPhotometryWheelPositionInterface.check_availability(one, eid, task=task)["available"]:
            data_interfaces[f"{task.replace('task_', 'Task')}WheelPosition"] = FiberPhotometryWheelPositionInterface(
                **interface_kwargs, task=task
            )
            conversion_options.update({f"{task.replace('task_', 'Task')}WheelPosition": dict(stub_test=stub_test)})
        if FiberPhotometryWheelKinematicsInterface.check_availability(one, eid, task=task)["available"]:
            data_interfaces[f"{task.replace('task_', 'Task')}WheelKinematics"] = (
                FiberPhotometryWheelKinematicsInterface(**interface_kwargs, task=task)
            )
            conversion_options.update({f"{task.replace('task_', 'Task')}WheelKinematics": dict(stub_test=stub_test)})
        if FiberPhotometryWheelMovementsInterface.check_availability(one, eid, task=task)["available"]:
            data_interfaces[f"{task.replace('task_', 'Task')}WheelMovements"] = FiberPhotometryWheelMovementsInterface(
                **interface_kwargs, task=task
            )
            conversion_options.update({f"{task.replace('task_', 'Task')}WheelMovements": dict(stub_test=stub_test)})

    # Session epochs (high-level task vs passive phases)
    if SessionEpochsInterface.check_availability(one, eid)["available"]:
        data_interfaces["SessionEpochs"] = SessionEpochsInterface(**interface_kwargs)

    # Passive period data - add each interface if its data is available
    if PassiveIntervalsInterface.check_availability(one, eid)["available"]:
        data_interfaces["PassiveIntervals"] = PassiveIntervalsInterface(**interface_kwargs)

    # NOTE: PassiveRFMInterface is temporarily disabled due to data quality issues - waiting for upstream fix
    # if PassiveRFMInterface.check_availability(one, eid)["available"]:
    #     data_interfaces["PassiveRFM"] = PassiveRFMInterface(**interface_kwargs)

    if PassiveReplayStimInterface.check_availability(one, eid)["available"]:
        data_interfaces["PassiveReplayStim"] = PassiveReplayStimInterface(**interface_kwargs)

    # Licks - optional interface
    if LickInterface.check_availability(one, eid)["available"]:
        data_interfaces["Licks"] = LickInterface(**interface_kwargs)

    # Camera-based interfaces (pose estimation, pupil tracking, ROI motion energy)
    # Check availability per camera since not all sessions have all cameras
    for camera_view in ["left", "right", "body"]:
        camera_name = f"{camera_view}Camera"

        # Pose estimation - check_availability handles Lightning Pose → DLC fallback
        pose_availability = IblPoseEstimationInterface.check_availability(one, eid, camera_name=camera_name)
        if pose_availability["available"]:
            # Determine tracker from which alternative was found
            alternative = pose_availability.get("alternative_used", "lightning_pose")
            tracker = "lightningPose" if alternative == "lightning_pose" else "dlc"
            data_interfaces[f"{camera_name}PoseEstimation"] = IblPoseEstimationInterface(
                camera_name=camera_name, tracker=tracker, **interface_kwargs
            )

        # Pupil tracking - only for left/right cameras (body camera doesn't capture eyes)
        if camera_view in ["left", "right"]:
            if PupilTrackingInterface.check_availability(one, eid, camera_name=camera_name)["available"]:
                data_interfaces[f"{camera_name}PupilTracking"] = PupilTrackingInterface(
                    camera_name=camera_name, **interface_kwargs
                )

        # ROI motion energy
        if RoiMotionEnergyInterface.check_availability(one, eid, camera_name=camera_name)["available"]:
            data_interfaces[f"{camera_name}RoiMotionEnergy"] = RoiMotionEnergyInterface(
                camera_name=camera_name, **interface_kwargs
            )

    # Add raw behavioral video
    # Add video interfaces for cameras that have timestamps
    # Check all camera types (left, right, body)
    for camera_view in ["left", "right", "body"]:
        camera_name = f"{camera_view}Camera"
        camera_times_pattern = f"*{camera_view}Camera.times*"
        video_filename = f"raw_video_data/_iblrig_{camera_view}Camera.raw.mp4"

        # Check if camera has timestamps (required for video interface)
        has_timestamps = bool(one.list_datasets(eid=eid, filename=camera_times_pattern))
        if not has_timestamps:
            continue

        # Check if video dataset exists
        has_video = bool(one.list_datasets(eid=eid, filename=video_filename))
        if not has_video:
            if verbose:
                print(f"No video file found for {camera_view}Camera - skipping")
            continue

        # In stub mode, check if video is already in cache (avoid triggering downloads)
        if stub_test:
            # Check cache without downloading - construct expected path from eid2path
            session_path = one.eid2path(eid)
            if session_path is None:
                # Session path not in cache, skip video
                if verbose:
                    print(f"✗ Stub mode: {camera_view}Camera video not in cache - skipping to avoid download")
                continue

            expected_video_path = session_path / video_filename
            video_in_cache = expected_video_path.exists()

            if not video_in_cache:
                if verbose:
                    print(f"✗ Stub mode: {camera_view}Camera video not in cache - skipping to avoid download")
                continue

            if verbose:
                print(f"✓ Stub mode: Including {camera_view}Camera video (already in cache)")
        else:
            if verbose:
                print(f"Adding {camera_view}Camera video interface")

        # Add video interface
        data_interfaces[f"{camera_name}RawVideoInterface"] = RawVideoInterface(
            **interface_kwargs,
            nwbfiles_folder_path=output_path / conversion_mode,  # Video files should be organized alongside NWB files
            subject_id=subject_id_for_filenames,
            camera_name=camera_view,
        )

    interface_creation_time = time.time() - interface_creation_start
    if verbose:
        print(f"Data interfaces created in {interface_creation_time:.2f}s")

    # ========================================================================
    # STEP 2: Create converter
    # ========================================================================
    converter = FiberPhotometryNWBConverter(one=one, session=eid, data_interfaces=data_interfaces)

    # ========================================================================
    # STEP 3: Get metadata
    # ========================================================================
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "_metadata" / "general_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # ========================================================================
    # STEP 4: Write NWB file
    # ========================================================================
    overwrite = False
    if nwbfile_path.exists() and not append_on_disk_nwbfile:
        overwrite = True

    subject_metadata_for_ndx = metadata.pop("Subject")
    ibl_subject = IblSubject(**subject_metadata_for_ndx)

    # TODO: Solve this for append_on_disk_nwbfile=True case
    nwbfile = NWBFile(**metadata["NWBFile"])
    nwbfile.subject = ibl_subject

    if verbose:
        print(f"Writing to NWB '{nwbfile_path}' ...")
    write_start = time.time()

    converter.run_conversion(
        metadata=metadata,
        nwbfile=nwbfile,
        nwbfile_path=nwbfile_path,
        conversion_options=conversion_options,
        append_on_disk_nwbfile=append_on_disk_nwbfile,
        overwrite=overwrite,
    )

    write_time = time.time() - write_start

    # Get NWB file size
    nwb_size_bytes = nwbfile_path.stat().st_size
    nwb_size_gb = nwb_size_bytes / (1024**3)

    if verbose:
        total_time_seconds = time.time() - start_time
        total_time_hours = total_time_seconds / 3600
        print(f"NWB file written in {write_time:.2f}s")
        print(f"NWB file size: {nwb_size_gb:.2f} GB ({nwb_size_bytes:,} bytes)")
        print(f"Write speed: {nwb_size_gb / (write_time / 3600):.2f} GB/hour")
        print(f"conversion total time: {total_time_seconds:.2f}s")
        print(f"conversion total time: {total_time_hours:.2f} hours")
        print(f"conversion completed: {nwbfile_path}")
        print(f"NWB saved to: {nwbfile_path}")

    return {
        "nwbfile_path": nwbfile_path,
        "nwb_size_bytes": nwb_size_bytes,
        "nwb_size_gb": nwb_size_gb,
        "write_time": write_time,
    }


if __name__ == "__main__":

    # Parameters for conversion
    eid = "fd688232-0dd8-400b-aa66-dc23460d9f98"
    stub_test = False  # Set to True for a quick test conversion with limited data
    start_time = time.time()
    session_to_nwb(
        eid=eid,
        one=ONE(),  # base_url="https://alyx.internationalbrainlab.org"
        stub_test=stub_test,
        output_path=Path("E:/IBL-fiberphotometry-nwbfiles"),
        append_on_disk_nwbfile=False,
        verbose=True,
    )
    print(f"Conversion completed in {time.time() - start_time:.2f} seconds.")
