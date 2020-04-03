from openstates.scrape import Person, Scraper
from .apiclient import OregonLegislatorODataClient
from .utils import SESSION_KEYS


class ORPersonScraper(Scraper):
    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        if not session:
            session = self.latest_session()

        yield from self.scrape_chamber(session)

    def scrape_chamber(self, session):
        session_key = SESSION_KEYS[session]
        legislators_reponse = self.api_client.get("legislators", session=session_key)

        for legislator in legislators_reponse:
            url_name = legislator["WebSiteUrl"].split("/")[-1]
            chamber_name = "house" if legislator["Chamber"] == "H" else "senate"
            img = "https://www.oregonlegislature.gov/{}/MemberPhotos/{}.jpg".format(
                chamber_name, url_name
            )

            party = legislator["Party"]
            if party == "Democrat":
                party = "Democratic"

            person = Person(
                name="{} {}".format(legislator["FirstName"], legislator["LastName"]),
                primary_org={"S": "upper", "H": "lower"}[legislator["Chamber"]],
                party=party,
                district=legislator["DistrictNumber"],
                image=img,
            )
            person.add_link(legislator["WebSiteUrl"])
            person.add_source(legislator["WebSiteUrl"])

            if legislator["CapitolAddress"]:
                person.add_contact_detail(
                    type="address",
                    value=legislator["CapitolAddress"],
                    note="Capitol Office",
                )

            if legislator["CapitolPhone"]:
                person.add_contact_detail(
                    type="voice",
                    value=legislator["CapitolPhone"],
                    note="Capitol Office",
                )

            person.add_contact_detail(
                type="email", value=legislator["EmailAddress"], note="Capitol Office"
            )

            yield person
