from datetime import datetime
from pathlib import Path

from dateutil import tz
from neuroconv import ConverterPipe
from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import dict_deep_update, load_dict_from_file
from one.api import ONE
from typing_extensions import Self

from ibl_fiberphotometry_to_nwb.fiber_photometry.utils import (
    get_ibl_subject_metadata,
    get_protocol_type_and_description,
)


class IblConverter(ConverterPipe):
    """
    Base NWB converter for IBL data that enriches metadata from the ONE API.

    Extends :class:`neuroconv.ConverterPipe` to automatically populate NWB
    metadata (session start time, lab, institution, task protocol description,
    and subject information) by querying Alyx via the ONE API.

    Subclass this converter for specific IBL recording modalities and override
    :meth:`get_metadata` to merge modality-specific metadata on top of the
    session-level fields populated here.
    """

    def __init__(
        self,
        one: ONE,
        session: str,
        data_interfaces: list[BaseDataInterface] | dict[str, BaseDataInterface],
        verbose=False,
    ) -> Self:
        """
        Parameters
        ----------
        one : ONE
            ONE API instance connected to Alyx.
        session : str
            Session UUID (experiment ID, ``eid``).
        data_interfaces : list[BaseDataInterface] | dict[str, BaseDataInterface]
            Data interfaces to include in the conversion pipeline.
        verbose : bool, optional
            Whether to print verbose output during conversion, by default False.
        """
        self.one = one
        self.session = session
        super().__init__(data_interfaces=data_interfaces, verbose=verbose)

    def get_metadata_schema(self) -> dict:
        """
        Return the metadata schema with relaxed validation.

        Enables ``additionalProperties`` on the top-level schema and on the
        ``Subject`` block so that IBL-specific extensions (e.g. ``IblSubject``)
        can pass extra fields without validation errors.

        Returns
        -------
        dict
            JSON-Schema compatible metadata schema dictionary.
        """
        metadata_schema = super().get_metadata_schema()
        metadata_schema["additionalProperties"] = True
        metadata_schema["properties"]["Subject"]["additionalProperties"] = True

        return metadata_schema

    def get_metadata(self) -> dict:
        """
        Aggregate metadata from data interfaces and the ONE / Alyx API.

        Fetches session and lab records from Alyx to populate:

        - ``NWBFile.session_start_time`` — timezone-aware datetime derived from
          the Alyx session record and the lab's configured timezone.
        - ``NWBFile.session_id`` — the session UUID (``eid``).
        - ``NWBFile.lab`` and ``NWBFile.institution`` — from the Alyx lab record.
        - ``NWBFile.protocol`` and ``NWBFile.session_description`` — derived from
          the task protocol string via :data:`PROTOCOLS_MAPPING`.
        - ``Subject`` block — species, date of birth, sex, weight, and other
          fields from :func:`~ibl_fiberphotometry_to_nwb.fiber_photometry.utils.get_ibl_subject_metadata`.

        Returns
        -------
        dict
            Merged metadata dictionary ready for NWB file creation.
        """
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
            task_protocol = session_metadata["task_protocol"]
            metadata["NWBFile"]["protocol"] = task_protocol
            session_description = f"The task protocol(s) performed in this experimental session:\n"
            # Determine protocol type and description from the mapping
            protocols = task_protocol.split("/")  # In case there are multiple protocols listed, separated by /
            for i, protocol in enumerate(protocols):
                protocol_type, protocol_description = get_protocol_type_and_description(protocol)
                if protocol_type is not None:
                    session_description = session_description + f"{i+1}. {protocol_description}\n"
            metadata["NWBFile"]["session_description"] = session_description
        # Setting publication and experiment description at project-specific converter level
        subject_metadata_block = get_ibl_subject_metadata(
            one=self.one, session_metadata=session_metadata, tzinfo=tzinfo
        )
        subject_metadata_block["weight"] = str(subject_metadata_block["weight"])  # Ensure weight is a string
        metadata["Subject"].update(subject_metadata_block)

        return metadata


class FiberPhotometryNWBConverter(IblConverter):
    """
    Primary NWB converter for IBL fiber photometry datasets.

    Combines all data interfaces for a fiber photometry session (fiber
    photometry signals, anatomical localization, wheel, behavioral, and
    camera data) and merges session-level metadata from the ONE API with
    experiment-level metadata from ``general_metadata.yaml``.
    """

    def get_metadata(self) -> dict:
        """
        Aggregate session metadata and merge with experiment-level metadata.

        Calls the parent :meth:`IblConverter.get_metadata` to populate session,
        lab, subject, and protocol fields, then deep-merges with the contents
        of ``_metadata/general_metadata.yaml`` which provides NWB keywords and
        the experiment description common to all sessions in this dataset.

        Returns
        -------
        dict
            Fully merged metadata dictionary for NWB file creation.
        """
        metadata = super().get_metadata()

        fiber_photometry_metadata_file_path = Path(__file__).parent / "_metadata" / "general_metadata.yaml"
        experiment_metadata = load_dict_from_file(file_path=fiber_photometry_metadata_file_path)
        metadata = dict_deep_update(metadata, experiment_metadata)

        return metadata
