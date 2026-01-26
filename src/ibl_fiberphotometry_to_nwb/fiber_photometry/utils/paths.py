"""Path utilities for IBL-to-NWB conversion."""

from pathlib import Path

from one.api import ONE


def setup_paths(
    one: ONE,
    eid: str,
    base_path: Path,
) -> dict:
    """
    Create a structured dictionary of paths for NWB conversion.

    Parameters
    ----------
    one : ONE
        An instance of the ONE API.
    eid : str
        The experiment ID for the session being converted.
    base_path : Path
        The base path for output files.

    Returns
    -------
    dict
        A dictionary containing the following paths:
        - output_folder: Path to store the output NWB files.
        - session_folder: Path to the original session data (ONE cache).
        - mc_imaging_folder: Path to the motion corrected imaging data for this session.
    """
    session_folder = one.eid2path(eid)
    mc_imaging_folder = session_folder / "suite2p"
    if not mc_imaging_folder.exists():
        mc_imaging_folder = session_folder / "suite2"  # correct for typo in folder name
        if not mc_imaging_folder.exists():
            raise FileNotFoundError(f"Motion corrected imaging folder not found at {mc_imaging_folder}")
    # raw_task_data_folder_list = session_folder / "raw_task_data" # raw_task_data_00, 01, ...
    # raw_imaging_data_folder_list = session_folder / "raw_imaging_data" # raw_imaging_data_00, 01, ...
    paths = dict(
        output_folder=base_path / "nwbfiles",
        session_folder=session_folder,
        mc_imaging_folder=mc_imaging_folder,
    )

    # Create directories
    paths["output_folder"].mkdir(exist_ok=True, parents=True)

    return paths


if __name__ == "__main__":
    # Example usage
    one = ONE()
    eid = "5ce2e17e-8471-42d4-8a16-21949710b328"
    base_path = Path("E:\\IBL-data-share\\")
    paths = setup_paths(one, eid, base_path)
    print(paths)
