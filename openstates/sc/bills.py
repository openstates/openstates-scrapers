import re
import datetime
import contextlib

from .utils import session_days_url, vote_history_url, action_type, bill_type, vote_url
from .utils import removeNonAscii, sponsorsToList, scrape_bill_details

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

import lxml.html

#################################################################
# main class:
class SCBillScraper(BillScraper):
    state = 'sc'
    people = dict()
    members = []

    def __init__(self, *args, **kwargs):
	super(SCBillScraper,self).__init__(*args,**kwargs)
	self.initStuff()

    def initStuff(self):
	self.debug("TODO get legislators to get first names for sponsors")

    def initMember(self,chamber):
        if chamber == 'lower':
            url = 'http://www.scstatehouse.gov/html-pages/housemembers.html'
        else:
            url = 'http://www.scstatehouse.gov/html-pages/senatemembersd.html'

        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)
            rows = doc.xpath('//pre/div[@class="sansSerifNormal"]')

            for row in rows:
                member_a = row.xpath('a')[0]

                name_party = member_a.text_content()
                if name_party.find('[D]') != -1:
                    party = 'Democratic'
                    full_name = name_party.partition('[D]')[0].strip()
		    self.debug("Democratic %s" % full_name );
                elif name_party.find('[R]') != -1:
                    party = 'Republican'
                    full_name = name_party.partition('[R]')[0].strip()
	            self.debug("Republican %s" % full_name );
		else:
		    full_name = None

		if full_name:
			#if there's a comma, should get rid of 
			parts = full_name.split()
			last_name = parts[-1]
			self.people[last_name] = full_name

			name_pat = re.compile(r'(?P<first>\w+)\s+(?P<mi>\w+)?\s+(?P<last>\w+)(?P<suffix>,.*)?')
			name_pat = re.compile(r'(?P<first>\w+)\s+(?P<mi>\w.?)?\s+(?P<last>[\w\']+)(,.*)?')
			self.debug("LAST NAME [%s] Full[%s]" % (last_name, full_name) );

			results = name_pat.search(full_name)
			if results:
				last_name = results.group('last')
				self.debug("    MATCHED RESULTS LAST NAME FULL [%s] last [%s]" % (full_name, last_name ))
				self.people[last_name] = full_name

	

    @contextlib.contextmanager
    def lxml_context(self,url):
	body = self.urlopen(url)
	body = unicode(self.urlopen(url), 'latin-1')
	elem = lxml.html.fromstring(body)
	try:
		yield elem
	except Exception as error:
		raise ScrapeError( "lxml url %s error %s"  % (url,error))


    #################################################################
    # Return list of bills on this page
    def scrape_vote_page(self, session, chamber, page):
	table_xpath = "/html/body/table/tbody/tr/td/div[@id='tablecontent']/table/tbody/tr/td[@class='content']/div[@id='votecontent']/div/div/table"

	self.log('scraping bill vote page for chamber %s' % chamber)
	bills_on_this_page = []
	bills_seen = set()

	tables = page.xpath(table_xpath)
	if len(tables) != 1:
		self.log( 'error, expecting one table, aborting' )
		return

	rows = tables[0].xpath("//tr")
	dupcount = 0

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
			self.debug("votepage: duplicate |%s| |%s|" % (bill_id, title))
		else:
			bills_seen.add( bill_id )

			# TAMI
			#try:
				#pdf, resp = self.urlretrieve(bill_vote_url)
				#self.debug("retrieved url %s" % bill_vote_url)
				#self.debug("resp %s" % resp)
				#vote_contents = convert_pdf(pdf, 'text-nolayout')
				#vote_contents = convert_pdf(bill_vote_url, 'text-nolayout')
			#except Exception as error:
			#	raise ScrapeError("Failed to parse vote_url %s error %s" % (bill_vote_url,error))
			#self.debug("vote_contents %s" % vote_contents)
			
			bill = Bill(session, chamber, bill_id, title)
			bill['vote_url'] = bill_vote_url
			bills_on_this_page.append(bill)
			bills_seen.add( bill_id )
			self.debug("   votepage: found bill |%s| |%s| |%s|", bill_id, title, bill_vote_url )
	  except UnicodeEncodeError:
		self.error("scrape vote page : unicode error")

	self.debug( "votepage: found %d bills: %d dups " % (len(bills_seen),dupcount)) 
	return bills_on_this_page


	###################################################
    def get_sponsors(self, d):
	# this matches the sponsor 
	sponsor_regexp = re.compile("--(.*):")
	result = sponsor_regexp.search(d)
	if result != None:
		self.log("get_sponsors found sponsors %s "  % result.group(0))
		return result.group(1)

    ###################################################
    def scrape_details(self, bill_detail_url, session, chamber, bill_id, page):
	
	data = page

	pat1 = re.compile(r'</FORM>')
	results = pat1.search(data)
	if not results:
		raise ScrapeError("scrape_details(1) - unable to parse |%s|"  % bill_detail_url)

	pre_start = page.find("<pre>",results.start())
	if pre_start == -1: 
		#raise ScrapeError("scrape_details(2) - unable to parse (no <pre>) |%s|\n|%s|"  % (bill_detail_url,page))
		self.log("scrape_details(2) - unable to parse (no <pre>) |%s|\n|%s|"  % (bill_detail_url,page))
		return

	pre_stop = page.find("</pre>",pre_start)
	if pre_stop == -1:
		raise ScrapeError("scrape_details(3) - unable to parse (no </pre>) %s"  % bill_detail_url)

	pre_section = page[pre_start:pre_stop]
	self.debug( "DETAILS PRE (%d,%d) [%s] " % (pre_start, pre_stop, pre_section))
	data = pre_section
	vurl = None
	
	date_re = re.compile("\d\d/\d\d/\d\d")

	billattr = dict()
	pat2 = re.compile(r' By ')
	results = pat2.search(data)
	#print " by = ", results.start() ,  " " , results.end()
	if results != None:
		bystuff = data[results.start():results.end()]
		#print " bystuff = ", bystuff
		data = data[results.end():]

	pat3 = re.compile(r'</b>')
	results1 = pat3.search(data)
	#print " after </b> = ", results1.start() ,  " " , results1.end()
	#if results1 != None:
	#	abba = data[results1.start():results1.end()]
	#	print " abba = ", abba 

	newspon = []
	if results != None and results1 != None:
		sponsors = data[:results1.start()]
		#self.debug( "DETAIL SPONSORS: [%s]" % data[:results1.start()].strip() )
		billattr['sponsors'] = data[:results1.start()]
		mysponsors = sponsorsToList( billattr['sponsors'] )
		#self.debug("QQQ SPONSOR ORIG |%s| becomes |%s|" % (billattr['sponsors'], mysponsors))
		for s in mysponsors:
			if s in self.people:
				#self.log( "DETAIL SPONSOR FOUND [%s]=[%s]" % (s,self.people[s]) )
				newspon.append(self.people[s])
			else:
				self.debug( "DETAIL [%s] SPONSOR NOT FOUND [%s]" % (bill_id,s) )
				newspon.append(s)
		data = data[results1.end():]
		
	linenum = 0
	parse_state = 0
	bill_summary = ""
	apat = re.compile(">(H|S) (\d*)<")
	billpat = re.compile("(\d+)")
	
	similar_bills = []
	actions = []
	for line in data.splitlines():
		#self.debug("   DETAILS parse_state: %d %d line |%s|" % (linenum, parse_state,line)) 
		if parse_state == 0: 
			result1 = apat.search(line)
			if result1:
				sbill = dict()	
				sbill['bill_number' ] = result1.group(2)
				sbill['bill_suffix' ] = result1.group(1)
				sbill['bill_name' ] = "%s %s" % (result1.group(1), result1.group(2))
				similar_bills.append(sbill)
			else:
				bill_summary += line	
			parse_state = 1
		elif parse_state == 1:
			ahref = line.find("<A HREF") 
			if ahref >= 0:
				# the links should be on this line 
				#if line.find("View full text"):
				#	self.debug("VV %s View full text" % bill_id)
				if line.find("View Vote History"):
					bill_results = billpat.search(bill_id)
					if bill_results:
						bill_number = bill_results.group(0)
						vurl = vote_url(bill_number)
					#self.debug("VV |%s| (%d) View Vote History" % (bill_id, ahref))
				parse_state = 2
			else:
				bill_summary += line
		elif parse_state == 2:
			# We'v got the bill summary now, create the bill
			bill_summary = bill_summary.strip() 
			try:
				bs = bill_summary.decode('utf8')
			except:
				self.log("scrubbing %s summary, originally %s" % (bill_id,bill_summary) )
				bill_summary = removeNonAscii(bill_summary)

			bill = Bill(session, chamber, bill_id, bill_summary, 
				type=bill_type(bill_summary))

			parse_state = 3
			date_results = date_re.search(line)
			if date_results:
				the_date = date_results.group(0)
				date = datetime.datetime.strptime(the_date, "%m/%d/%y")
				date = date.date()
				action = line
				bill.add_action(chamber, action, date, type=action_type(action) )
				self.debug( "     bill %s action: %s %s" % (bill_id,the_date,action))

		elif parse_state == 3:
			date_results = date_re.search(line)
			if date_results:
				the_date = date_results.group(0)
				date = datetime.datetime.strptime(the_date, "%m/%d/%y")
				date = date.date()
				action = line
				bill.add_action(chamber, action, date, type=action_type(action) )
				self.debug( "     bill %s action: %s %s" % (bill_id,the_date,action))
		linenum += 1


	if similar_bills:
		billattr['similar'] = similar_bills
		self.debug("similar %s %s" % (bill_id, similar_bills))
		bill['similar'] = similar_bills
		
	sponsors = newspon 

	bill.add_source(bill_detail_url)
	bill_name = bill_id

	for sponsor in sponsors:
		bill.add_sponsor("sponsor", sponsor )

	if vurl:
		self.debug("QQQ Got vote url [%s]" % vurl )

	#self.debug("QQQ SPONSOR ORIG\n|%s|\n|%s|\n" % (billattr['sponsors'], sponsors))
	self.debug("QQQ %s - Summary |%s|" % (bill_id, bill_summary ))
	#self.debug("QQQ %s - Source |%s|" % (bill_id, bill_detail_url))
	#self.debug("QQQ %s - Sponsors |%s|" % (bill_id, sponsors ))
	self.save_bill(bill)


    ###################################################
    def fix_bill_id(self,s):
	"Adds a period to the bill, eg from H 8000 to H. 8000"
	return "%s.%s" % (s[0:1],s[1:])

    ###################################################
    def recap(self, data):
	"""Extract bill ids from daily recap page.  
	Splits page into sections, and returns list containing bill ids 
	"""
	# throw away everything before <body>
	start = data.index("<body>")
	stop = data.index("</body>",start)

	bill_id_exp = re.compile(">(?P<id>\w\. \d{1,4}?)</a> \(<a href=")
	billids = set()
	if stop >= 0 and stop > start:
	  all = re.compile( "/cgi-bin/web_bh10.exe" ).split(data[start:stop])
	  for part in all[1:]:
		result = bill_id_exp.search(part)
		if result: 
			bill_id = result.group('id')
			billids.add(bill_id)

	  return billids

	raise ScrapeError("recap: bad format %s" % data )



    ####################################################
    # 1. Get list of days with information by parsing daily url
    #    which will have one link for each day in the session.
    # 2. Scan each of the days and collect a list of bill numbers.
    # 3. Get Bill info.
    ####################################################
    def scrape(self, chamber, session):
	self.debug( 'scrape(session %s,chamber %s)' % (session, chamber))

        if session != '119':
            raise NoDataForPeriod(session)

	self.initMember(chamber)
        sessions_url = session_days_url(chamber) 

	days = []
	with self.urlopen( sessions_url ) as page:
		page = lxml.html.fromstring(page)
		page.make_links_absolute(sessions_url)
		days = [str(link.attrib['href']) for link in page.find_class('contentlink')]

	self.log( "Session days: %d" % len(days) )

	bills_with_votes = []
	vhistory_url = vote_history_url(chamber)
