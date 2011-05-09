import re
import datetime
import contextlib

from .utils import sessionDaysUrl, voteHistoryUrl
from .utils import removeNonAscii, sponsorsToList

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

#################################################################
# main class:
class SCBillScraper(BillScraper):
    state = 'sc'

    @contextlib.contextmanager
    def lxml_context(self,url):
	body = self.urlopen(url)
	body = unicode(self.urlopen(url), 'latin-1')
	elem = lxml.html.fromstring(body)
	try:
		yield elem
	except Exception as error:
		print 'show error ', url , ' error ', error
		#self.show_error(url,body)	
		raise


    #################################################################
    # Return list of bills on this page
    def scrape_vote_page(self, chamber, page):
	table_xpath = "/html/body/table/tbody/tr/td/div[@id='tablecontent']/table/tbody/tr/td[@class='content']/div[@id='votecontent']/div/div/table"

	self.log('scraping bill vote page for chamber %s' % chamber)
	bills_on_this_page = []
	bills_seen = set()

	tables = page.xpath(table_xpath)
	if len(tables) != 1:
		self.warn( 'error, expecting one table, aborting' )
		return

	rows = tables[0].xpath("//tr")
	numbills, dupcount = 0, 0
	session = "119"

	for r in rows:
	  try:
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
		else:
			title = " ".join(btitle)

		if title.startswith("(") and title.endswith(")"):
			title = title[1:-1]

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
			self.debug("   votepage: found bill |%s| |%s|", bill_id, title)
	  except UnicodeEncodeError:
		self.error("scrape vote page : unicode error")

	self.log( "THERE ARE %d bills: %d dups " %(numbills,dupcount)) 
	return bills_on_this_page


    ###################################################
    def scrape_session_days(self, url, page):
	"""The session days page contains a list of 
	bills by introduction date.
	Returns a list of these pages
	"""

	page = lxml.html.fromstring(page)
	self.log("scrape_session_days: getting list of day pages: [%s]" % url )
	page.make_links_absolute(url)

	# All the links have 'contentlink' class
	for link in page.find_class('contentlink'):
		self.debug( "   Bills introduced on %s are at %s" % ( str(link.text),str(link.attrib['href']) ))
	return [str(link.attrib['href']) for link in page.find_class('contentlink')]


    ###################################################
    def extract_bill_info(self, session,chamber,dayurl,d):
	"""Extracts bill info, which is the bill id,
	the sponsors, and a paragraph describing the bill (a shorter
	summary suitable for a title may be available 
	elsewhere, but not here).

	Returns: a Bill with bill id, sponsor, and title set."""

	regexp = re.compile( "/cgi-bin/web_bh10.exe" )
	bregexp = re.compile( "bill1=(\d+)&" )

	bill_name, summary, the_action = None, None, None

	start = d.find("--")
	stop = d.find(":",start)

	d1 = d
	after_sponsor = d
	sponsors = []

	bill_source, bill_document, bill_id = None, None, None
	if start >= 0 and stop > start:
		bn = d[:start]
		bill_name = bregexp.search(bn).groups()[0]

		temp1 = d[1:start]
		s1 = temp1.find(">") 
		if s1 >= 0:
			s2 = temp1.find("<",s1)
			if s2 > s1:	
				temp2 = temp1[s1+1:s2].split()
				complete_bill_name = " ".join(temp2)
				bill_id = complete_bill_name

		start += 2  # skip the two dashes
		bill_source = d[1:start]
		bill_document = d[1:start]

		sponsors = sponsorsToList( d[start+2:stop] )

		after_sponsor = d[stop+1:]

	summary = d1[stop]
	summary_end = after_sponsor.find("<br>")
	if summary_end < 0:
		summary_end = after_sponsor.find("<p>")

	if summary_end > 0:
		summary = d1[stop:summary_end]

		d1 = d1[:summary_end]
		maybe_actions = d
		act = maybe_actions.find("<center>")
		if act != -1:
			end_act = maybe_actions.index("</center>", act)
			act += len("<center>")
			maybe_actions = maybe_actions[act:end_act]
			#print "Action: ", maybe_actions
			the_action = maybe_actions
	else:
		self.log("\n\nSUMMARY_END: %s %s, %s ==> %s\n\n" %(dayurl, summary_end,summary,d))

	try:
		bs = summary.decode('utf8')
	except:
		self.log("scrubbing %s summary, originally %s" % (bill_name,summary) )
		summary = removeNonAscii(summary)

	if len(summary) > 300:
		summary = summary[1:300]
		self.log("Truncated summary [%s]" % summary )

	if len(summary) == 0:
		self.log("NO SUMMARY url:%s (%s,%s,%s) " % (dayurl, session,chamber,bill_id))
		return None
	else:
		self.debug("Bill(%s,%s,%s,%s)" %(session,chamber,bill_id,summary))
		bill = Bill(session,chamber,bill_id,summary)
		bill.add_source(dayurl)
		for sponsor in sponsors:
			bill.add_sponsor("primary", sponsor )

		#TEMPORARY TAMI
		#if the_action != None:
		#	bill.add_action(chamber, the_action, 'date')
		return bill

    ###################################################
    def fix_bill_id(self,s):
	return "%s%s%s" % (s[0:1],".",s[1:])

    ###################################################
    def scrape_day(self, session,chamber,dayurl,data):
	"""Extract bill info from the daily summary
	page.  Splits the page into the different
	bill sections, extracts the data,
	and returns list containing the parsed bills.
	"""
	# throw away everything before <body>
	start = data.index("<body>")
	stop = data.index("</body>",start)

	if stop >= 0 and stop > start:
	  all = re.compile( "/cgi-bin/web_bh10.exe" ).split(data[start:stop])
	  self.debug( "number of bills on page = %d" % (len(all)-1 ))

	  # skip first one, because it's before the pattern
	  return [self.extract_bill_info(session,chamber,dayurl,segment) 
		for segment in all[1:]]

	self.log("scrape_day: bad format %s" % dayurl)
	raise

    ####################################################
    # 1. Get list of days with information by parsing daily url
    #    which will have one link for each day in the session.
    # 2. Scan each of the days and collect a list of bill numbers.
    # 3. Get Bill info.
    ####################################################
    def scrape(self, chamber, session):
	self.log( 'scrape(session %s,chamber %s)' % (session, chamber))

        if session != '119':
            raise NoDataForPeriod(session)

        sessions_url = sessionDaysUrl(chamber) 

	session_days = []
	with self.urlopen( sessions_url ) as page:
		session_days = self.scrape_session_days(sessions_url,page)

	self.log( "Session days: %d" % len(session_days) )

	bills_with_votes = []
	with self.lxml_context( voteHistoryUrl(chamber) ) as page:
		bills_with_votes = self.scrape_vote_page(chamber,page)

	self.debug( "Bills with votes: %d" % len(bills_with_votes))
	

	# now go through each session day and extract the bill summaries
	# if the vote page has a bill summary, use that for the title
	# otherwise, use the longer paragraph on the day page
	#
	# keep track of which bills have been processed, and get bill details only once
	# (each bill will appear on the day page whenever it had an action)
	bills_processed = set()
	bills_with_summary = set()

	billdict = dict()
	for b in bills_with_votes:
		fixed = self.fix_bill_id(b['bill_id'])
		billdict[ fixed ] = b
		bills_with_summary.add(fixed) 

	for dayurl in session_days:
		self.debug( "processing day %s" % dayurl )
		with self.urlopen( dayurl ) as data:
			daybills = self.scrape_day(session,chamber,dayurl,data)
			self.debug( "  #bills on this day %d" % len(daybills))

		for b in daybills:
			if b == None:
				continue
			bill_id = b['bill_id']
			if bill_id in bills_processed: 
				self.debug("   already processed %s" % bill_id )
				continue

			self.debug( "    processing [%s] ... " % bill_id )
			if bill_id in bills_with_summary:
				ab = billdict[bill_id]
				self.log( "  changing title to %s" % ab['title'])
				b['description'] = b['title']
				b['title'] = ab['title']

			bills_processed.add( bill_id )
			self.save_bill(b)

	self.log( "Total bills processed: %d : " % len(bills_processed) )
	#self.debug( "Bills processed: %s" % ("|".join(bills_processed)) )
