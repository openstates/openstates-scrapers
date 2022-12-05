import re
import pytz
import datetime as dt
from collections import defaultdict
from openstates.scrape import Scraper, Event

from .utils import MDBMixin


class NJEventScraper(Scraper, MDBMixin):
    _tz = pytz.timezone("US/Eastern")
    _event_bills = {}

    def initialize_committees(self, year_abr):
        chamber = {"A": "Assembly", "S": "Senate", "": ""}

        com_csv = self.to_csv("COMMITTEE.TXT")

        self._committees = {}

        # There are some IDs that are missing. I'm going to add them
        # before we load the DBF, in case they include them, we'll just
        # override with their data.
        overlay = {
            "A": "Assembly on the Whole",
            "S": "Senate on the Whole",
            "J": "Joint Legislature on the Whole",
            "TED": "First Legislative District Economic Development Task Force",
            "ABUB": "Assembly Budget Committee",
            "JBOC": "Joint Budget Oversight",
            "JPS": "Joint Committee on the Public Schools",
            "LRC": "New Jersey Law Revision Commission",
            "LSI": "Select Committee on Investigation",
            "PHBC": "Pension and Health Benefits Review Commission",
            "SBAB": "Senate Budget and Appropriations Committee",
            "JLSU": "Space Leasing and Space Utilization Committee",
            "SUTC": "Sales and Use Tax Review Commission",
            "SPLS": "Special Session",
            "JCES": "Joint Committee on Ethical Standards",
            "JEJ": "Joint Committee on Economic Justice and Equal Employment Opportunity",
            "LSC": "Legislative Services Commission",
            "THIE": "Senate Task Force on Health Insurance Exchange Implementation Committee",
            "CASC": "College Affordability Study Commission",
            "CIR": "State Commission of Investigation",
            "TDWI": "Taskforce on Drinking Water Infrastructure",
            "JMC": "State Capitol Joint Management Commission",
            "APPC": "Legislative Apportionment Commission",
        }
        self._committees = overlay

        for com in com_csv:
            # map XYZ -> "Assembly/Senate _________ Committee"
            self._committees[com["Code"]] = " ".join(
                (chamber[com["House"]], com["Description"], "Committee")
            )

    def scrape(self, session=None):
        year_abr = ((int(session) - 209) * 2) + 2000
        self._init_mdb(year_abr)
        self.initialize_committees(year_abr)
        self.scrape_bills()
        records = self.to_csv("AGENDAS.TXT")
        for record in records:
            status = "tentative"

            if record["Status"] == "Canceled" or record["Status"] == "Cancelled":
                status = "cancelled"
            elif record["Status"] == "Not Meeting":
                status = "cancelled"
            description = record["Comments"]
            related_bills = []

            for bill in re.findall(r"(A|S)(-)?(\d{4})", description):
                related_bills.append(
                    {"bill_id": "%s %s" % (bill[0], bill[2]), "descr": description}
                )

            date_time = "%s %s" % (record["Date"], record["Time"])
            date_time = dt.datetime.strptime(date_time, "%m/%d/%Y %I:%M %p")

            if date_time < dt.datetime.now():
                status = "passed"

            try:
                hr_name = self._committees[record["CommHouse"]]
            except KeyError:
                self.warning("unknown committee code %s, skipping", record["CommHouse"])

            description = "Meeting of the {}".format(hr_name)

            event = Event(
                name=description,
                start_date=self._tz.localize(date_time),
                location_name=record["Location"] or "Statehouse",
                classification="committee-meeting",
                status=status,
            )
            item = None
            for bill in related_bills:
                item = item or event.add_agenda_item(description)
                item.add_bill(bill["bill_id"])

            for bill in self._event_bills[record["CommHouse"][0]][record["CommHouse"]][
                f"{record['Date']}{record['Time']}"
            ]:
                item = item or event.add_agenda_item(description)
                item.add_bill(bill)

            event.add_committee(hr_name, id=record["CommHouse"], note="host")
            event.add_source("http://www.njleg.state.nj.us/downloads.asp")

            url_date = date_time.strftime("%Y-%m-%d-%H:%M:00")
            event_url = f"https://www.njleg.state.nj.us/live-proceedings/{url_date}/{record['CommHouse']}/{record['Type']}"
            if status != "cancelled":
                event.add_source(event_url)

            if status == "passed":
                year = date_time.strftime("%Y")
                agenda_type_code = record["Type"][0]
                media_url = (
                    f"https://www.njleg.state.nj.us/archived-media/{year}/{record['CommHouse']}-meeting-list"
                    f"/media-player?committee={record['CommHouse']}&agendaDate={url_date}&agendaType={agenda_type_code}&av=A"
                )
                event.add_media_link("Hearing Audio", media_url, "text/html")
            yield event

    def scrape_bills(self):
        rows = self.to_csv("BAGENDA.TXT")
        temp = self.ndd()
        for row in rows:
            chamber = row["CommHouse"][0]
            com = row["CommHouse"]
            lookupdate = f"{row['Date']}{row['Time']}"

            if not temp[chamber][com][lookupdate]:
                temp[chamber][com][lookupdate] = []

            temp[chamber][com][lookupdate].append(
                f"{row['BillType']} {row['BillNumber']}"
            )

        print(temp)
        self._event_bills = temp

    def ndd(self):
        return defaultdict(self.ndd)
