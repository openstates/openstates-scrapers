BASE_URL = 'http://www.leg.state.co.us'

def year_from_session(session):
    return int(session.split()[0])

