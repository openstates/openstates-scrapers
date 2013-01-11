import re
import pytz
import datetime
import lxml.html

from billy.scrape.events import EventScraper, Event


class SCEventScraper(EventScraper):
    jurisdiction = 'sc'

    def get_page_from_url(self,url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page
        
    def scrape(self, chamber, session):
        if chamber == 'upper':
            events_url = 'http://www.scstatehouse.gov/meetings.php?chamber=S&&headerfooter=0'
        elif chamber == 'lower':
            events_url = 'http://www.scstatehouse.gov/meetings.php?chamber=H&headerfooter=0'
        else:
            return

        page = self.get_page_from_url(events_url)

        dates = page.xpath("//div[@id='contentsection']/ul")

        for date in dates:
            print date

