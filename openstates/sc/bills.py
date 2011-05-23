import re
import datetime
import contextlib

from .utils import action_type, bill_type, vote_url
from .utils import removeNonAscii, sponsorsToList

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

from pdfminer.pdfinterp import PDFResourceManager, process_pdf
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

import tempfile
import sys, traceback

import lxml.html

#################################################################
# main class:
class SCBillScraper(BillScraper):
    state = 'sc'
    urls = {
	'bill-detail' : "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%s&session=%s" ,
	'vote-url' : "http://www.scstatehouse.gov/php/votehistory.php?type=BILL&session=119&bill_number=%s",

	'lower' : { 
	  'daily-bill-index': "http://www.scstatehouse.gov/hintro/hintros.htm",
    	  'members':'http://www.scstatehouse.gov/html-pages/housemembers.html',
	  'vote-history': "http://www.scstatehouse.gov/php/votehistory.php?chamber=H"
	},

	'upper' : { 
	  'daily-bill-index': "http://www.scstatehouse.gov/sintro/sintros.htm",
	  'members' :'http://www.scstatehouse.gov/html-pages/senatemembersd.html',
	  'vote-history':"http://www.scstatehouse.gov/php/votehistory.php?chamber=S"
	}
    }


    people = dict()
    members = []

    def __init__(self, *args, **kwargs):
	super(SCBillScraper,self).__init__(*args,**kwargs)

    def initLegislators(self):
	self.initMember("lower")
	self.initMember("upper")

    def initMember(self,chamber):
	url = self.urls[chamber]['members']

        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)
            rows = doc.xpath('//pre/div[@class="sansSerifNormal"]')

            for row in rows:
                member_a = row.xpath('a')[0]

                name_party = member_a.text_content()
                if name_party.find('[D]') != -1:
                    party = 'Democratic'
                    full_name = name_party.partition('[D]')[0].strip()
		    #self.debug("Democratic %s" % full_name );
                elif name_party.find('[R]') != -1:
                    party = 'Republican'
                    full_name = name_party.partition('[R]')[0].strip()
	            #self.debug("Republican %s" % full_name );
		else:
		    full_name = None

		if full_name:
			#parts = full_name.split()
			#last_name = parts[-1]
			#self.people[last_name] = full_name

			# get rid of parenthetical expression
			# ex. Shannon S. Erickson (Mrs. Kendall F.)
			name_without_paren = full_name.partition('(')[0]

			# get rid of the suffix
			# ex. James E. Smith, Jr
			name_without_suffix = name_without_paren.partition(',')[0]
			nlast_name = name_without_suffix.split()[-1]
			self.people[nlast_name] = full_name

			#self.debug("%s Name [%s] Lastname [%s]" % (chamber, full_name, nlast_name))


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
		self.warning( 'error, scrape_vote_page, expecting one table, aborting' )
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
    def parse_rollcall(self,data):
	sections = [ 'FIRST', 'RESULT', 'Yeas:', 'YEAS','NAYS', 'EXCUSED ABSENCE', 'NOT VOTING', 'REST' ]

	lines = data.split("\n")
	section  = 0 
	next_section = 1

	areas = dict()
	for s in sections:
		areas[s] = []

	#print "number of lines ", len(lines)
	linenum = 0
	section_list = []
	expected = dict()
	for line in lines:
		if section >= len(sections):
			#print "after ", line
			continue

		skey = sections[section]
		nkey = sections[next_section]

		if line.startswith( nkey ) :
			#self.debug( "FOUND: %d %s %s "  % (linenum, line, section))
			areas[skey] = section_list	

			# get specified value to verify we get them all
			epat = re.compile("\w - (\d+)")
			eresult = epat.search(line)
			section_count = 0
			if eresult:
				section_count = int(eresult.group(1))

			expected[ nkey ] = section_count
			section_list = []

			section += 1
			next_section += 1

		elif len(line.strip()) > 0 and not re.search("Page \d+ of \d+", line):
			# Skip page footer, Page x of Y
			if not re.search("Page \d+ of \d+", line):
				section_list.append(line.strip())
		linenum += 1

	# handle last section lines
	areas[sections[section]] = section_list	

	# get specified value to verify we get them all
	epat = re.compile("\w - (\d+)")
	eresult = epat.search(line)
	section_count = 0
	if eresult:
		section_count = int(eresult.group(1))

	expected[ sections[next_section] ] = section_count

	yays = areas['YEAS']
	nays = areas['NAYS']
	other = areas['EXCUSED ABSENCE'] 
	other.extend( areas['NOT VOTING'] )

	return (expected, areas, yays, nays, other )


    ###################################################
    def add_vote_yeas(self,vote,bill_id,yays):
	#self.debug("VVV-XX add_vote_yea %s %s" % (bill_id,yays))
	try:
	  for legislator in yays:
		#self.debug("VVV-XX   ADDING YEA %s [%s] " % (bill_id, legislator) )
		vote.yes(legislator)
	except Exception as error:
		self.warning("VVV-XX   FAILED TO ADD YEA %s [%s] " % (bill_id, error) )
		raise ScrapeError("VVV-XX: Failed to add yea  %s" % bill_id)

    ###################################################
    def add_vote_nays(self,vote,bill_id,nays):
	self.debug("VVV-XX add_vote_nays %s %s" % (bill_id,nays))
	try:
	  for legislator in nays:
		#self.debug("VVV-XX   ADDING NAY %s [%s] " % (bill_id, legislator) )
		vote.no(legislator)
	except Exception as error:
		self.warning("VVV-XX   %FAILED TO ADD NAY %s [%s] " % (bill_id, error) )


    ###################################################
    def print_vote_sections(self,bill_id,expected,areas):
	for k in areas:
		if k == "RESULT":
			continue
		if k == "FIRST":
			continue
		v = areas[k]
		msg = ""
		try:
			exp = expected[ k ] 
		except KeyError:
			exp = 0

		try:
			if len(v) != exp:
				self.warning("Vote count mismatch - %s [%s] Got %d, expected %d"  % (bill_id,k, len(v), exp))
			else:
				self.debug("VVV-ZZ Section %s [%s] actual (%d) expected (%d)"  % (bill_id,k, len(v), exp))
			for vv in v:
				self.debug("   %s  %s: [%s] " % (bill_id, k, vv) )
		except Exception as error:
			self.debug("VVV-ERR: [%s] " % (error) )

	for k in areas:
		if k == "RESULT":
			continue
		if k == "FIRST":
			continue
		v = areas[k]
		try:
			exp = expected[ k ] 
		except KeyError:
			exp = 0
		try:
			if len(v) != exp:
				self.warning("Vote count mismatch - %s [%s] Got %d, expected %d"  % (bill_id,k, len(v), exp))
			else:
				self.debug("VVV-ZZ-1 Section %s [%s] actual (%d) expected (%d)"  % (bill_id,k, len(v), exp))

		except Exception as error:
			self.debug("VVV-ERR-1: [%s] " % (error) )
