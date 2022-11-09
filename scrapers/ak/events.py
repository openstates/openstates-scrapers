import pytz
import lxml
import dateutil.parser
import re

from utils import LXMLMixin
from utils.events import match_coordinates
from openstates.scrape import Scraper, Event


class AKEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("US/Alaska")
    API_BASE = "https://www.akleg.gov/publicservice/basis"
    NS = {"ak": "http://www.legis.state.ak.us/Basis"}
    CHAMBERS = {"S": "upper", "H": "lower", "J": "joint"}
    COMMITTEES = {"upper": {}, "lower": {}, "joint": {}}
    COMMITTEES_PRETTY = {"upper": "SENATE", "lower": "HOUSE", "joint": "JOINT"}

    # date_filter argument can give you just one day;
    # format is "2/28/2019" per AK's site
    def scrape(self, chamber=None, session=None, date_filter=None):
        listing_url = "/meetings"
        args = {"minifyresult": "true", "session": session}
        headers = {"X-Alaska-Legislature-Basis-Query": "meetings;details"}

        # 2/28/2019
        if date_filter is not None:
            args["date"] = date_filter

        # load the committee abbrevs
        self.scrape_committees(session)

        page = self.api_request(listing_url, args, headers)

        events_xml = page.xpath("//Meeting")

        for row in events_xml:
            # Their spelling, not a typo
            if row.get("Canceled") == "true":
                continue

            row_chamber = row.xpath("string(chamber)")
            if chamber and self.CHAMBERS[row_chamber] != chamber:
                continue

            yield from self.parse_event(row, self.CHAMBERS[row_chamber])

    def parse_event(self, row, chamber):
        # sample event available at http://www.akleg.gov/apptester.html
        committee_code = row.xpath("string(Sponsor)").strip()

        if committee_code in self.COMMITTEES[chamber]:
            committee_name = "{} {}".format(
                self.COMMITTEES_PRETTY[chamber],
                self.COMMITTEES[chamber][committee_code]["name"],
            )
        else:
            committee_name = "{} {}".format(
                self.COMMITTEES_PRETTY[chamber], "MISCELLANEOUS"
            )

        name = "{} {}".format(
            self.COMMITTEES_PRETTY[chamber], row.xpath("string(Title)").strip()
        )

        # If name is missing, make it "<CHAMBER> <COMMITTEE NAME>"
        if name == "":
            name = committee_name

        location = row.xpath("string(Location)").strip()

        # events with no location all seem to be committee hearings
        if location == "" or re.match(r"^\w+\s\d+$", location):
            location = "Alaska State Capitol, 120 4th St, Juneau, AK 99801"
        elif re.match(r"^\w+\s\d+$", location) or re.match(
            r"(HOUSE|SENATE)\s\w+(\s\d+)?", location
        ):
            location = f"{location}, Alaska State Capitol, 120 4th St, Juneau, AK 99801"
        elif "anch lio" in location.lower():
            location = re.sub(
                r"anch lio",
                "Anchorage Legislative Information Office, 1500 W Benson Blvd, Anchorage, AK 99503",
                location,
                flags=re.IGNORECASE,
            )

        start_date = dateutil.parser.parse(row.xpath("string(Schedule)"))
        # todo: do i need to self._TZ.localize() ?

        event = Event(start_date=start_date, name=name, location_name=location)

        event.add_source("http://w3.akleg.gov/index.php#tab4")

        if committee_code in self.COMMITTEES[chamber]:
            event.add_participant(committee_name, type="committee", note="host")

        match_coordinates(
            event,
            [
                ("state capitol", ("58.302068966269374", "-134.41033234349783")),
                (
                    "anchorage legislative information",
                    ("61.19311529903147", "-149.91182077226256"),
                ),
            ],
        )

        for item in row.xpath("Agenda/Item"):
            agenda_desc = item.xpath("string(Text)").strip()
            if agenda_desc != "":
                agenda_item = event.add_agenda_item(description=agenda_desc)
                if item.xpath("BillRoot"):
                    bill_id = item.xpath("string(BillRoot)")
                    # AK Bill ids have a bunch of extra spaces
                    bill_id = re.sub(r"\s+", " ", bill_id)
                    agenda_item.add_bill(bill_id)

        yield event

    def scrape_committees(self, session):
        listing_url = "/committees"
        args = {"minifyresult": "true", "session": session}
        page = self.api_request(listing_url, args)

        for row in page.xpath("//Committee"):
            code = row.get("code").strip()
            name = row.get("name").strip()
            chamber = self.CHAMBERS[row.get("chamber")]
            category = row.get("category").strip()
            self.COMMITTEES[chamber][code] = {"name": name, "category": category}

            if category == "Joint Committee":
                self.COMMITTEES["joint"][code] = {"name": name, "category": category}

    def api_request(self, path, args={}, headers={}):
        # http://www.akleg.gov/apptester.html
        # http://www.akleg.gov/basis/BasisPublicServiceAPI.pdf

        # http://www.legis.state.ak.us/publicservice/basis/meetings?minifyresult=false&session=31
        # X-Alaska-Legislature-Basis-Version:1.2
        # X-Alaska-Legislature-Basis-Query:meetings;details
        headers["X-Alaska-Legislature-Basis-Version"] = "1.2"

        url = "{}{}".format(self.API_BASE, path)
        page = self.get(url, params=args, headers=headers, verify=False)
        page = lxml.etree.fromstring(page.content)
        return page
