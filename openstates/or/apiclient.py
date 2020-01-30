import requests


class OregonLegislatorODataClient(object):
    """
    Client for interfacing with Oregon Legislator OData API.
    https://www.oregonlegislature.gov/citizen_engagement/Pages/data.aspx
    """

    root = "https://api.oregonlegislature.gov/odata/odataservice.svc/"
    resources = dict(
        sessions="LegislativeSessions",
        legislators="LegislativeSessions('{session}')/Legislators",
        legislator="Legislators(LegislatorCode='{legislator_code}',SessionKey='{session}')",
        committees="LegislativeSessions('{session}')/Committees",
        committee_meetings="CommitteeMeetings?$filter=(MeetingDate gt datetime'{start_date}')"
        " and (SessionKey eq '{session}')&$expand=CommitteeAgendaItems,CommitteeMeetingDocuments",
        committee_members="Committees(CommitteeCode='{committee}',"
        "SessionKey='{session}')/CommitteeMembers",
        measures="LegislativeSessions('{session}')/Measures"
        "?$expand=MeasureSponsors,MeasureDocuments,MeasureHistoryActions,"
        "CommitteeAgendaItems/CommitteeProposedAmendments",
        votes="LegislativeSessions('{session}')/Measures"
        "?$expand=MeasureHistoryActions/MeasureVotes,CommitteeAgendaItems/CommitteeVotes",
    )

    def _build_url(self, resource_name, **endpoint_format_args):
        endpoint = self.resources[resource_name]
        endpoint = endpoint.format(**endpoint_format_args)

        url = self.root + endpoint
        return url

    def __init__(self, scraper):
        if not scraper:
            scraper = requests.Session()
        self.scraper = scraper

    def all_sessions(self):
        return self.get("sessions")

    def latest_session(self):
        return self.get("sessions")[-1]["SessionKey"]

    def get(
        self,
        resource_name,
        page=None,
        skip=0,
        requests_args=None,
        requests_kwargs=None,
        **url_format_args
    ):
        num_bad_packets_allowed = 10
        url = self._build_url(resource_name, **url_format_args)

        if page:
            url = "{url}&$top={page}&$skip={skip}".format(url=url, page=page, skip=skip)

        requests_args = requests_args or ()
        requests_kwargs = requests_kwargs or {}
        requests_kwargs.update(verify=True)
        headers = requests_kwargs.get("headers", {})
        headers["Accept"] = "application/json"
        requests_kwargs["headers"] = headers

        response = None

        tries = 0
        while response is None and tries < num_bad_packets_allowed:
            try:
                response = self.scraper.get(url, *requests_args, **requests_kwargs)
            except requests.exceptions.RequestException as e:
                err, string = e.args
                print("warn: retry")
                tries += 1
                if tries >= num_bad_packets_allowed:
                    print(err, string)
                    raise RuntimeError("Received too many bad packets from API.")

        response = response.json()["value"]
        if page and len(response) > 0:
            skip += page
            response.extend(
                self.get(
                    resource_name,
                    page,
                    skip,
                    requests_args,
                    requests_kwargs,
                    **url_format_args
                )
            )
        return response
