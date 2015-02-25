import re
import datetime

from openstates.utils import LXMLMixin
from billy.scrape.events import EventScraper, Event


class MOEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'mo'

    def scrape(self, session, chambers):
        print("Scraping events for Missouri")
