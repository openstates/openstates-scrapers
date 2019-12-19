import pytz
import lxml
import dateutil.parser
import re

from openstates.utils import LXMLMixin
from pupa.scrape import Scraper, Event


class AKEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("US/Alaska")
    API_BASE = "http://www.legis.state.ak.us/publicservice/basis"
    NS = {"ak": "http://www.legis.state.ak.us/Basis"}
    CHAMBERS = {"S": "upper", "H": "lower"}
    COMMITTEES = {"upper": {}, "lower": {}}
    COMMITTEES_PRETTY = {"upper": "SENATE", "lower": "HOUSE"}

    # date_filter argument can give you just one day;
    # format is "2/28/2019" per AK's site
    def scrape(self, chamber=None, session=None, date_filter=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

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
        committee_name = "{} {}".format(
            self.COMMITTEES_PRETTY[chamber],
            self.COMMITTEES[chamber][committee_code]["name"],
        )

        name = "{} {}".format(
            self.COMMITTEES_PRETTY[chamber], row.xpath("string(Title)").strip()
        )

        # If name is missing, make it "<CHAMBER> <COMMITTEE NAME>"
        if name == "":
            name = committee_name

        location = row.xpath("string(Location)").strip()

        # events with no location all seem to be committee hearings
        if location == "":
            location = "Alaska State Capitol, 120 4th St, Juneau, AK 99801"

        start_date = dateutil.parser.parse(row.xpath("string(Schedule)"))
        # todo: do i need to self._TZ.localize() ?

        event = Event(start_date=start_date, name=name, location_name=location)

        event.add_source("http://w3.akleg.gov/index.php#tab4")

        event.add_participant(committee_name, type="committee", note="host")

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

    def api_request(self, path, args={}, headers={}):
        # http://www.akleg.gov/apptester.html
        # http://www.akleg.gov/basis/BasisPublicServiceAPI.pdf

        # http://www.legis.state.ak.us/publicservice/basis/meetings?minifyresult=false&session=31
        # X-Alaska-Legislature-Basis-Version:1.2
        # X-Alaska-Legislature-Basis-Query:meetings;details
        headers["X-Alaska-Legislature-Basis-Version"] = "1.2"

        url = "{}{}".format(self.API_BASE, path)
        page = self.get(url, params=args, headers=headers)
        page = lxml.etree.fromstring(page.content)
        return page
