import re

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

