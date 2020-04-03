import pytz


def index_legislators(scraper, session_key):
    """
    Get the full name of legislators. The membership API only returns a "LegislatorCode".
    This will cross-reference the name.
    """
    legislators_response = scraper.api_client.get("legislators", session=session_key)

    legislators = {}
    for leg in legislators_response:
        legislators[leg["LegislatorCode"]] = "{} {}".format(
            leg["FirstName"], leg["LastName"]
        )

    return legislators


def get_timezone():
    return pytz.timezone("US/Pacific")


SESSION_KEYS = {
    "2017 Regular Session": "2017R1",
    "2018 Regular Session": "2018R1",
    "2018 Special Session": "2018S1",
    "2019 Regular Session": "2019R1",
    "2020 Regular Session": "2020R1",
}
