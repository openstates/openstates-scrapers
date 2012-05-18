import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.events import EventScraper, Event

import pytz
import lxml.html


class TXEventScraper(EventScraper):
    state = 'tx'
    _tz = pytz.timezone('US/Central')
    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape(self, chamber, session):
        if not session.startswith('82'):
            raise NoDataForPeriod(session)

        self.scrape_committee_upcoming(session, chamber)

    def scrape_event_page(self, session, chamber, url):
        page = self.lxmlize(url)
        print page

    def scrape_page(self, session, chamber, url):
        try:
            page = self.lxmlize(url)
            events = page.xpath("//a[contains(@href, 'schedules/html')]")
            for event in events:
                self.scrape_event_page(session, chamber, event.attrib['href'])
        except lxml.etree.XMLSyntaxError:
            pass  # lxml.etree.XMLSyntaxError: line 248: htmlParseEntityRef: expecting ';'
            # XXX: Please fix this, future hacker. I think this might be a problem
            # with lxml -- due diligence on this is needed.

    def scrape_committee_upcoming(self, session, chamber):
        chid = {'upper': 'S',
                        'lower': 'H',
                        'other': 'J'}[chamber]

        url = "http://www.capitol.state.tx.us/Committees/Committees.aspx" + \
                "?Chamber=" + chid

        page = self.lxmlize(url)
        refs = page.xpath("//div[@id='content']//a")
        for ref in refs:
            self.scrape_page(session, chamber, ref.attrib['href'])
