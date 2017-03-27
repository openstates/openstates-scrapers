def clean_space(str):
    new_str = ' '.join(str.split())
    return new_str

def base_url():
    return 'http://www.leg.state.or.us/'

def bills_url():
    return 'http://www.leg.state.or.us/bills_laws/billsinfo.htm'


def year_from_session(session):
    return int(session.split()[0])


def index_legislators(scraper):
    """
    Get the full name of legislators. The membership API only returns a "LegislatorCode".
    This will cross-reference the name.
    """
    legislators_response = scraper.api_client.get('legislators', session=scraper.session)

    legislators = {}
    for leg in legislators_response:
        legislators[leg['LegislatorCode']] = '{} {}'.format(leg['FirstName'], leg['LastName'])

    return legislators
