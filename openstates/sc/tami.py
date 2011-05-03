import re
import datetime

import sys
print 'sys ', sys
sys.path.append("../..")

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

xurl = "http://www.scstatehouse.gov/php/web_bh10.php?bill1=494&session=119"
url = "file://bill494.html"

ofilename = "bill494.html"
filename = "php494.html"
filename = "494_fulltext.htm"
#filename = "1_fulltext.htm"
filename2 = "494_2.htm"

# example title: <title>2011-2012 Bill 1: S.C. Election Reform Act - South Carolina Legislature Online</title>

#--
def scrape_bill_name_chamber(page):
	title = page.xpath("/html/head/title/text()")[0].split(":",1)[1].split("-",1)[0]
	billname = page.xpath("/html/body/p/b")[0].text
	if billname.startswith("S"):
		chamber = "upper"
	else:
		chamber = "lower"
	#paras = page.xpath("//p")
	#for para in paras:
		#if para.text.find("General Bill"):
		#	print '********* GENEFRAL BILL ********'
		#print 'Got para ', para, ' para ' , para.text
	return (title,billname,chamber)

try:

	fsock = open(filename, "r")
	print "file opened: ", filename

	page = lxml.html.parse(fsock)
	#hpage = lxml.html.soupparser(fsock)
	#print 'got hpage'

	(title,bill_id,chamber) = scrape_bill_name_chamber(page)

	session = "119"
	bill = Bill(session, chamber, bill_id, title)
	print "billname [%s] title[%s] chamber[%s]" % (bill_id,title,chamber)
	#print "bill" , bill 

	#bill.add_version(bill_version, bill_html)


except IOError:
	print 'Got IOError, reading ', filename

try:
	fsock2 = open(filename2, "r")
	print "file opened: ", filename2
	fpage = lxml.html.parse(fsock2)
	fbillname = fpage.xpath("//b")
	for iff  in fbillname:
		print 'iff ' , iff, ' ', iff.text
		ftxt = iff.itertext()
		print 'fxt ', ftxt
		for z in ftxt:
			print "z = ", z
			if z.find("General Bill"):
				print "Found general bill"
			else:
				print "DID NOT FIND GENFREAL BILL"
		#bill.add_sponsor # version(bill_version, bill_html)
	for ff in fbillname:
		print 'ff ' , ff, ' ', ff.text
		
	#fbillname = fpage.xpath("/html/body/pre/b")[0].text
	# find the test with S 0404hh04
except IOError:
	print 'Got IOError, reading ', filename2



