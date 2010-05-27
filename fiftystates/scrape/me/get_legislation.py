#!/usr/bin/env python
import urllib
import urllib2
import re
from BeautifulSoup import BeautifulSoup
import datetime as dt

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.legislation import LegislationScraper, NoDataForYear

class MELegislationScraper(LegislationScraper):

    state = 'me'

    def scrape_session(self, chamber, year, session):
        if chamber == "lower":
            bill_abbr = "HP"
        else:
            bill_abbr = "SP"
	
        legislature = (int(year) - 1761)/2
        sessionname = str(legislature) + "-" + session

        bill_list_url = "http://www.mainelegislature.org/legis/bills/search_ps.asp"
        postvalues = {'snum' : legislature,
                  'stype' : session,
                  'paperNumberPrefix' : bill_abbr } 
        postdata = urllib.urlencode(postvalues) + "&PID=1456&titleSearch=&wordSearch=&ldFrom=1&ldTo=5000&paperNumber=&lrFrom=&lrTo=&fiscalImpact=&sec1=0&amend_filing_no_prefix=%25&amend_filing_no=&amend_type=&amend_sequence=&aff_amend_type=&aff_amend_sequence=&sec2=0&law_type=&chapter_number=&sec3=0&committeeOfRef=&phMMFr=&phDDFr=&phYYFr=2009&phMMTo=&phDDTo=&phYYTo=2009&wkMMFr=&wkDDFr=&wkYYFr=2009&wkMMTo=&wkDDTo=&wkYYTo=2009&sec4=0&sponsorSession=124&hSponsor=&sSponsor=&sec5=0&hStat=&hStatMMFr=&hStatDDFr=&hStatYYFr=2009&hStatMMTo=&hStatDDTo=&hStatYYTo=2009&sStat=&sStatMMFr=&sStatDDFr=&sStatYYFr=2009&sStatMMTo=&sStatDDTo=&sStatYYTo=2009&sec6=0&affectedTitle=&affectedSection=&affectedSubSection=&affectedParagraph=&sec7=0&subject=&submit=Search"
        req = urllib2.Request(bill_list_url, postdata)
        self.log("Getting bill list for %s, session %s, %s chamber" % (year, session, chamber))
        try:
            base_bill_list = BeautifulSoup(urllib2.urlopen(req).read())
        except:
            # this session doesn't exist for this year
            self.log("No data found for %s, session %s, %s chamber" % (year, session, chamber))
            return

        for item in base_bill_list.find("table", { "class" : "resultstable" }).findAll("tr"):
            if item.find("td", { "class" : "RecordNumbers" }):
		bill_id = item.find("td", { "class" : "RecordNumbers" }).contents[0].split(',')[1].strip()
		bill_title = item.nextSibling.find("td", { "class" : "RecordTitle" }).contents[0]
                self.save_bill(chamber, sessionname, bill_id, bill_title)

    def scrape_bills(self, chamber, year):
        if int(year) < 1998 or int(year) > dt.date.today().year or int(year) % 2 == 0:
            raise NoDataForYear(year)

        for special in ["R1", "R2", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]:
            self.scrape_session(chamber, year, special)

if __name__ == '__main__':
    MELegislationScraper.run()
