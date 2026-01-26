from datetime import datetime
from pathlib import Path

from dateutil import tz
from neuroconv import ConverterPipe
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import dict_deep_update, load_dict_from_file
from one.api import ONE
from typing_extensions import Self

from ibl_fiberphotometry_to_nwb.fiber_photometry.utils import get_ibl_subject_metadata


class IblConverter(ConverterPipe):

    def __init__(
        self,
        one: ONE,
        session: str,
        data_interfaces: list[BaseDataInterface] | dict[str, BaseDataInterface],
        verbose=False,
    ) -> Self:
        self.one = one
        self.session = session
        super().__init__(data_interfaces=data_interfaces, verbose=verbose)

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        metadata_schema["additionalProperties"] = True
        metadata_schema["properties"]["Subject"]["additionalProperties"] = True

        return metadata_schema

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()  # Aggregates from the interfaces

        (session_metadata,) = self.one.alyx.rest(url="sessions", action="list", id=self.session)
        assert session_metadata["id"] == self.session, "Session metadata ID does not match the requested session ID."
        (lab_metadata,) = self.one.alyx.rest("labs", "list", name=session_metadata["lab"])

        # TODO: include session_metadata['number'] in the extension attributes
        session_start_time = datetime.fromisoformat(session_metadata["start_time"])
        tzinfo = tz.gettz(lab_metadata["timezone"])
        session_start_time = session_start_time.replace(tzinfo=tzinfo)
        metadata["NWBFile"]["session_start_time"] = session_start_time
        metadata["NWBFile"]["session_id"] = session_metadata["id"]
        metadata["NWBFile"]["lab"] = session_metadata["lab"].replace("lab", "").capitalize()
        metadata["NWBFile"]["institution"] = lab_metadata["institution"]
        if session_metadata.get("task_protocol"):
            metadata["NWBFile"]["protocol"] = session_metadata["task_protocol"]
        # Setting publication and experiment description at project-specific converter level
        subject_metadata_block = get_ibl_subject_metadata(
            one=self.one, session_metadata=session_metadata, tzinfo=tzinfo
        )
        subject_metadata_block["weight"] = str(subject_metadata_block["weight"])  # Ensure weight is a string
        metadata["Subject"].update(subject_metadata_block)

        return metadata


class RawFiberPhotometryNWBConverter(IblConverter):
    """Primary conversion class for raw IBL fiber photometry datasets."""

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        fiber_photometry_metadata_file_path = (
            Path(__file__).parent / "_metadata" / "fiber_photometry_general_metadata.yaml"
        )
        experiment_metadata = load_dict_from_file(file_path=fiber_photometry_metadata_file_path)
        metadata = dict_deep_update(metadata, experiment_metadata)

        return metadata


class ProcessedFiberPhotometryNWBConverter(IblConverter):
    """Primary conversion class for processed IBL fiber photometry datasets."""

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        fiber_photometry_metadata_file_path = (
            Path(__file__).parent / "_metadata" / "fiber_photometry_general_metadata.yaml"
        )
        experiment_metadata = load_dict_from_file(file_path=fiber_photometry_metadata_file_path)
        metadata = dict_deep_update(metadata, experiment_metadata)

        return metadata
