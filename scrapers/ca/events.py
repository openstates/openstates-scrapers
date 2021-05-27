import os
import re
import pytz
from collections import defaultdict

from openstates.scrape import Scraper, Event
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from .models import CACommitteeHearing, CALocation

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")


class CAEventScraper(Scraper):
    _tz = pytz.timezone("US/Pacific")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        host = kwargs.pop("host", MYSQL_HOST)
        user = kwargs.pop("user", MYSQL_USER)
        pw = kwargs.pop("pw", MYSQL_PASSWORD)

        if (user is not None) and (pw is not None):
            conn_str = "mysql://%s:%s@" % (user, pw)
        else:
            conn_str = "mysql://"
        conn_str = "%s%s/%s?charset=utf8" % (
            conn_str,
            host,
            kwargs.pop("db", "capublic"),
        )
        self.engine = create_engine(conn_str)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        grouped_hearings = defaultdict(list)

        for hearing in self.session.query(CACommitteeHearing):
            location = (
                self.session.query(CALocation)
                .filter_by(location_code=hearing.location_code)[0]
                .description
            )

            date = self._tz.localize(hearing.hearing_date)

            chamber_abbr = location[0:3]
            event_chamber = {"Asm": "lower", "Sen": "upper"}[chamber_abbr]

            if event_chamber != chamber:
                continue

            grouped_hearings[(location, date)].append(hearing)

        for ((location, date), hearings) in grouped_hearings.items():

            # Get list of bill_ids from the database.
            bill_ids = [hearing.bill_id for hearing in hearings]
            bills = [
                "%s %s" % re.match(r"\d+([^\d]+)(\d+)", bill).groups()
                for bill in bill_ids
            ]

            # Dereference the committee_nr number and get display name.
            msg = "More than one committee meeting at (location, date) %r"
            msg = msg % ((location, date),)
            assert len(set(hearing.committee_nr for hearing in hearings)) == 1, msg
            committee_name = _committee_nr[hearings.pop().committee_nr]

            desc = "Committee Meeting: " + committee_name
            event = Event(name=desc, start_date=date, location_name=committee_name)
            for bill_id in bills:
                if "B" in bill_id:
                    type_ = "bill"
                else:
                    type_ = "resolution"
                item = event.add_agenda_item("consideration")
                item.add_bill(bill_id, note=type_)

            event.add_person(committee_name + " Committee", note="host")
            event.add_source("https://downloads.leginfo.legislature.ca.gov/")

            yield event


# A mapping of committee_nr numbers to committee names they
# (probably) represent, based on direct correlation they bore
# to hearing locations that resemble committee names in
# the location_code_tbl in the db dump.
_committee_nr = {
    1: "Assembly Agriculture",
    2: "Assembly Accountability and Administrative Review",
    3: "Assembly Education",
    4: "Assembly Elections and Redistricting",
    5: "Assembly Environmental Safety and Toxic Materials",
    6: "Assembly Budget X1",
    7: "Assembly Governmental Organization",
    8: "Assembly Health",
    9: "Assembly Higher Education",
    10: "Assembly Housing and Community Development",
    11: "Assembly Human Services",
    13: "Assembly Judiciary",
    14: "Assembly Labor and Employment",
    15: "Assembly Local Government",
    16: "Assembly Natural Resources",
    17: "Assembly Public Employees, Retirement/Soc Sec",
    18: "Assembly Public Safety",
    19: "Assembly Revenue and Taxation",
    20: "Assembly Rules",
    22: "Assembly Transportation",
    23: "Assembly Utilities and Commerce",
    24: "Assembly Water, Parks and Wildlife",
    25: "Assembly Appropriations",
    27: "Assembly Banking and Finance",
    28: "Assembly Insurance",
    29: "Assembly Budget",
    30: "Assembly Public Health and Developmental Services",
    31: "Assembly Aging and Long Term Care",
    32: "Assembly Privacy and Consumer Protection",
    33: "Assembly Business, Professions and Consumer Protection ",
    34: "Assembly Jobs, Economic Development, and the Economy",
    35: "Assembly Finance",
    37: "Assembly Arts, Entertainment, Sports, Tourism, and Internet Media",
    38: "Assembly Veterans Affairs",
    39: "Assembly Communications and Conveyance",
    40: "Senate Agriculture",
    42: "Senate Business, Professions and Economic Development",
    44: "Senate Education",
    45: "Senate Elections and Constitutional Amendments",
    48: "Senate Governmental Organization",
    51: "Senate Labor and Industrial Relations",
    53: "Senate Judiciary",
    55: "Senate Natural Resources and Water",
    56: "Senate Public Employment and Retirement",
    58: "Senate Rules",
    59: "Senate Transportation and Housing",
    60: "Senate Health",
    61: "Senate Appropriations",
    62: "Senate Budget and Fiscal Review",
    64: "Senate Environmental Quality",
    66: "Senate Veterans Affairs",
    67: "Senate Transportation and Infrastructure Development",
    68: "Senate Public Health and Developmental Services",
    69: "Senate Banking and Financial Institutions",
    70: "Senate Insurance",
    71: "Senate Energy, Utilities and Communications",
    72: "Senate Public Safety",
    73: "Senate Governance and Finance",
    74: "Senate Human Services",
    75: "Senate Housing",
    80: "Senate Insurance, Banking and Financial Institutions",
}
