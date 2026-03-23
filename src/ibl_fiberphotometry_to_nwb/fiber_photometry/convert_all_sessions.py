"""Script to convert all sessions in a dataset using session_to_nwb."""

import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import List, Union

from tqdm import tqdm

from ibl_fiberphotometry_to_nwb.fiber_photometry.convert_session import session_to_nwb


def dataset_to_nwb(
    *,
    eids: List[str],
    output_dir_path: Union[str, Path],
    stub_test: bool = False,
    max_workers: int = 1,
    verbose: bool = True,
):
    """Convert a list of sessions to NWB.

    Parameters
    ----------
    eids : List[str]
        List of experiment IDs (session UUIDs) to convert.
    output_dir_path : Union[str, Path]
        The path to the directory where the NWB files will be saved.
    stub_test : bool, optional
        If True, run a lightweight test conversion with limited data, by default False.
    max_workers : int, optional
        The number of workers to use for parallel processing, by default 1.
    verbose : bool, optional
        Whether to print verbose output, by default True.
    """
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    futures = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for eid in eids:
            session_to_nwb_kwargs = dict(
                eid=eid,
                output_path=output_dir_path,
                stub_test=stub_test,
                verbose=verbose,
            )
            exception_file_path = output_dir_path / f"ERROR_{eid}_{mode}.txt"
            futures.append(
                executor.submit(
                    safe_session_to_nwb,
                    session_to_nwb_kwargs=session_to_nwb_kwargs,
                    exception_file_path=exception_file_path,
                )
            )
        for _ in tqdm(as_completed(futures), total=len(futures)):
            pass


def safe_session_to_nwb(*, session_to_nwb_kwargs: dict, exception_file_path: Union[Path, str]):
    """Convert a session to NWB while recording any errors to exception_file_path.

    Parameters
    ----------
    session_to_nwb_kwargs : dict
        The keyword arguments for session_to_nwb.
    exception_file_path : Union[Path, str]
        The path to the file where exception messages will be saved.
    """
    exception_file_path = Path(exception_file_path)
    try:
        session_to_nwb(**session_to_nwb_kwargs)
    except Exception:
        with open(exception_file_path, mode="w") as f:
            f.write(f"session_to_nwb_kwargs:\n{pformat(session_to_nwb_kwargs)}\n\n")
            f.write(traceback.format_exc())


if __name__ == "__main__":

    eids = [
        "fd688232-0dd8-400b-aa66-dc23460d9f98",
    ]
    output_dir_path = Path("E:/IBL-fiberphotometry-nwbfiles")
    stub_test = False
    max_workers = 1

    for mode in ("processed", "raw"):
        dataset_to_nwb(
            eids=eids,
            output_dir_path=output_dir_path,
            stub_test=stub_test,
            max_workers=max_workers,
            verbose=True,
        )
