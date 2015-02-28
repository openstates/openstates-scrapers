import re
import datetime
import requests

from lxml import html
from openstates.utils import LXMLMixin
from billy.scrape.events import EventScraper, Event



class MOEventScraper(EventScraper, LXMLMixin):
    jurisdiction = 'mo'

    keywords = ["Committee:", "Chair:", "Vice Chair:", "Time:", "Location:", "Note:"]

    # A generator to return the next two tables that make up an event
    def hearings(self, tables):
        limit = len(tables)
        count = 0
        while count < limit :
            header = tables[count]
            bills = tables[count+1]
            count += 2
            yield header, bills

#   # A generator to return keyword/value pairs from the scraped data
    def next_kv(self, list_of_td):
        extra_note = ""
        current_kw = ""
        for item in list_of_td:
            s = item.text_content().strip()
            if current_kw == "":
                if s[0:3] == "***":
                    extra_note = s
                    extra_note += " "

                elif s in self.keywords:
                    current_kw = s
            else:
                if current_kw == "Note:" and extra_note != "":
                    yield current_kw, extra_note + s
                else:
                    yield current_kw, s
                current_kw = ""


    def scrape(self, session, chambers):

        # Read from file -- keeps the data constant for debugging
        # purposes since the actual pages changes every day
        #f = open('/Users/pfcass/Dev/openstates/events.html')
        #page = f.read()
        #doc = html.fromstring(page)

        # Grab the page of meetings and convert to an html list document
        page = requests.get('http://house.mo.gov/HearingsPrint.aspx?DateOrder=true')
        doc = html.fromstring(page.text)

        # The document is made up of multiple tables
        # A pair of tables represents a hearing.
        # - first table is the 'header': personnel, location, etc
        # - second table are the bills
        agenda = doc.xpath("/html/body/form[@id='form1']/span[@id='lblCmtInfo']/table[@id='cmtGroup'][*]")

        # here are the thing well need for the event
        when = ""
        title = ""
        related_bills = []
        room = ""
        link = ""
        description = ""
        additional_info =  { "+NOTE" : "" }

        for header, bills in self.hearings( agenda ):
            hrows = header.xpath("./*/td")
            brows = bills.xpath("./*/td")
            print "{0} hrows and {1} brows".format(len(hrows), len(brows))

            for keyword, value in self.next_kv(hrows):
                print "{0} / {1}".format(keyword, value)


            for item in brows:
                print "brow:{0}".format(item.text_content().strip())
        #count = 0
        #for agenda_item in agenda:
        #    ++count
        #    item =  agenda_item.xpath("tr[1]/td")
        #    if len(item) > 0:
        #       print "{0} {2}-> {1}".format(count, item[0].text_content().strip(), len(item))

        #agenda = doc.xpath("/html/body/form[@id='form1']/span[@id='lblCmtInfo']/table[@id='cmtGroup'][1]/tr[1]/td")
        #print "0: {0}".format( str[0].text_content().strip() )
        #print "1: {0}".format( str[1].text_content().strip() )
        #print "2: {0}".format( str[2].text_content().strip() )
        #print "3: {0}".format( str[3].text_content().strip() )

        event = Event(session, when, 'committee:meeting', title,
                          location=room, link=link, details=description,
                          related_bills=related_bills)

        #self.save_event(event)

        print("Scraping events for Missouri")
