def get_session_slug(jurisdiction, session):
    session_details = next(
        item
        for item in jurisdiction.legislative_sessions
        if item["identifier"] == session
    )
    return session_details["extras"]["session_slug"]
