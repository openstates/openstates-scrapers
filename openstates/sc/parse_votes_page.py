import re
import datetime

import sys
print 'sys ', sys
sys.path.append("../..")

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

senate_url = "http://scstatehouse.gov/php/votehistory.php?chamber=S"
house_url = "http://scstatehouse.gov/php/votehistory.php?chamber=H"

table_xpath = "/html/body/table/tbody/tr/td/div[@id='tablecontent']/table/tbody/tr/td[@class='content']/div[@id='votecontent']/div/div/table"

# for testing
senate_filename = "senate_votehistory.html"
house_filename = "house_votehistory.html"


# example title: <title>2011-2012 Bill 1: S.C. Election Reform Act - South Carolina Legislature Online</title>

#########################################################################
def scrape_bill_name_chamber(page):
	title = page.xpath("/html/head/title/text()")[0].split(":",1)[1].split("-",1)[0]
	billname = page.xpath("/html/body/p/b")[0].text
	if billname.startswith("S"):
		chamber = "upper"
	else:
		chamber = "lower"
	return (title,billname,chamber)


def scrape_vote_page(chamber, page):
	if chamber == "S":
		url = senate_url
	else:
		url = house_url

	fname = ("%s_summary_bills.txt") % chamber
	summary = open(fname, "w")
	tables = page.xpath(table_xpath)

	print "num tables ", len(tables)
	tbl = tables[0]
	print "1 GOT TABLE ", tbl
	tnum = 1
	numbills = 0
	dupcount = 0
	billdict = {}
	for table in tables:
		rows = table.xpath("//tr")

		print 'table ', tnum, ' numrows ', len(rows)
		#or rr in brows:
		#print "rr ", rr, " ", rr.text 
		rownum = 1
		for r in rows:
		  try:
			item = {}
			alltd = r.xpath("td");
			brows = r.xpath("td[1]/a[@target='_blank']/text()")
			bname = r.xpath("td[2]/a[@target='_blank']/text()")
			btitle = r.xpath("td[3]/text()")
			btitle1 = r.xpath("string(td[3])")
		
			if len(bname) == 0:
				continue

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

			if len(brows) > 0:
				bill_name = " ".join(bname)
				#print 'row ', rownum, ' num cols ', len(alltd)
				#print '   ', title, ' nm ', bname , ' ', brows

				item["title"] = " ".join(title)
				item["name"] = " ".join(bname)
				item["ayes"] = " ".join(bayes)
				item["nayes"] = " ".join(bnayes)
				item["nv"] = " ".join(bnv)
				item["candidate"] = " ".join(bcandidate)
				item["date"] = " ".join(bdate)

				try:
					if billdict[bill_name] != None:
						print "**** DUPLICATE: ", bill_name
					billdict[bill_name] = item
					dupcount = dupcount + 1
				except KeyError:
					numbills = numbills + 1
					billdict[bill_name] = item

		
				#print '   ', brows, ' ', title, ' nm ', bname, ' btitle ', btitle , ' b1 ', btitle1

				#print '   date ', bdate , ' candidate ', bcandidate 
				#print '   ayes ', bayes, ' nayes ', bnayes, ' nv ', bnv , ' excabs ', excabs, ' abstain ', abstain , ' total', total,  ' result ', result 
				#print '   item ', item 
				#print ' '
				summary.write("%s,%s,%s,%s\n" % (bname, title, bdate, bcandidate ))
			cols = r.xpath("string(td)");

		  except UnicodeEncodeError:
				print "unicode error"

		  rownum = rownum + 1
		tnum = tnum + 1


	summary.close()

	print "THERE ARE " , len(billdict) , " different bills"
	print "  numbills = " , numbills 
	print "  dupcount = " , dupcount 

	fname = "%s_summary2.txt" % chamber
	summary2 = open(fname, "w")
	for k in billdict.keys():
		v = billdict[k]
		#print "%s,%s" % (v['name'],v['title'])
		summary2.write("%s,%s\n" % (v['name'],v['title']))
	summary2.close()



try:
	fsock = open(senate_filename, "r")
	print "file opened: ", senate_filename
	page = lxml.html.parse(fsock)

	scrape_vote_page("S",page)
	fsock.close()


	fsock = open(house_filename, "r")
	print "file opened: ", house_filename
	page = lxml.html.parse(fsock)

	scrape_vote_page("H",page)
	fsock.close()

except IOError:
	print 'Got IOError, reading ', filename


