# -*- coding: utf-8 -*-
from BeautifulSoup import BeautifulSoup
from urlparse import urljoin
import re
from util import get_text

from fiftystates.scrape.il import year2session
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

MEMBER_LIST_URL = {
    'upper': 'http://ilga.gov/senate/default.asp?GA=%s',
    'lower': 'http://ilga.gov/house/default.asp?GA=%s',
}

MEMBER_ID_PATTERN = re.compile("^.*MemberID=(\d+).*$")

class ILLegislatorScraper(LegislatorScraper):
    state = 'il'

    def scrape(self, chamber, year):
        # Data available for 1993 on
        try:
            session = year2session[year]
        except KeyError:
            raise NoDataForYear(year)

        url = get_legislator_url(chamber,session)
        data = self.urlopen(url)

        for legislator in get_legislators(chamber,session,data):
            self.save_legislator(legislator)

def get_legislator_url(chamber,session):
    """Produce a URL for a list of legislators for a given chamber/session.
    """
    return MEMBER_LIST_URL[chamber] % session

def get_legislators(chamber, session, data):
    """Given a file-like object representing a typical HTML page listing legislators for 
       a chamber of the GA, return a generator over Legislator objects encapsulating 
       that data.
    """
    rows = get_legislator_rows(data)
    for row in rows:
        legislator = parse_legislator_row(chamber, session, row)
        if legislator is None: continue
        yield legislator


def parse_legislator_row(chamber, session, row):
    cells = row("td")
    party = get_text(cells[-1])
    district = get_text(cells[-2])
    name_cell = cells[0].contents
    if not name_cell: return None
    linked_name = name_cell[0]
    first_name = middle_name = last_name = full_name = suffix = ""
    try:
        link = linked_name['href']
        match = MEMBER_ID_PATTERN.match(link)
        member_id = match.groups()[0]
        url = urljoin(MEMBER_LIST_URL[chamber],link)
        full_name = " ".join(linked_name.contents) # a list
        if full_name.find(",") != -1:
            (name,suffix) = full_name.split(",")
        else:
            name = full_name
            suffix = ""

        name_parts = name.split()
        if len(name_parts) == 2:
            (first_name,last_name) = name_parts
        elif len(name_parts) > 3:
            (first_name,middle_name) = name_parts[:2]
            last_name = " ".join(name_parts[2:])
        elif len(name_parts) == 3:
            first_name,middle_name,last_name = name_parts
        else:
            raise ValueError("Unexpected number of parts to %s" % full_name)
    except KeyError, e:
        return None
    except TypeError, e:
        # it's a string, not an element.
        return None
    return Legislator(session, chamber, district,
                                           full_name, first_name,
                                           last_name, middle_name,
                                           party, member_id=member_id,suffix=suffix,
                                           url=url)

def get_legislator_rows(data):
    s = BeautifulSoup(data)
    table = s("table")[3]
    rows = table("tr")
    rows = filter(lambda row: len(row) == 5, rows)
    return rows