#		file = open("sample_vote_file.txt","r")
#		data = file.read()
#		(expected, areas) = parse_rollcall(data)
#		print_vote_sections(expected, areas)
#		file.close()

    ###################################################
    def scrape_vote_detail(self, vurl, chamber, bill, bill_id ):

	with self.urlopen( vurl ) as votepage:
		#if votepage.find("No Votes Returned") >= 0:
		#	self.debug("VVV-1 NO VOTES [%s]" % vurl )
		if votepage.find("No Votes Returned") != -1:
			return

		bill_title_xpath = "//div[@id='votecontent']/div[1]"

		vxpath = '/html/body/table/tbody/tr/td/div[@id="tablecontent"]/table/tbody/tr/td[@class="content"]/div[@id="votecontent"]//td'

		doc = lxml.html.fromstring(votepage)
		doc.make_links_absolute(vurl)

		vote_row = doc.xpath(vxpath)

		bill_title_dev = doc.xpath(bill_title_xpath)[0].text_content().strip()
		#bill_title_dev = doc.xpath(bill_title_xpath)
		#try:
		#	for bt in bill_title_dev:
		#		self.debug("VVV-TITLE-2 BT [%s]" % bt.text_content().strip() )
		#except Exception as error:
		#	self.debug("VVV-TITLE FAILED TO GET CONTENT [%s]" % error)


		# 0, 1 = datetime, 2 = text,3 = link to votes page
		# 4 = yeas , #5 = nays, #6 = nv , #7 = Ex Abs, #8 = Abstain, #9 = Total , #10 result

		vote_date_time = vote_row[1].text_content()
		action = vote_row[2].text_content()

		# Get link to PDF containing roll call votes
		link_to_votes = vote_row[3].text_content()
		link = vote_row[3]
		link_to_votes_href = link.xpath("a/@href")[0]
		#self.debug("VVV-BB link href[%s]" % (link_to_votes_href))

		yes_count_str = vote_row[4].text_content()
		nay_count_str = vote_row[5].text_content()
		other_count_str = vote_row[6].text_content()
		total_count_str = vote_row[9].text_content()
		result = vote_row[10].text_content()
		
		yes_count = int(yes_count_str)
		no_count = int(nay_count_str)
		total_count = int(total_count_str)

		other_count = total_count - (yes_count + no_count)
		self.debug("VVV-BB %s[%s] %s Yes/No/Other %d/%d/%d %s %s %s" % (bill_id, action, result, yes_count, no_count, other_count,
vote_date_time, link_to_votes, link_to_votes_href 
) )

