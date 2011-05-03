import re
import datetime
import urllib2

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

def corrected_sponsor(orig):

	sponsors = []

	parts = orig.split()
	if orig.startswith("Senators") and len(parts) == 2:
		print '|', orig, '| returning ', parts[1]
		sponsors.append(parts[1])
		return sponsors

	if len(parts) == 1:
		sponsors.append(parts[0])
		return sponsors

	#print 'orig ' , orig , ' parts ', len(parts)
	and_start = orig.find(" and ")
	if and_start > 0:
		print 'has and |', orig, '|'
		for p in parts:
			if p != "and":
				sponsors.append(p)
		print  ' returning ', sponsors 
		return sponsors
	
	else:
		sponsors.append(orig)

	return sponsors


def find_end_of(line,pattern):
	match = line.find(pattern)
	if match != -1:
		return match + len(pattern)
	return match


# Returns a tuple with the bill id, sponsors, and blurb 

def extract_bill_data(data):

	pat1 = "<title>"
	pat1 = "<title>"
	match = data.find(pat1)

	title = None
	start_title = data.find("<title>")
	end_title = data.find("</title>")

	if start_title > 0 and end_title > start_title:
		start_title = start_title + len("<title>")
		title = data[start_title:end_title]
		print 'title is ', title
		aa = title.split(":",1)
		bb = aa[1].split("-",1)
		cc = bb[0].split()
		title = " ".join(cc)
	else:
		return ()

	next_part = end_title + len("</title>")
	sample1 = data[next_part:]

	start_sponsor = sample1.find("Sponsors: ")
	if start_sponsor < 0:
		print 'warning no sponsors'
		return ()

	start_sponsor = start_sponsor + len("Sponsors:")
	sample1 = sample1[start_sponsor:]
	#print 'start sponsor: ' , start_sponsor 

	end_sponsor = sample1.find("<br>")
	print 'end sponsor: ' , end_sponsor 
	if end_sponsor < 0:
		print 'warning no sponsors'
		return ()

	sponsor_names = sample1[:end_sponsor]
	tmp = sponsor_names.split()
	sponsor_names = " ".join(tmp).split(",")
	slist = [corrected_sponsor(n) for n in sponsor_names]

	sponlist = []
	for bbb in slist:
		sponlist.extend(bbb)

	#print 'Sponsor names: ' , sponsor_names
	#print 'SS Sponsor names: ' , slist 
	#print 'sponlist: ' , sponlist 
	#print '=================' 


	blurb = None
	bill_name = title
	return ( bill_name, sponlist, blurb )


#
# This page contains links for each day in the session
# Follow Each link to get the bills introduced on that day.
#   Note that both senate and house bills will be on the same
#   page.
#
daily_url = "http://www.scstatehouse.gov/sintro/sintros.htm"

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

	for r in range(1,2):
		#billurl = "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%d&session=119" % r
		billurl = "http://scstatehouse.gov/sess119_2011-2012/bills/%d.htm" % r
		savefilename = "savebill_%d.htm" % r
		print '   reading bill ', r, ' ', billurl
		print '       save ', savefilename

		try:
        		with self.urlopen(billurl) as data:
				bd = extract_bill_data(data)
				if len(bd) == 3:
					print "SUCCESS: \nBill[%s] \nSponsors[%s]\nBlurb: [%s]" % (bd)

		except IOError:
			print 'Failed ', billurl


	if r != -100:
		return
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
		if billurl != "TAMI": 
			return

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
		pass
