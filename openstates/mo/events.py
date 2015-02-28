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

            # grab a couple of specific field from the next block
            td1 = bills.xpath("tr[1]/td")
            td2 = bills.xpath("tr[2]/td")
            if len(td1) == 0 or len(td2) == 0:
                count += 1
                yield header, None
                continue

            s1 = td1[0].text_content().strip()
            s2 = td2[0].text_content().strip()

            # test the 'bills' block.  If it has the 'Committee:' field
            # then it's really the next header.  There are no bills
            # associated with this meeting
            if s1.find("Committee") == 0 or s2.find("Committee") == 0:
                count += 1
                yield header, None
            else:
                bills = tables[count + 1]
                count += 2
                yield header, bills

#   # A generator to return keyword/value pairs from the scraped data
    # for the header for each bill.
    def next_kv(self, list_of_td):
        status = "scheduled"
        current_kw = ""
        for item in list_of_td:
            s = item.text_content().strip()
            if current_kw == "":
                if s[0:3] == "***":
                    status = s[3:]
                    end = status.find("***")
                    yield "Status", status[:end]

                elif s in self.keywords:
                    current_kw = s
            else:
                yield current_kw, s
                current_kw = ""

    # This routine process a table consisting of bills, where a bill is:
    # - a line w/ the bill number and a title
    # - a line w/ the sponsor
    # - a line of descriptive text
    #
    # ... and there may be a leading line about the type of hearing, which is 'sticky'
    # and holds until it is changes.  Initially, it's 'unspecified', but we assume that
    # it's a public hearing
    def bills(self, bill_data):
        separator = " -- "
        hearing_type = "Public Hearing"
        bill_no = ""
        bill_title = ""
        sponsor = ""
        for item in bill_data:
            s = item.text_content().strip()
            # line might be a bill or the type of hearing
            if s.find("Public Hearing") == 0:
                hearing_type = "Public Hearing"
            elif s.find("Executive Session") == 0:
                hearing_type = "Executive Session"
            elif s.find("Sponsor") == 0:
                sponsor = s
            elif s.find("HB") == 0 or s.find("HCR") == 0:
                sep = s.find(separator)
                bill_no = s[0:sep]
                bill_title = s[sep+len(separator):]
            else:
                # this is the description, which marks the end
                # of the record
                yield hearing_type, bill_no, bill_title, sponsor, s
                bill_no = bill_title = sponsor = ""




    def scrape(self, session, chambers):

        # Grab the page of meetings and convert to an html list document
        page = requests.get('http://house.mo.gov/HearingsPrint.aspx?DateOrder=true')
        doc = html.fromstring(page.text)

        # The document is made up of multiple tables
        # A pair of tables represents a hearing.
        # - first table is the 'header': personnel, location, etc
        # - second table are the bills
        agenda = doc.xpath("/html/body/form[@id='form1']/span[@id='lblCmtInfo']/table[@id='cmtGroup'][*]")
        print "agenda consists of {0} tables".format(len(agenda))

        # here are the thing well need for the event
        related_bills = []
        mtg = dict()

        for header, bills in self.hearings( agenda ):
            hrows = header.xpath("./*/td")

            status = ""
            for keyword, value in self.next_kv(hrows):
                if keyword == "Status":
                    status = value
                else:
                    mtg[keyword] = value

            if "Note:" in mtg:
                mtg["Note:"] = "(" + status + ") " + mtg["Note:"]
            else:
                mtg["Note:"] = status

            for k in mtg.keys():
                print "{0} {1}".format( k, mtg[k])

            if bills != None:
                print "Bills considered:"
                brows = bills.xpath("./*/td")
                for hearing_type, bill_no, bill_title, sponsor, text in self.bills(brows):
                    print " hearing_type: {0}".format(hearing_type)
                    print " bill: {0}".format(bill_no)
                    print " title: {0}".format(bill_title)
                    print " sponsor: {0}".format(sponsor)
                    print " text: {0}".format(text)
                    print

            print "---------------------"

            #event = Event(session, when, 'committee:meeting', title,
            #              location=room, link=link, details=description,
            #              related_bills=related_bills)

            #self.save_event(event)

        print("Scraping events for Missouri")
