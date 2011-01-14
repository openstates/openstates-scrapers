BASE_URL = "http://www.capitol.hawaii.gov"

def year_from_session(session):
    return int(session.split()[0].split('-')[0])
