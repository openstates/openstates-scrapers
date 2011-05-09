import re
import datetime

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

senate_url = "http://scstatehouse.gov/php/votehistory.php?chamber=S"
house_url = "http://scstatehouse.gov/php/votehistory.php?chamber=H"

table_xpath = "/html/body/table/tbody/tr/td/div[@id='tablecontent']/table/tbody/tr/td[@class='content']/div[@id='votecontent']/div/div/table"

# example title: <title>2011-2012 Bill 1: S.C. Election Reform Act - South Carolina Legislature Online</title>

#########################################################################
def scrape_bill_name(page):
	#log('scraping bill name')

	title = page.xpath("/html/head/title/text()")[0].split(":",1)[1].split("-",1)[0]
	billname = page.xpath("/html/body/p/b")[0].text
	if billname.startswith("S"):
		chamber = "upper"
	else:
		chamber = "lower"
	return (title,billname,chamber)


#########################################################################
# Return a list of bills found on this page
def scrape_vote_page(chamber, page):
	#log('scraping bill vote page for chamber ', chamber)
	bills_on_this_page = []
	bills_seen = set()
	if chamber == "S":
		url = senate_url
	else:
		url = house_url

	tables = page.xpath(table_xpath)
	if len(tables) != 1:
		print 'error, expecting one table, aborting'
		return

	rows = tables[0].xpath("//tr")
	numbills, dupcount = 0, 0
	session = "119"

	for r in rows:
	  try:
		item = {}
		alltd = r.xpath("td");
		brows = r.xpath("td[1]/a[@target='_blank']/text()")
		if len(brows) <= 0:
			continue

		bname = r.xpath("td[2]/a[@target='_blank']/text()")
		if len(bname) == 0:
			continue

		btitle = r.xpath("td[3]/text()")
		btitle1 = r.xpath("string(td[3])")
		
		title = btitle
		if len(btitle) == 0:
			title = btitle1

		bdate = r.xpath("td[4]/text()")
		bcandidate = r.xpath("td[5]/text()")

		bayes = r.xpath("td[6]/text()")
		bnayes = r.xpath("td[7]/text()")
		bnv = r.xpath("td[8]/text()")
		excabs = r.xpath("td[9]/text()")
		abstain = r.xpath("td[10]/text()")
		total = r.xpath("td[11]/text()")
		result = r.xpath("td[5]/text()")

		bill_id = " ".join(bname)
		if bill_id in bills_seen:
			dupcount = dupcount + 1
		else:
			bills_seen.add( bill_id )
			numbills = numbills + 1

			bill = Bill(session,chamber, bill_id, title)
			bills_on_this_page.append(bill)
			bills_seen.add( bill_id )
	  except UnicodeEncodeError:
		print "unicode error"

	#print "THERE ARE #bills: " ,  numbills, "  dups= " , dupcount 
	return bills_on_this_page


################################################################
if __name__ == '__main__':
	import sys
	sys.path.append("../..")

	def go(filename,chamber):
		"""Used as part of testing.  Processes a page stored in a file.
		Extracts the bills.  Writes the bills to a file name
		based on the chamber. eg. S_chamber_bills.txt or H_chamber_bills.txt.
		"""

		# Scrape the data 
		try:
			fsock = open(filename, "r")
			page = lxml.html.parse(fsock)
			bills = scrape_vote_page(chamber,page)
			print '  read file ', filename, ' chamber ', chamber, ' number of bills ', len(bills)
			fsock.close()
		except IOError:
			print 'Got IOError, filename = ', filename
		
		# Save data to file 
		try:
			ofilename = "%s_chamber_bills.txt" % chamber
			print '  writing output file: ', ofilename, ' #bills ', len(bills) 
			out = open(ofilename, "w")
			for bill in bills:
				out.write("%s,%s\n" % (bill['bill_id'], bill['title']))
			out.close()
			#output_bills_file(bills,ofilename);
		except IOError:
			print 'Got IOError, filename = ', ofilename


	# for testing
	senate_filename = "senate_votehistory.html"
	senate_filename = "tempfile.txt"
	house_filename = "house_votehistory.html"

	try:
		print 'Process senate: ', senate_filename
		go(senate_filename,"S")
		#print 'Process house: ', house_filename
		#go(house_filename,"H")
	except IOError:
		print 'Got IOError'

