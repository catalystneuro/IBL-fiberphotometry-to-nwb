"""Primary script to run to convert an entire session for of data using the NWBConverter."""

import time
from pathlib import Path

from ibl_to_nwb.datainterfaces import RawVideoInterface
from ndx_ibl import IblMetadata, IblSubject
from neuroconv.utils import dict_deep_update, load_dict_from_file
from one.api import ONE
from pynwb import NWBFile

from ibl_fiberphotometry_to_nwb.fiber_photometry import RawFiberPhotometryNWBConverter
from ibl_fiberphotometry_to_nwb.fiber_photometry.utils import (
    sanitize_subject_id_for_dandi,
)


def convert_raw_session(
    eid: str,
    one: ONE,
    output_path: Path,
    stub_test: bool = False,
    append_on_disk_nwbfile: bool = False,
    verbose: bool = True,
) -> dict:
    """Convert IBL raw session to NWB.

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
        print(f"Starting RAW conversion for session {eid}...")
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
    nwbfile_path = output_dir / f"sub-{subject_id_for_filenames}_ses-{eid}_desc-raw_behavior+ophys.nwb"

    # ========================================================================
    # STEP 1: Define data interfaces
    # ========================================================================

    if verbose:
        print(f"Creating data interfaces...")
    interface_creation_start = time.time()

    data_interfaces = dict()
    conversion_options = dict()
    interface_kwargs = dict(one=one, session=eid)

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
    converter = RawFiberPhotometryNWBConverter(one=one, session=eid, data_interfaces=data_interfaces)

    # ========================================================================
    # STEP 3: Get metadata
    # ========================================================================
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent.parent / "_metadata" / "general_metadata.yaml"
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
        print(f"RAW NWB file size: {nwb_size_gb:.2f} GB ({nwb_size_bytes:,} bytes)")
        print(f"Write speed: {nwb_size_gb / (write_time / 3600):.2f} GB/hour")
        print(f"RAW conversion total time: {total_time_seconds:.2f}s")
        print(f"RAW conversion total time: {total_time_hours:.2f} hours")
        print(f"RAW conversion completed: {nwbfile_path}")
        print(f"RAW NWB saved to: {nwbfile_path}")

    return {
        "nwbfile_path": nwbfile_path,
        "nwb_size_bytes": nwb_size_bytes,
        "nwb_size_gb": nwb_size_gb,
        "write_time": write_time,
    }


if __name__ == "__main__":
    # Example usage
    convert_raw_session(
        eid="fd688232-0dd8-400b-aa66-dc23460d9f98",
        one=ONE(),  # base_url="https://alyx.internationalbrainlab.org"
        stub_test=True,
        output_path=Path("E:/IBL-fiberphotometry-nwbfiles"),
        append_on_disk_nwbfile=False,
        verbose=True,
    )
