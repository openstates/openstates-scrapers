def get_year_slug(jurisdiction, session):
    details = next(
        each for each in jurisdiction.legislative_sessions
        if each['identifier'] == session
    )
    return details['site_id'] if 'site_id' in details else session[5:]
