import re
import datetime
import urllib2

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

# Extracts bill number and title from a string
# Sample input "Something someting Bill 1: Bill Title - Something else "
#    returns (1,Bill Title)
def extract_title(string):
	title_pattern = re.compile(".* Bill (\d*):\s*(.*)\s*-.*$")
	g1 = title_pattern.search(string)
	#print 'g1 = ', g1
	if g1 != None:
		groups = g1.groups()
		#print 'groups ', groups
		if len(groups) == 2:
			bill_number = groups[0]
			title = groups[1].strip()
			#print "extract_title billn orig [%s] [%s] title [%s]" % (string, bill_number, title)
			return (bill_number, title )
	return (None,None)

# extracts senators from string.
#   Gets rid of Senator(s) at start of string, 
#   Senator last names are separated by commas, except the last two 
#   are separated by the word 'and'
#   handles ' and '
def corrected_sponsor(orig):

	sponsors = []
	parts = orig.split()
	if orig.startswith("Senator") and len(parts) >= 2:
		#print '|', orig, '| returning ', parts[1]
		sponsors.append(" ".join(parts[1:]))
		return sponsors

	if len(parts) == 1:
		sponsors.append(parts[0])
		return sponsors

	#print 'orig ' , orig , ' parts ', len(parts)
	and_start = orig.find(" and ")
	if and_start > 0:
		#print 'has and |', orig, '|'
		for p in parts:
			if p != "and":
				sponsors.append(p)
		#print  ' returning ', sponsors 
		return sponsors
	
	else:
		sponsors.append(orig)

	return sponsors


# Returns a tuple with the bill id, sponsors, and blurb 
def extract_bill_data(data):

	chamber = "lower"
	pat1 = "<title>"
	match = data.find(pat1)

	title = None
	start_title = data.find("<title>")
	end_title = data.find("</title>")

	if start_title > 0 and end_title > start_title:
		start_title = start_title + len("<title>")
		title = data[start_title:end_title]
		#print 'before title is [', title, ']'
		(bill_number,title) = extract_title(title)
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
	#print 'end sponsor: ' , end_sponsor 
	if end_sponsor < 0:
		print 'warning no sponsors'
		return ()

	sponsor_names = sample1[:end_sponsor]
	if sponsor_names.find("Senator") >= 0:
		chamber = "upper"
	tmp = sponsor_names.split()
	sponsor_names = " ".join(tmp).split(",")

	slist = [corrected_sponsor(n) for n in sponsor_names]

	sponlist = []
	for bbb in slist:
		sponlist.extend(bbb)

	blurb = None
	bill_name = title
	return ( bill_number, bill_name, sponlist, blurb, chamber )


#
# This page contains links for each day in the session
# Follow Each link to get the bills introduced on that day.
#   Note that both senate and house bills will be on the same
#   page.
#
daily_url = "http://www.scstatehouse.gov/sintro/sintros.htm"

class SCBillScraper(BillScraper):
    state = 'sc'

    ####################################################
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
            return
		

	# the first page contains a list of bills by introduction date
	# find links which are of the form YYYYMMDD.htm (eg. 20110428.htm)
	# then process each of these pages
        url = "http://www.scstatehouse.gov/sintro/sintros.htm"

	summary_file = open("summary.txt","w")
	print "BillNumber:Title:Sponsors:Blurb" 
	for r in range(1,3):
		#billurl = "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%d&session=119" % r
		billurl = "http://scstatehouse.gov/sess119_2011-2012/bills/%d.htm" % r
		try:
        		with self.urlopen(billurl) as data:
				bill = scrape_static_html_bill_page(data,summary_file):
            			self.save_bill(bill)
		except IOError:
			print 'Failed ', billurl
	summary_file.close()

    	####################################################
	# scrape static bill html pages, urls are like 
	# http://scstatehouse.gov/sess119_2011-2012/bills/%d.htm
	def scrape_static_html_bill_page(data,summary_file):
		(bill_id,title,sponsors,blurb,chamber) = extract_bill_data(data)
		print "%s:%s:%s:%s:%s" % (bill_id,title,chamber,sponsors,blurb)
		summary_file.write( "%s:%s:%s\n    %s\n" % (bill_id,title,chamber,sponsors))
		#summary_file.write( "%s:%s:%s:%s" % (bill_id,title,sponsors,blurb))
		save_file = open("bill_%s.html" %(bill_id),"w")
		save_file.write(data)
		save_file.close()

            	bill = Bill(session, chamber, bill_id, title)
		bill.add_source(billurl)

		for sponsor in sponsors:
			bill.add_sponsor("sponsor", sponsor )

		return bill
