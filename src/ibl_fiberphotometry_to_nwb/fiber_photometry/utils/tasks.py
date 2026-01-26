from one.api import ONE


def get_available_tasks(one: ONE, session: str) -> list[str]:
    """Get available tasks for a given session."""

    collections = one.list_collections(
        eid=session,
        filename="*alf/task*",
    )
    return [collection.split("/")[1] for collection in collections]
