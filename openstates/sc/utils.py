
#senate_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=S"
#house_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=H"

def get_session_days_url(chamber):
	"""Returns the url which contains the list of day that have been
	in session.  There will be a link for each day that the chamber
	was in session.
	"""

	if chamber == "upper":
	        url = "http://www.scstatehouse.gov/sintro/sintros.htm"
	else:
	        url = "http://www.scstatehouse.gov/hintro/hintros.htm"
	return url


def get_bill_detail_url(billnum):
	"Location of static html page containing bill details."

	# another option
	# billurl = "http://scstatehouse.gov/cgi-bin/web_bh10.exe?bill1=%d&session=119" % billnum
	return "http://scstatehouse.gov/sess119_2011-2012/bills/%d.htm" % billnum


# extracts senators from string.
#   Gets rid of Senator(s) at start of string, 
#   Senator last names are separated by commas, except the last two 
#   are separated by the word 'and'
#   handles ' and '
def corrected_sponsor(orig):
	"""Takes a string containing list of sponsors.
	returns a list of sponsors
	"""

	sponsors = []
	parts = orig.split()
	if orig.startswith("Senator") and len(parts) >= 2:
		#print '|', orig, '| returning ', parts[1]
		sponsors.append(" ".join(parts[1:]))
		return sponsors

	if orig.startswith("Reps."):
		start = len("Reps.")
		orig = orig[start:]

	if orig.startswith("Rep."):
		start = len("Rep.")
		orig = orig[start:]

	if len(parts) == 1:
		sponsors.append(parts[0])
		return sponsors

	#print 'orig ' , orig , ' parts ', len(parts)
	and_start = orig.find(" and ")
	if and_start > 0:
		#print 'has and |', orig, '|'
		left_operand = orig[1:and_start]
		right_start = and_start + len(" and ")
		right_operand = orig[right_start:]

		sponsors.append(left_operand)
		#print ' ===> LEFT |', left_operand, '|'
		sponsors.append(right_operand)
		#print ' ===> RIGHT |', right_operand, '|'

		#print  ' returning ', sponsors 
		return sponsors
	else:
		sponsors.append(orig)
	return sponsors


def sponsorsToList(str):
	#print '\n========================\nsponsorsToList: ENTER ', str, '\n\n'

	tmp = str.split()
	sponsor_names = " ".join(tmp).split(",")

	sponlist = []
	for n in sponsor_names:
		sponlist.extend( corrected_sponsor(n) )

	#print '\n\nRETURNING the results is : ', sponlist
	#print "************************************\n\n"
	return sponlist


def get_vote_history_url(chamber):
	house_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=H"
	senate_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=S"

	if chamber == "lower":
		return house_url
	else:
		return senate_url


def removeNonAscii(s):
	return "".join(i for i in s if ord(i)<128)
