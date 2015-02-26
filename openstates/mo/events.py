import re
import datetime
import requests

from lxml import html
from openstates.utils import LXMLMixin
from billy.scrape.events import EventScraper, Event


class MOEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'mo'

    def scrape(self, session, chambers):

        # Read from file -- keeps the data constant for debugging
        # purposes since the actual pages changes every day
        #f = open('/Users/pfcass/Dev/openstates/events.html')
        #page = f.read()
        #doc = html.fromstring(page)

        # Grab the page of meetings and convert to an html list document
        page = requests.get('http://house.mo.gov/HearingsPrint.aspx?DateOrder=true')
        doc = html.fromstring(page.text)

        str = doc.xpath("/html/body/form[@id='form1']/span[@id='lblCmtInfo']/table[@id='cmtGroup'][3]/tr[1]/td")
        print "0: {0}".format( str[0].text_content().strip() )
        #print "1: {0}".format( str[1].text_content().strip() )
        #print "2: {0}".format( str[2].text_content().strip() )
        #print "3: {0}".format( str[3].text_content().strip() )

        #event = Event()

        #self.save_event(event)

        print("Scraping events for Missouri")