#		self.debug("VVV-BB %s [%s] %s LINK_TO_VOTES[%s] HREF[%s] %s" % (bill_id, action, vote_date_time, link_to_votes, link_to_votes_href, result ))

		#vote_date = vote_date_time.split()[0]
		vote_date_1 = vote_date_time.split()
		vote_date = " ".join(vote_date_1)

		motion = result
		passed = result.find("Passed") != -1
		vote = Vote(chamber, vote_date, motion, passed, yes_count, no_count, other_count )
						#use default for type

		# PARSING ONLY WORKS FOR lower now
		if link_to_votes_href and chamber == "lower":
		   bill.add_source(link_to_votes_href)
		   billnum = re.search("(\d+)", bill_id).group(1)
		   # Save pdf to a local file
		   temp_file = tempfile.NamedTemporaryFile(delete=False,suffix='.pdf',prefix="votetmp_%s_"%billnum )
		   otemp_file = tempfile.NamedTemporaryFile(delete=False,suffix='.txt',prefix="vote_text_%s_"%billnum )
		   try:
			with self.urlopen(link_to_votes_href) as whatever:
				pdf_file = file(temp_file.name, 'w')
				pdf_file.write(whatever)
				pdf_file.close()

			outfp = file(otemp_file.name, 'w')

			rsrcmgr = PDFResourceManager(caching=True)
			laparams = LAParams()
			codec = 'utf-8'
			device = TextConverter(rsrcmgr, outfp, codec=codec,laparams=laparams)

			fp = open(temp_file.name,'rb')
			process_pdf(rsrcmgr, device, fp )
			device.close()
			outfp.close()

			# at this point, the votes are in text format in 
			#file = open("sample_vote_file.txt","r")
			vfile = open(otemp_file.name,"r")
			vdata = vfile.read()
			vfile.close()

			(expected, areas, yays, nays, other) = self.parse_rollcall(vdata)
			#self.debug("VVV-XX %s yays %s" % (bill_id, yays))
			#message = "bill %s file %s" % (bill_id,otemp_file.name)
			#self.print_vote_sections(message, expected, areas)

	  		for legislator in yays:
				vote.yes(legislator)
	  		for legislator in nays:
				vote.no(legislator)

    			#self.add_vote_nays(vote,bill_id,nays)
		   except Exception as error:
			self.warning("VVV-XX CC %s FAILED %s " % ( bill_id, traceback.format_exc()) ) 
			#self.warning("CC Failed to get votes for bill[%s] %s" % (bill_id, error))

		bill.add_vote(vote)
				
		date = datetime.datetime.strptime(vote_date, "%m/%d/%Y %I:%M %p")
		date = date.date()
		bill.add_action(chamber, action, date, type=action_type(action) )



    ###################################################
    def split_page_into_parts(self, data):
	"""
	Return a tuple containing: similar list, summary, after_summary
	"""

	#self.debug("VVV AAA Data==[%s]\n========" % data)
	similar_to_list, after_summary, summary = [], None, None

	sim = re.match("Similar (.+)\n",data)
	if sim:
		for part in sim.group(1).split(","):
			simparts_pat = re.compile('\(<A HREF=".+">(.+)</A>\)')
			#self.debug("VVV CCC Part==[%s]\n========" % part)
			sr = simparts_pat.match( part.strip() )
			if sr:
				similar_to_list.append( sr.group(1) )
		data = data[sim.end():]

	bb = data.find("<A HREF")
	if bb != -1:
		summary = re.sub(r'\s+', ' ', data[1:bb])
		after_summary = data[bb:]
	else:
		summary = re.sub(r'\s+', ' ', data)

	return ( similar_to_list, summary, after_summary )


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
	#self.debug( "DETAILS PRE (%d,%d) [%s] " % (pre_start, pre_stop, pre_section))

	data = pre_section
	vurl = None
	
	date_re = re.compile("\d\d/\d\d/\d\d")

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
		spondata = data[:results1.start()]
		mysponsors = sponsorsToList( spondata )
		#self.debug("QQQ SPONSOR ORIG |%s| becomes |%s|" % (spondata, mysponsors))
		for s in mysponsors:
			if s in self.people:
				#self.log( "DETAIL SPONSOR FOUND [%s]=[%s]" % (s,self.people[s]) )
				newspon.append(self.people[s])
			else:
				self.debug( "DETAIL [%s] SPONSOR NOT FOUND [%s]" % (bill_id,s) )
				newspon.append(s)
		data = data[results1.end():]
		
	linenum = 0
	bill_summary = ""
	apat = re.compile(">(H|S) (\d*)<")
	billpat = re.compile("(\d+)")

	(similar_bills,summary,after_summary) = self.split_page_into_parts(data)
	#self.debug("VVV: %s Similar List %s " % (bill_id,similar_bills) )
	#self.debug("VVV: %s Summary len %d %s " % (bill_id,len(summary),summary) )
	#self.debug("VVV: %s After %d %s " % (bill_id,len(after_summary), after_summary) )

	bill_summary = summary.strip() 
	try:
		bs = bill_summary.decode('utf8')
	except:
		self.log("scrubbing %s summary, originally %s" % (bill_id,bill_summary) )
		bill_summary = removeNonAscii(bill_summary)

	bill = Bill(session, chamber, bill_id, bill_summary, type=bill_type(bill_summary))
		
	parse_state = 1
	for line in after_summary.splitlines():
		#self.debug("   DETAILS parse_state: %d %d line |%s|" % (linenum, parse_state,line)) 
		if parse_state == 1: 
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
				parse_state = 2
		elif parse_state == 2:
			date_results = date_re.search(line)
			if date_results:
				the_date = date_results.group(0)
				date = datetime.datetime.strptime(the_date, "%m/%d/%y")
				date = date.date()
				action = line.partition("(")[0]
				bill.add_action(chamber, action, date, type=action_type(action) )
				#self.debug( "     bill %s action: %s %s" % (bill_id,the_date,action))
		linenum += 1


	if similar_bills:
		#self.debug("similar %s %s" % (bill_id, similar_bills))
		bill['similar'] = similar_bills
		
	sponsors = newspon 

	bill.add_source(bill_detail_url)

	for sponsor in sponsors:
		bill.add_sponsor("sponsor", sponsor )

	if vurl:
		try:
	    		self.scrape_vote_detail( vurl, chamber, bill, bill_id )
			bill.add_source(vurl)
		except Exception as error:
			self.warning("VVV-BB FAILED TO SCRAPE VOTE %s" % error )

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

	self.initLegislators()

	bill_index_url = self.urls[chamber]['daily-bill-index']

	days = []
	with self.urlopen( bill_index_url ) as page:
		page = lxml.html.fromstring(page)
		page.make_links_absolute(bill_index_url)
		days = [str(link.attrib['href']) for link in page.find_class('contentlink')]

	self.log( "Session days: %d" % len(days) )

	bills_with_votes = []
	vhistory_url = self.urls[chamber]['vote-history']
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
		#self.log("Processing [%s]" % bill_id)
		pat = regexp.search(bill_id)
		if not pat:
			self.warning( "383 Missing billid [%s]" % bill_id )
			continue

		bn = pat.group(0)
		dtl_url = self.urls['bill-detail'] % (bn,session)

		#self.debug("447 detail %s %s" % (bn,dtl_url) )
		with self.urlopen(dtl_url) as page:
			self.scrape_details( dtl_url, session, chamber, bill_id, page)

	self.log( "Total bills processed: %d : " % len(all_bills) )
