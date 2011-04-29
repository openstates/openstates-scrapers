import re
import datetime

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

class SCBillScraper(BillScraper):
    state = 'sc'

    def scrape(self, chamber, session):
	print '=== South Carolina SCRAPING session %s chamber %s\n' % (session, chamber)

        if session != '119':
            raise NoDataForPeriod(session)

        #if session != '2011-2012':
        #    raise NoDataForPeriod(session)

        if chamber == 'lower':
            bill_abbr = "H."
        else:
            bill_abbr = "S."

	# the first page contains a list of bills by introduction date
	# find links which are of the form YYYYMMDD.htm (eg. 20110428.htm)
	# then process each of these pages
        url = "http://www.scstatehouse.gov/sintro/sintros.htm"

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
	    #print 'HI TAMI GOT THE PAGE %s\n' % (str(page),)

            page.make_links_absolute(url)

	    # All the links have the 'contentlink' class
            for link in page.find_class('contentlink'):
		print "   Bills introduced on %s are at %s" % ( str(link.text),str(link.attrib['href']) )

            billPages = [str(link.attrib['href']) for link in page.find_class('contentlink')]
            print '--------------------------------------------------'
            print 'Bill pages ', billPages
	
            for billurl in billPages:
                print 'got a bill url ', billurl
                with self.urlopen(billurl) as billpage:
                    bpage = lxml.html.fromstring(billpage)
                    bpage.make_links_absolute(billurl)
                    # print '== got bill day page'
                    # find links with /cgi-bin/.....eec?billx=xxx&session=119>NAME OF THE BILL          
                    billnames = [str(zlink.text) 
				for zlink in bpage.xpath("//a[contains(@href, '/cgi-bin/web_bh10.exe')]")]
                    print 'billnames is for %s is %s' % (billurl, billnames)


            for link in page.xpath("//a[contains(@href, 'summary.cfm')]"):
		#print 'HI TAMI GOT LINK\n\n'

                #bill_id = link.text
                #title = link.xpath("string(../../td[2])")

                #bill = Bill(session, chamber, bill_id, title)
                #self.scrape_bill(bill, link.attrib['href'])

