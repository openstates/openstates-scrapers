
def sessionDaysUrl(chamber):
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
		left_operand = orig[1:and_start]
		right_start = and_start + len(" and ")
		right_operand = orig[right_start:]

		sponsors.append(left_operand)
		sponsors.append(right_operand)
		return sponsors
	else:
		sponsors.append(orig)
	return sponsors


def sponsorsToList(str):
	sponsor_names = " ".join(str.split()).split(",")

	sponlist = []
	for n in sponsor_names:
		sponlist.extend( corrected_sponsor(n) )
	return sponlist


def voteHistoryUrl(chamber):
	house_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=H"
	senate_url="http://www.scstatehouse.gov/php/votehistory.php?chamber=S"

	if chamber == "lower":
		return house_url
	else:
		return senate_url


def removeNonAscii(s):
	return "".join(i for i in s if ord(i)<128)
