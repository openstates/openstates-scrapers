import pytz
import dateutil.parser
import datetime
import json
from scrapers.utils import LXMLMixin
from openstates.scrape import Scraper, Event


class MEEventScraper(Scraper, LXMLMixin):
    _TZ = pytz.timezone("US/Eastern")
    chambers = {"upper": "Senate", "lower": ""}
    date_format = "%B  %d, %Y"

    def scrape(self, session=None, start=None, end=None):

        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # testimony url, we'll need it later in a loop

        # testmony query looks gnary but breaks down to:
        # $filter: (Request/PaperNumber eq 'SP0219') and (Request/Legislature eq 129)
        # $orderby: LastName,FirstName,Organization
        # $expand: Request
        # $select: Id,FileType,NamePrefix,FirstName,LastName,Organization,
        # PresentedDate,FileSize,Topic

        testimony_url_base = (
            "http://legislature.maine.gov/backend/"
            "breeze/data/CommitteeTestimony?"
            "$filter=(Request%2FPaperNumber%20eq%20%27{}%27)%20and"
            "%20(Request%2FLegislature%20eq%20{})"
            "&$orderby=LastName%2CFirstName%2COrganization&"
            "$expand=Request&$select=Id%2CFileType%2CNamePrefix"
            "%2CFirstName%2CLastName%2COrganization%2CPresentedDate%2CFileSize%2CTopic"
        )

        if start is None:
            start_date = datetime.datetime.now().isoformat()
        else:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
            start_date = start_date.isoformat()

        # default to 30 days if no end
        if end is None:
            dtdelta = datetime.timedelta(days=30)
            end_date = datetime.datetime.now() + dtdelta
            end_date = end_date.isoformat()
        else:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
            end_date = end_date.isoformat()

        bills_by_event = {}

        bills_url = (
            "http://legislature.maine.gov/backend/breeze/data/"
            "getCalendarEventsBills?startDate={}&endDate={}"
        )
        bills_url = bills_url.format(start_date, end_date)
        page = json.loads(self.get(bills_url).content)

        for row in page:
            bills_by_event.setdefault(row["EventId"], [])
            bills_by_event[row["EventId"]].append(row)

        # http://legislature.maine.gov/backend/breeze/data/getCalendarEventsRaw?startDate=2019-03-01T05%3A00%3A00.000Z&endDate=2019-04-01T03%3A59%3A59.999Z&OnlyPHWS=false
        url = (
            "http://legislature.maine.gov/backend/breeze/data/"
            "getCalendarEventsRaw?startDate={}&endDate={}&OnlyPHWS=true"
        )
        url = url.format(start_date, end_date)

        page = json.loads(self.get(url).content)

        for row in page:
            if row["Cancelled"] is True or row["Postponed"] is True:
                continue

            start_date = self._TZ.localize(dateutil.parser.parse(row["FromDateTime"]))
            end_date = self._TZ.localize(dateutil.parser.parse(row["ToDateTime"]))

            name = row["CommitteeName"]

            if name is None:
                name = row["Host"]

            address = row["Location"]
            address = address.replace(
                "Cross Building",
                "Cross Office Building, 111 Sewall St, Augusta, ME 04330",
            )

            address = address.replace(
                "State House", "Maine State House, 210 State St, Augusta, ME 04330"
            )

            event = Event(
                start_date=start_date,
                end_date=end_date,
                name=name,
                location_name=address,
            )

            event.add_source(
                "http://legislature.maine.gov/committee/#Committees/{}".format(
                    row["CommitteeCode"]
                )
            )

            if bills_by_event.get(row["Id"]):
                for bill in bills_by_event[row["Id"]]:
                    description = "LD {}: {}".format(bill["LD"], bill["Title"])
                    agenda = event.add_agenda_item(description=description)
                    agenda.add_bill("LD {}".format(bill["LD"]))

                    if bill["TestimonyCount"] > 0:
                        test_url = testimony_url_base.format(
                            bill["PaperNumber"], session
                        )
                        test_page = json.loads(self.get(test_url).content)
                        for test in test_page:
                            title = "{} {} - {}".format(
                                test["FirstName"],
                                test["LastName"],
                                test["Organization"],
                            )
                            if test["NamePrefix"] is not None:
                                title = "{} {}".format(test["NamePrefix"], title)

                            test_url = (
                                "http://legislature.maine.gov/backend/app/services"
                                "/getDocument.aspx?doctype=test&documentId={}".format(
                                    test["Id"]
                                )
                            )

                            if test["FileType"] == "pdf":
                                media_type = "application/pdf"

                            event.add_document(
                                note=title, url=test_url, media_type=media_type
                            )
            yield event
