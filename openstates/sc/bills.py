import re
import datetime
import contextlib

from .utils import session_days_url, vote_history_url, action_type, bill_type
from .utils import removeNonAscii, sponsorsToList

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

#################################################################
# main class:
class SCBillScraper(BillScraper):
    state = 'sc'

    def __init__(self, *args, **kwargs):
	super(SCBillScraper,self).__init__(*args,**kwargs)
	self.initStuff()

    def initStuff(self):
	self.debug("TODO get legislators to get first names for sponsors")

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
    def scrape_vote_page(self, session, chamber, page):
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

	for r in rows:
	  try:
		brows = r.xpath("td[1]/a[@target='_blank']/text()")
		if len(brows) <= 0:
			continue

		bill_vote_url = None
		bill_votes_url = r.xpath("td[1]/a[@target='_blank']/@href")
		if bill_votes_url:
			bill_vote_url = str(bill_votes_url[0])

		bname = r.xpath("td[2]/a[@target='_blank']/text()")
		if len(bname) == 0:
			continue

		self.debug("brows [%s] bname[%s] url[%s]" % (brows,bname,bill_vote_url) )

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

			bill = Bill(session, chamber, bill_id, title)
			bill['vote_url'] = bill_vote_url
			#bill['vote_url_x'] = make_bill_vote_url(bill_id)
			bills_on_this_page.append(bill)
			bills_seen.add( bill_id )
			self.debug("   votepage: found bill |%s| |%s|", bill_id, title)
			self.debug("   voteurl: found bill |%s| |%s|", bill_id, bill_vote_url)
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
	self.debug("getting list of day pages: [%s]" % url )

	page = lxml.html.fromstring(page)
	page.make_links_absolute(url)

	# All the links have 'contentlink' class
	for link in page.find_class('contentlink'):
		self.debug( "Bills introduced %s at %s" % ( str(link.text),str(link.attrib['href']) ))
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
	summary_and_actions = None

	start = d.find("--")
	stop = d.find(":",start)

	d1 = d
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

		sponsors = sponsorsToList( d[start:stop] )
		self.debug("SPONSOR ORIG\n|%s|\n|%s|\n" % (d[start:stop], sponsors))

	summary_and_actions = d1[stop+1:]

	break_pat = re.compile(".*<br>", re.IGNORECASE )
	mm = re.match(break_pat,summary_and_actions)

	summary = summary_and_actions
	action_section = None

	if mm:
		# don't include the <br> as part of the title
		s_end = mm.end() - len("<br>")
		summary =  summary_and_actions[mm.start():s_end]
		action_section = summary_and_actions[mm.end():]

	action_mm = None
	actions_list = []
	if action_section:
		action_pat = re.compile("<center>(.*)</center>", re.IGNORECASE )
		action_mm = re.search(action_pat,action_section)
		if action_mm:
		 	gg = action_mm.groups()
			if gg:
				self.debug( "%s -- has action (%s)" % (str(bill_name), gg) )
				actions_list.extend(gg)

	try:
		bs = summary.decode('utf8')
	except:
		self.log("scrubbing %s summary, originally %s" % (bill_name,summary) )
		summary = removeNonAscii(summary)

	if len(summary) > 1000:
		origlen = len(summary)
		summary = summary[1:1000]
		self.log("Truncated summary (origlen=%d) [%s]" % (origlen, summary ))

	if len(summary) == 0:
		self.log("NO SUMMARY url:%s (%s,%s,%s) " % (dayurl, session,chamber,bill_id))
		return None

	summary = summary.strip()
	bill = Bill(session,chamber,bill_id,summary, type=bill_type(summary))

	self.log("Bill[%s,%s,%s][%s]\n" % (session,chamber,bill_id,summary))
	self.debug("%s - type |%s|" % (bill_name, bill_type(summary)))

	bill.add_source(dayurl)
	self.debug("%s - Source |%s|" % (bill_name, dayurl))

	bill_detail_url = "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%s&session=%s" % (bill_name,session)
	self.debug("%s - Source |%s|" % (bill_name, bill_detail_url))

	bill.add_source(bill_detail_url)
	self.debug("%s - Sponsors |%s|" % (bill_name, sponsors ))

	for sponsor in sponsors:
		bill.add_sponsor("primary", sponsor )

	for action in actions_list:
		date = datetime.datetime.strptime('11/23/1960', "%m/%d/%Y")
		date = date.date()
		#date = "11231960"
		bill.add_action(chamber, action, date, type=action_type(action) )
		self.debug("%s -  Action |%s|" % (bill_name, action_type(action)) )

	return bill

    ###################################################
    def fix_bill_id(self,s):
	"Adds a period to the bill, eg from H 8000 to H. 8000"
	return "%s%s%s" % (s[0:1],".",s[1:])

    ###################################################
    def process_daily_bills(self, daybills, billdict, bills_processed ):
	"""Process all the bills on the daily summary page."""

	for bill in daybills:
		if bill == None:
			continue

		bill_id = bill['bill_id']
		if bill_id in bills_processed: 
			self.debug("   already processed %s" % bill_id )
			continue

		if bill_id in billdict:
			ab = billdict[bill_id]
			self.log( "  changing title of %s to %s" % (bill_id,ab['title']))
			bill['description'] = bill['title']
			bill['title'] = ab['title']
			# how about getting the vote url here as well
			if ab['vote_url']:
				vv = ab['vote_url']
				self.debug("Bill %s has vote url %s" % (bill_id,ab['vote_url']))
				bill['vote_url'] = ab['vote_url']
				bill.add_source( ab['vote_url'] )
				# could collect votes here although the votes
				# are embedded in pdf


		bills_processed.add( bill_id )
		self.save_bill(bill)

    ###################################################
    def scrape_day(self, session,chamber,dayurl,data):
	"""Extract bill info from the daily summary
	page.  Splits page into the different
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

        sessions_url = session_days_url(chamber) 

	session_days = []
	with self.urlopen( sessions_url ) as page:
		session_days = self.scrape_session_days(sessions_url,page)

	self.log( "Session days: %d" % len(session_days) )

	bills_with_votes = []
	vhistory_url = vote_history_url(chamber)
	with self.lxml_context( vhistory_url ) as page:
		page.make_links_absolute(vhistory_url)
		bills_with_votes = self.scrape_vote_page(session, chamber,page)

	self.debug( "Bills with votes: %d" % len(bills_with_votes))

	# visit each session day and extract bill summaries
	# if the vote page has a bill summary, use that for the title
	# otherwise, use the longer paragraph on the day page

	# keep track of which bills have already been processed 
	# (each bill will appear on every day page whenever it had an action)
	bills_processed = set()

	billdict = dict()
	for b in bills_with_votes:
		fixed = self.fix_bill_id(b['bill_id'])
		billdict[ fixed ] = b

	for dayurl in session_days:
		self.debug( "processing day %s" % dayurl )

		with self.urlopen( dayurl ) as data:
			daybills = self.scrape_day(session,chamber,dayurl,data)
			self.debug( "  #bills on this day %d %s" % (len(daybills),dayurl))

    		self.process_daily_bills( daybills, billdict, bills_processed )

	self.log( "Total bills processed: %d : " % len(bills_processed) )