#	with self.lxml_context( vhistory_url ) as page:
#		page.make_links_absolute(vhistory_url)
#		bills_with_votes = self.scrape_vote_page(session, chamber,page)

	self.debug( "Bills with votes: %d" % len(bills_with_votes))
	#if len(bills_with_votes) > 0:
	#	self.debug("ABORTING")
	#	return

	# visit each day and extract bill ids
	all_bills = set()
	for dayurl in days:
		#self.debug( "processing day %s" % dayurl )
		with self.urlopen( dayurl ) as data:
			billids = self.recap(data)
			all_bills |= billids;
			self.debug( "  #bills %d all %d on %s" % (len(billids),len(all_bills),dayurl))
		
	regexp = re.compile( "\d+" )
	for bill_id in all_bills:
		self.log("Processing [%s]" % bill_id)
		pat = regexp.search(bill_id)
		if not pat:
			self.log( "383 Missing billid [%s]" % bill_id )
			continue

		bn = pat.group(0)
		dtl_url = "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%s&session=%s" % (bn,session)
		self.debug("447 detail %s %s" % (bn,dtl_url) )
		with self.urlopen(dtl_url) as page:
			self.scrape_details( dtl_url, session, chamber, bill_id, page)

	self.log( "Total bills processed: %d : " % len(all_bills) )
