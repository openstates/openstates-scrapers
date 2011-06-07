import re
import datetime
import contextlib

from .utils import action_type, bill_type
from .utils import removeNonAscii, sponsorsToList

from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

from pdfminer.pdfinterp import PDFResourceManager, process_pdf
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

import tempfile
import os
import sys, traceback

import lxml.html
from lxml import etree

#################################################################
# main class:
class SCBillScraper(BillScraper):
    state = 'sc'
    urls = {
	'bill-detail' : "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%s&session=%s" ,
	'vote-url' : "http://www.scstatehouse.gov/php/votehistory.php?type=BILL&session=%s&bill_number=%s",
	'vote-url-base' : "http://www.scstatehouse.gov",

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

    #################################################################
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
    def find_part( self, alist, line, start=0 ):
	for ii in range(start,len(alist)): 
		if line.find(alist[ii]) != -1:
			return ii
	return -1
	
    ###################################################
    def count_votes(self, url,chamber,bill_id,data):
   	house_sections =  [ 'FIRST', 'RESULT', 'Yeas:', 'YEAS', 'NAYS', 'EXCUSED ABSENCE', 'ABSTAIN', 'NOT VOTING', 'REST' ]
	senate_sections = [ 'FIRST', 'RESULT', 'Ayes:', 'AYES', 'NAYS', 'EXCUSED ABSENCE', 'ABSTAIN', 'NOT VOTING', 'REST' ]

	#print("195 parse_rollcall: %s %s" % (chamber,bill_id) )

	result_pat = re.compile("RESULT: (.+)$")

	house_yes_section, hyes = 'YEAS', 'Yeas:'
	senate_yes_section, syes = 'AYES', 'Ayes:'
	yes_section = house_yes_section

	#replace multiple lines with single lines?
	data = re.sub(r'\n+', '\n', data)

	lines = data.split("\n")
	#print("199 parse_rollcal: numlines %s %d" % (bill_id,len(lines)))

	if re.match("Senate", lines[0]):
		sections = senate_sections
		yes_section = senate_yes_section
	else:
		sections = house_sections
		yes_section = house_yes_section

	section, linenum, expected, areas = 0, 0, dict(), dict()
	for s in sections:
		areas[s] = []
		if not s in ['REST','FIRST','RESULT','Yeas:', 'Ayes:']:
			expected[s] = 0

	# Get the result line
	nlines = len(lines)
	result_pat = re.compile("RESULT: (.+)$")
	epat = re.compile("\w - (\d+)")
	#section_header_pat = re.compile("\w - (\d+)")
	done, vresult, vtitle = False, "", ""
	#while linenum < nlines and not done:
	while linenum < nlines and not result_pat.search(lines[linenum]):
		linenum += 1

	if linenum < nlines:
		result_match = result_pat.search( lines[linenum] )
		if not result_match:
			self.warning("failed to find RESULT")
			return
	else:
		self.warning("2 failed to find RESULT")
		return

	#self.debug("%s %d got result: %s |%s|" % (bill_id, linenum, result_match.group(1), lines[linenum]))
	vresult = result_match.group(1)

	# Get the summary line
	# Get the bill title line
	# get the YEAS line, starting adding to YEAS
	done = False
	while linenum < nlines and not done:
		line = lines[linenum]
		if line.find(sections[2]):
			self.debug ("%s %d got VOTE TOTALS section[%s] line|%s|" % (bill_id, linenum, sections[2], line ))
			linenum += 1
			vtitle = lines[linenum]
			done = True
		linenum += 1

	self.debug ("%s %d ==> VOTE |%s| |%s| " % (bill_id, linenum, vtitle, vresult ))

	current_expected = 0
	done = False
	while linenum < nlines and not done:
		line = lines[linenum]
		result_match = epat.search( lines[linenum] )
		if result_match:
			#self.debug ("277 %s %d found result: %s |%s|" % (bill_id, linenum, result_match.group(1), line))
			current_expected = int(result_match.group(1))
			expected[ sections[3] ] = current_expected
			#self.debug 'set expected ', sections[3], ' to ', current_expected
			done = True
			section = 3
		linenum += 1

	skey = sections[section]

	done = False
	while linenum < nlines and not done:
		line = lines[linenum].strip()

		nn = self.find_part(sections, line, section )
		if nn != -1:
			#self.debug( "FOUND: %s linenum=%d line=|%s| section=%s"  % (nn, linenum, line, section ))

			# get specified value to verify we get them all
			eresult = epat.search(line)
			section_count = 0
			if eresult:
				section_count = int(eresult.group(1))

			skey = sections[nn]
			#self.debug 'found next section key=[', skey , '] count=', section_count
			expected[ skey ] = section_count
			#self.debug 'set expected ', skey, ' to ', section_count

			section = nn

		elif len(line) > 0 and not re.search("Page \d+ of \d+", line):
			# Skip page footer, Page x of Y
			possible = line.split("  ")
			nonblank = [s.strip() for s in possible if len(s) >0]
			areas[skey].extend(nonblank) 

		linenum += 1

	counts_match, counts_in_error, expected_counts_in_error, area_errors = True, 0, 0, [] 
	self.debug ("EXPECTED %s " % expected )
	for k in expected.keys():
		v = areas[k]
		expected_len = expected[k]
		#self.debug("%s count AREAS %s %d expected %d" % (bill_id, k, len(v), expected_len ) )
		if len(v) != expected[k]:
			self.warning ("***** ERROR %s VOTE COUNT FOR %s: Got %d expected %d (%s)" % (bill_id, k, len(v) , expected[k], v ) )
			counts_match = False
			counts_in_error += len(v)
			expected_counts_in_error += expected_len
			area_errors.append(k)

	if counts_match:
		yays = areas[ yes_section ]
		nays = areas['NAYS']
		other = areas['EXCUSED ABSENCE'] 
		other.extend( areas['NOT VOTING'] )
		msg = "SUCCESSFUL (y/n/o) (%d/%d/%d)" % (len(yays), len(nays), len(other) )
		self.debug ("%s %s ROLL_CALL %s: %s" % (bill_id, chamber, msg, url) )
	else: 
		yays = []
		nays = []
		other = []
		self.warning("%s %s ROLL_CALL FAILED: %s" % (bill_id, chamber, url) )

	return (expected, areas, yays, nays, other )


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

    ###################################################
    def extract_rollcall_from_pdf(self,chamber,vote, bill, url,bill_id):
	billnum = re.search("(\d+)", bill_id).group(1)
	self.debug("Scraping rollcall %s|%s|" % (billnum, url) )

	bill_prefix = "vote_%s_%s_"  % (chamber, re.sub(r'\s+', '_', bill_id ))

	bill.add_source(url)
	#billnum = re.search("(\d+)", bill_id).group(1)

	# Save roll call pdf to a local file
	temp_file = tempfile.NamedTemporaryFile(delete=False,suffix='.pdf',prefix=bill_prefix )
	pdf_temp_name = temp_file.name

	# Save converted text to a local file
	#otemp_file = tempfile.NamedTemporaryFile(delete=False,suffix='.txt',prefix=bill_prefix )
	#txt_temp_name = otemp_file.name

	#self.debug("Parsing pdf votes, saving to tempfile [%s] textfile=[%s]" % (temp_file.name, otemp_file.name))
	self.debug("Parsing pdf votes, saving to tempfile [%s]" % temp_file.name)
	with self.urlopen(url) as pdata:
		pdf_file = file(pdf_temp_name, 'w')
		pdf_file.write(pdata)
		pdf_file.close()

	# NOW WE HAVE THE PDF SAVE IN A TEMP FILE
	rollcall_data  = convert_pdf(pdf_temp_name, type='text')
	(expected, areas, yays, nays, other) = self.count_votes(url,chamber,bill_id,rollcall_data)
	#(expected, areas, yays, nays, other) = self.count_votesparse_rollcall(chamber,bill_id,vdata)
	self.debug("VOTE 370 %s %s yays %d nays %d other %d pdf=%s" % (bill_id, chamber, len(yays), len(nays), len(other), pdf_temp_name ) )

	os.unlink(pdf_temp_name)

  	for legislator in yays:
		#self.debug("VOTE %s YES %s" % (bill_id,legislator))
		vote.yes(legislator)
  	for legislator in nays:
		#self.debug("VOTE %s NAY %s" % (bill_id,legislator))
		vote.no(legislator)
  	for legislator in other:
		#self.debug("VOTE %s OTHER %s" % (bill_id,legislator))
		vote.other(legislator)

    ###################################################
    def extract_vote_rows(self, bill_id,fb ):

	vote_data = []

	tables = fb.xpath("//div/div/table")
	if len(tables) > 1:
		#self.debug("TABLE HANDL VOTE: %s " % etree.tostring(tables[1]))
		fb = tables[1]
		rows = fb.xpath("tr")
	else:
		self.warning("problem handling vote history div")
		return vote_data

	if len(rows) >= 3:
		header_row = rows[0]
		data_row = rows[2]

		rowtd = data_row.xpath("td")
		rowth = header_row.xpath("th")

		for rr in range(2,len(rows)):
			data_row = rows[rr]
			rowtd = data_row.xpath("td")
			item = dict()
			for ii in range(0,len(rowtd)):
				links = rowtd[ii].xpath("a/@href")
				if len(links) == 1:
					#self.debug("item %d LINKS %s s" % (ii, links ) )
					item['vote_link'] = links[0]
				
				key = rowth[ii].text_content()
				value = rowtd[ii].text_content()
				item[key] = value
	
			vote_data.append(item)
		
	else:
		self.warning("Failed to parse vote hisstory div, expecting 3 rows")
		return []

	self.debug("VOTE_DATA %s returning %d items, %s" % (bill_id, len(vote_data), vote_data))
	return vote_data

    ###################################################
    def scrape_vote_history(self, vurl, chamber, bill, bill_id ):
	"""Get information from the vote history page.

	The bill title will appear. If this is shorter than the bill title we have,
	add it to the bill.

	Collect data for each vote row, which will have a link to the pdf file containing the votes,
		the motion, the counts (yeas,nays,etc).
	
	For each vote row, fetch the pdf and extract the votes.  Add this vote information to the bill.

	"""
	#self.debug("ENTER VOTE %s scrape_vote_history: (%s,%s)" % (bill_id,vurl,chamber))

	with self.urlopen( vurl ) as votepage:
		if votepage.find("No Votes Returned") != -1:
			return

		bill_title_xpath = "//div[@id='votecontent']/div[1]"
		fb_vxpath = '/html/body/table/tbody/tr/td/div[@id="tablecontent"]/table/tbody/tr/td[@class="content"]/div[@id="votecontent"]/div'
		doc = lxml.html.fromstring(votepage)
		doc.make_links_absolute(vurl)

		fb_vote_row = doc.xpath(fb_vxpath)

		if len(fb_vote_row) != 3:
			self.warning("vote history page, expected 3 rows, returning")
			return

		bname = fb_vote_row[0].text_content().strip()
		btitle = fb_vote_row[1].text_content().strip()
		#self.debug("GGGG %s name %s title %s" % (bill_id,bname,btitle))

		l1 = len(bill['title'])
		l2 = len(btitle)
		if l1 - l2 > 20 and l2 > 4 and l2 < l1:
			self.debug("%s Setting title: %s" % (bill_id,btitle))
			bill['alternate_title'] = btitle
			bill['short_title'] = btitle

		vote_details = self.extract_vote_rows(bill_id,fb_vote_row[2])

	#now everyting ins in vote_details
	for d in vote_details:
	   try:
		#self.debug("VOTE_HISTORY: Processing a vote: %s" % d)

		vote_date_time = d['Date/Time']
		motion = d['Motion']
		result = d['Result']

		# Get link to PDF containing roll call votes
		link_to_votes_href = d['vote_link']
		
		y, no, total_count = int(d['Yeas']), int(d['Nays']), int(d['Total'])

		other_count = total_count - (y + no)
		self.debug("VOTE %s[%s] %s Y/N/Other %d/%d/%d %s %s" % (bill_id, motion, result, y, no, other_count, vote_date_time, link_to_votes_href ) )

		vote_date_1 = vote_date_time.split()
		vote_date = " ".join(vote_date_1)

		vvote_date = datetime.datetime.strptime(vote_date, "%m/%d/%Y %I:%M %p")
		vvote_date = vvote_date.date()

		passed = result.find("Passed") != -1
		vote = Vote(chamber, vvote_date, motion, passed, y, no, other_count )
						#use default for type

		################################################
		if link_to_votes_href: 
		   bill.add_source(link_to_votes_href)
		   vote['pdf-source'] = link_to_votes_href
		   vote['source'] = link_to_votes_href
		   #billnum = re.search("(\d+)", bill_id).group(1)
		   try:
		   	self.extract_rollcall_from_pdf(chamber,vote,bill,link_to_votes_href,bill_id)
		   except Exception as error:
			self.warning("Failed while fetching votes bill=%s %s" % ( bill_id, traceback.format_exc()) ) 

		bill.add_vote(vote)
	   except Exception as error:
		#self.warning("VOTE_HISTORY: Processing a vote: %s" % d)
		self.warning("Failed while vote history bill=%s %s %s" % ( bill_id, d, traceback.format_exc()) ) 

	#self.debug("EXIT VOTE %s scrape_vote_history: (%s,%s)\n\n" % (bill_id,vurl,chamber))


    ###################################################
    def split_page_into_parts(self, data, session, bill_number):
	"""
	Data contains the content of a bill detail page.
	Return a tuple containing: 
		similar list, summary, after_summary, vote_url
	"""

	similar_to_list, after_summary, summary, vurl = [], None, None, None

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

		vh = after_summary.find("View Vote History")
		vh1 = after_summary.find("\n")
		#self.debug("VOTE (eol vh1: %d) (votehistory %d)" % (vh1, vh))
		if vh != -1: 
			vurl = self.urls['vote-url'] % (session,bill_number)
		if vh1 != -1:
			# skip to end of line
			after_summary = after_summary[vh1:]
	else:
		summary = re.sub(r'\s+', ' ', data)

	return ( similar_to_list, summary, after_summary, vurl )


    ###################################################
    def emit_bill(self, bill): 
	self.outfile = open("debug_bills.txt","a")
	self.outfile.write("%s,%s,%s\n" % (bill['chamber'],
			bill['session'], bill['bill_id'] ))
	self.outfile.close()

    ###################################################
    def process_rollcall(self,chamber,vvote_date,bill,bill_id,action):
	self.debug("508 Roll call: [%s]" % action )
	if re.search(action,'Ayes'):
		pat1 = re.compile('<a href="(.+)" target="_blank">Ayes-(\d+)\s+Nays-(\d+)</a>')
	else:
		pat1 = re.compile('<a href="(.+)" target="_blank">Yeas-(\d+)\s+Nays-(\d+)</a>')
	sr1 = pat1.search( action )
	if not sr1:
		self.debug("515 Roll call: NO MATCH " )
		return

	the_link = sr1.group(1)
	the_ayes = sr1.group(2)
	the_nays = sr1.group(3)

	vbase = self.urls['vote-url-base'] 
	vurl = "%s%s" % (self.urls['vote-url-base'], the_link)
	self.debug("\n\nVOTE 512 Roll call: link [%s] AYES [%s] NAYS[%s] vurl[%s]" % (the_link, the_ayes, the_nays, vurl ) )

	motion = "some rollcall action"
	yes_count = int(the_ayes)
	no_count = int(the_nays)
	other_count = 0
	passed = True
	vote = Vote(chamber, vvote_date, motion, passed, yes_count, no_count, other_count )
   	self.extract_rollcall_from_pdf(chamber,vote, bill,vurl,bill_id)
	self.debug("2 ADD VOTE %s" % bill_id)
	bill.add_vote(vote)


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
		self.warning("scrape_details(2) - unable to parse (no <pre>) |%s|\n|%s|"  % (bill_detail_url,page))
		return

	pre_stop = page.find("</pre>",pre_start)
	if pre_stop == -1:
		raise ScrapeError("scrape_details(3) - unable to parse (no </pre>) %s"  % bill_detail_url)

	pre_section = page[pre_start:pre_stop]
	#self.debug( "DETAILS PRE (%d,%d) [%s] " % (pre_start, pre_stop, pre_section))

	data = pre_section
	vurl = None
	
	action_line_re = re.compile(r'(\d\d/\d\d/\d\d)\s+(\w+)\s+(.+)')

	pat2 = re.compile(r' By ')
	results = pat2.search(data)
	if results != None:
		bystuff = data[results.start():results.end()]
		data = data[results.end():]

	pat3 = re.compile(r'</b>')
	results1 = pat3.search(data)

	newspon = []
	if results != None and results1 != None:
		spondata = data[:results1.start()]
		mysponsors = sponsorsToList( spondata )
		for s in mysponsors:
			if s in self.people:
				#self.log( "DETAIL SPONSOR FOUND [%s]=[%s]" % (s,self.people[s]) )
				newspon.append(self.people[s])
			else:
				self.debug( "DETAIL [%s] SPONSOR NOT FOUND [%s]" % (bill_id,s) )
				newspon.append(s)
		data = data[results1.end():]
		
	apat = re.compile(">(H|S) (\d*)<")
	billpat = re.compile("(\d+)")
	bill_number = billpat.search(bill_id).group(0)

	(similar_bills,summary,after_summary,vurl) = self.split_page_into_parts(data,session, bill_number)
	self.debug("VVV: %s VOTE HISTORY URL %s " % (bill_id,vurl) )
	#self.debug("VVV: %s Similar List %s " % (bill_id,similar_bills) )
	#self.debug("VVV: %s Summary len %d %s " % (bill_id,len(summary),summary) )
	#self.debug("VVV: %s After %d %s " % (bill_id,len(after_summary), after_summary) )

	bill_summary = summary.strip() 
	try:
		bs = bill_summary.decode('utf8')
	except:
		self.log("scrubbing %s, originally %s" % (bill_id,bill_summary) )
		bill_summary = removeNonAscii(bill_summary)

	bill = Bill(session, chamber, bill_id, bill_summary, type=bill_type(bill_summary))
		
	linenum = 0
	for line in after_summary.splitlines():
		#get rid of the parenthesis
		action_line = line.partition("(")[0].strip()
		#r1 = action_line_re.search(action_line)
		r = action_line_re.search(action_line)

		if r:
			the_date = r.group(1)
			action_chamber = r.group(2)
			action = r.group(3)

			date = datetime.datetime.strptime(the_date, "%m/%d/%y")
			date = date.date()
		
####
####			if re.search('Roll call', action):
####				self.debug("VOTE call roll call line %d %s" % (linenum,line))
####				self.process_rollcall(chamber,date,bill,bill_id,action)


			t = action_type(action)
			if t == ['other']:
				self.debug("OTHERACTION: bill %s %d Text[%s] line[%s]" % (bill_id,linenum,action,line))
			else:
				self.debug("ACTION: %s %d dt|ch|action [%s|%s|%s] [%s]" % (bill_id, linenum, the_date, action_chamber, action, str(t)))

			#self.debug("543 scrape details ACTION: [%s] is [%s]" % (action,t))
			bill.add_action(chamber, action, date, t )
			#self.debug( "     bill %s action: %s %s" % (bill_id,the_date,action))
		elif len(line) > 0:
			self.debug("Skipping line %d [%s] line:[%s]" % (linenum, bill_id, line))

		linenum += 1

	if similar_bills:
		#self.debug("similar %s %s" % (bill_id, similar_bills))
		bill['similar'] = similar_bills
		
	bill.add_source(bill_detail_url)

	for sponsor in newspon:
		bill.add_sponsor("sponsor", sponsor )

	if vurl:
		try:
	    		self.scrape_vote_history( vurl, chamber, bill, bill_id )
			bill.add_source(vurl)
			self.debug("Scraped votes: (chamber=%s,bill=%s,url=%s)" % (chamber,bill_id,vurl) )
		except Exception as error:
			self.warning("Failed to scrape votes: bill=%s %s" % ( bill_id, traceback.format_exc()) ) 
			self.warning("Failed to scrape votes: (chamber=%s,bill=%s,url=%s) %s" % (chamber,bill_id,vurl,error) )

	self.save_bill(bill)
	#self.emit_bill(bill)

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

	index_url = self.urls[chamber]['daily-bill-index']

	days = []
	with self.urlopen( index_url ) as page:
		page = lxml.html.fromstring(page)
		page.make_links_absolute(index_url)
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
	n = len(days) - 2
	#self.debug("days %s" % days )
	small = False
	if small and len(days) > 2:
		nn = 3 
		newdays = days[1:nn]
		self.debug("newdays %s" % newdays )
		days = newdays
		self.debug("Just looking at last %d days" % (len(days)) )

	for dayurl in days:
		self.debug( "processing day %s %s" % (dayurl,chamber) )
		with self.urlopen( dayurl ) as data:
			billids = self.recap(data)
			all_bills |= billids;
			self.debug( "  Day count: #bills %d all %d on %s" % (len(billids),len(all_bills),dayurl))
		
	regexp = re.compile( "\d+" )
	for bill_id in all_bills:
		pat = regexp.search(bill_id)
		if not pat:
			self.warning( "383 Missing billid [%s]" % bill_id )
			continue

		bn = pat.group(0)
		dtl_url = self.urls['bill-detail'] % (bn,session)

		with self.urlopen(dtl_url) as page:
			self.scrape_details( dtl_url, session, chamber, bill_id, page)

	self.log( "Total bills processed: %d : " % len(all_bills) )
