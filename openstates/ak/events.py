import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import Event, EventScraper

import pytz
import lxml.html


class AKEventScraper(EventScraper):
    state = 'ak'

    _tz = pytz.timezone('US/Alaska')

    def scrape(self, chamber, session):
        if session != '27':
            raise NoDataForPeriod(session)

        if chamber == 'other':
            return

        year, year2 = None, None
        for term in self.metadata['terms']:
            if term['sessions'][0] == session:
                year = str(term['start_year'])
                year2 = str(term['end_year'])
                break

        # Full calendar year
        date1 = '0101' + year[2:]
        date2 = '1231' + year[2:]

        url = ("http://www.legis.state.ak.us/basis/"
               "get_hearing.asp?session=%s&Chamb=B&Date1=%s&Date2=%s&"
               "Comty=&Root=&Sel=1&Button=Display" % (
                   session, date1, date2))

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            path = "//font[starts-with(., '(H)') or starts-with(., '(S)')]"
            for font in page.xpath(path):
                match = re.match(r'^\((H|S)\)(.+)$', font.text)

                chamber = {'H': 'lower', 'S': 'upper'}[match.group(1)]
                comm = match.group(2).strip().title()

                next_row = font.xpath("../../following-sibling::tr[1]")[0]

                when = next_row.xpath("string(td[1]/font)").strip()
                when = datetime.datetime.strptime(when + " " + year,
                                                  "%b %d  %A %I:%M %p %Y")
                when = self._tz.localize(when)

                where = next_row.xpath("string(td[2]/font)").strip()

                description = "Committee Meeting\n"
                description += comm

                links = font.xpath(
                    "../../td/font/a[contains(@href, 'get_documents')]")
                if links:
                    agenda_link = links[0]
                    print agenda_link
                    event['link'] = agenda_link.attrib['href']

                event = Event(session, when, 'committee:meeting',
                              description, location=where)
                event.add_source(url)
                self.save_event(event)
