from one.api import ONE


def get_available_tasks(one: ONE, session: str) -> list[str]:
    """Get available tasks for a given session."""

    collections = one.list_collections(
        eid=session,
        filename="*alf/task*",
    )
    return [collection.split("/")[1] for collection in collections]


# def get_available_tasks_from_raw_collections(one: ONE, session: str) -> list[str]:
#     """Get available tasks for a given session."""

#     collections = one.list_collections(
#         eid=session,
#         filename="*raw_task_data*",
#     )
#     return [collection.split("_")[-1] for collection in collections]


# if __name__ == "__main__":
#     one = ONE()
#     session = "fd688232-0dd8-400b-aa66-dc23460d9f98"
#     tasks = get_available_tasks_from_alf_collections(one, session)
#     print(f"Available tasks for session {session}: {tasks}")
#     tasks = get_available_tasks_from_raw_collections(one, session)
#     print(f"Available tasks for session {session}: {tasks}")
