import re

def session_days_url(chamber):
	"""Returns the url which contains the list of day that have been
	in session.  There will be a link for each day that the chamber
	was in session.
	"""

	if chamber == "upper":
	        url = "http://www.scstatehouse.gov/sintro/sintros.htm"
	else:
	        url = "http://www.scstatehouse.gov/hintro/hintros.htm"
	return url



# extracts senators from string.
#   Gets rid of Senator(s) at start of string, 
#   Senator last names are separated by commas, except the last two 
#   are separated by the word 'and'
#   handles ' and '
def corrected_sponsor(orig):
	"""Takes a string containing list of sponsors.
	returns a list of sponsors
	"""

	#print '25 TAMI corrected_sponsor [%s]\n' % orig
	sponsors = []
	parts = orig.split()

	if orig.startswith("Senators"):
		sparts = orig.split("Senators",1)
		parts = sparts[1:]
		orig = " ".join(sparts[1:])

	elif orig.startswith("Senator"):
		sparts = orig.split("Senator",1)
		parts = sparts[1:]
		orig = " ".join(sparts[1:])

#	if orig.startswith("Senator") and len(parts) >= 2:
#		print '|', orig, '| returning ', parts[1]
#		this_sponsor = " ".join(parts[1:])
#		print 'TAMI corrected_sponsor [%s] this_sponsor [%s]\n' % (orig,str(this_sponsor))
#		sponsors.append(" ".join(parts[1:]))
#		print 'TAMI corrected_sponsor [%s] return [%s]\n' % (orig,str(sponsors))
#		return sponsors

	if orig.startswith("Reps."):
		start = len("Reps.")
		orig = orig[start:]

	if orig.startswith("Rep."):
		start = len("Rep.")
		orig = orig[start:]

	if len(parts) == 1:
		sponsors.append(parts[0].strip())
		return sponsors

	#print 'orig ' , orig , ' parts ', len(parts)
	and_start = orig.find(" and ")
	if and_start > 0:
		left_operand = orig[1:and_start]
		right_start = and_start + len(" and ")
		right_operand = orig[right_start:]

		sponsors.append(left_operand.strip())
		sponsors.append(right_operand.strip())
		return sponsors
	else:
		sponsors.append(orig.strip())
	#print '71 TAMI corrected_sponsor [%s] return [%s]' % (orig,str(sponsors))
	return sponsors


def sponsorsToList(str):
	sponsor_names = " ".join(str.split()).split(",")

	sponlist = []
	for n in sponsor_names:
		sponlist.extend( corrected_sponsor(n) )
	return sponlist

# vote url - contains all votes for a bill, including links to drill down on specific bill actions
def vote_url(bill_number):
	return "http://www.scstatehouse.gov/php/votehistory.php?type=BILL&session=119&bill_number=%s" % bill_number 

# vote url - page with all bills with their pass/fail vote summaries with links to specific votes
def vote_history_url(chamber):
	house_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=H"
	senate_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=S"

	if chamber == "lower":
		return house_url
	else:
		return senate_url


def removeNonAscii(s):
	return "".join(i for i in s if ord(i)<128)


def action_type(action):
	action = action.lower()
	atypes = []
	if re.match('^read (the )?(first|1st) time', action):
		atypes.append('bill:introduced')
		atypes.append('bill:reading:1')

	if re.match('^referred to the committee', action):
		atypes.append('committee:referred:1')

	if atypes:
		return atypes

	return ['other']



def bill_type(s):
	action = s.lower()
	if re.match('house resolution', s):
		return 'resolution'

	if re.match('senate resolution', s):
		return 'resolution'

	if re.match('concurrent resolution', s):
		return 'joint resolution'

	if re.match('joint resolution', s):
		return 'joint resolution'

	return 'bill'


def scrape_bill_details(data):
	
	#print 'DETAILS scrape bill details '

	bill_number, sponsors = None, None
	
	pat1 = re.compile(r'</FORM>')
	results = pat1.search(data)
	#print "results = ", results
	#print "DETAILS FORM results = ", results.start() ,  " " , results.end()
	data = data[results.end():]

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

	if results != None and results1 != None:
		sponsors = data[:results1.start()]
		print "DETAIL SPONSORS: [", data[:results1.start()].strip(), "]"
		billattr['sponsors'] = data[:results1.start()].strip()
		data = data[results1.end():]
		
	print "DETAILS ", data
	linenum = 0
	state = 0
	bill_summary = ""
	apat = re.compile(">(H|S) (\d*)<")
	
	prestart = data.find("<pre>") + len("<pre>")
	prestop = data.find("</pre>",prestart)
	data = data[prestart:prestop]
	
	similar_bills = []
	actions = []
	for line in data.splitlines():
		#print "DETAILS GOT LINE ", linenum, " ", line
		if linenum < 10000:
			#print "      DETAILS state: ", state, " line ", line
			if state == 0: 
				result1 = apat.search(line)
				if result1:
					sbill = dict()	
					sbill['bill_number' ] = result1.group(2)
					sbill['bill_suffix' ] = result1.group(1)
					sbill['bill_name' ] = "%s %s" % (result1.group(1), result1.group(2))
					similar_bills.append(sbill)
					#print "line [", line, "]"
				else:
					bill_summary += line	
				state = 1
			elif state == 1:
				if line.find("<A HREF") >= 0:
					state = 2
				else:
					bill_summary += line
			elif state == 2:
				if line.find("View full text"):
					state = 3
				else:
					date_results = date_re.search(line)
					if date_results:
						the_date = date_results.group(0)
						m = "THE DATE %s line %s" % (the_date,line)
						actions.append(m)
						print '1 QQQQ THE DATE LINE  ', date_results.group(0)
					else:
						actions.append(line)
			elif state == 3:
					print 'QQQQ ACTION LINE  ', line
					if line.find("</pre>"):
						state = 4
					date_results = date_re.search(line)
					if date_results:
						the_date = date_results.group(0)
						m = "THE DATE %s line %s" % (the_date,line)
						actions.append(m)
						print '2 QQQQ THE DATE LINE  ', date_results.group(0)
					else:
						actions.append(line)
		linenum += 1

	#print '= Bill DETAIL ========================'
	#print "Bill summary ", bill_summary.strip() 
	if similar_bills:
		billattr['similar'] = similar_bills
		
	if actions:
		billattr['actions'] = actions
		
	billattr['summary'] = bill_summary.strip()
	return billattr


