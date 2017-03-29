import pytz


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


def get_timezone():
    return pytz.timezone("US/Pacific")
