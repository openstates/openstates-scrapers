def get_year_slug(jurisdiction, session):
    details = next(
        each for each in jurisdiction.legislative_sessions
        if each['identifier'] == session
    )
    try:
        session_id = details['extras']['site_id']
    except KeyError:
        session_id = session[5:]

    return session_id
