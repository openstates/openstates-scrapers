
filename = 'bill_812.htm' 

def find_end_of(line,pattern):
	match = line.find(pattern)
	if match != -1:
		return match + len(pattern)
	return match

# Returns a tuple with the bill id, sponsors, and blurb 
def extract_bill_data(data):

	pat1 = "font class=\"number\">"
	match = data.find(pat1)

	if match != 1:
		start = match + len(pat1)
		sample1 = data[start:]

		stop = sample1.find("<A HREF")

		stuff = sample1[:stop]
		#print 'extract_bill_data', stuff

		bill_name = None
		sponsor_names = None

		stop_bill_name = sample1.find("</font>")

		by_sponsor = find_end_of(sample1,", By");
		stop_bold = sample1.find("</b>")
		blurb = None

		if stop_bill_name != 1:
			bill_name = sample1[:stop_bill_name]
			#print 'Bill name is [%s]' %  (bill_name,)

			if by_sponsor > 0 and stop_bold > by_sponsor:
				sponsor_names = sample1[by_sponsor:stop_bold]
				tmp = sponsor_names.split()
				sponsor_names = " ".join(tmp).split(",")
				slist = []
				slist.extend(sponsor_names)
				sponsor_names = slist
				#print 'Sponsor names: ' , sponsor_names

		
			stop2 = sample1.find("</b>")
			if stop2 != 1 and stop != -1:
				stop2 = stop2 + len("</b>")
				blurb = sample1[stop2:stop]
				words = blurb.split()
				blurb = " ".join(words)
				#print 'sponsor and bill id ', blurb

		return ( bill_name, sponsor_names, blurb )

	return ()


try:
	f = open(filename,"r")
	data = f.read()
	bd = extract_bill_data(data)
	#print bd
	if len(bd) == 3:
		print "SUCCESS: \nBill[%s] \nSponsors[%s]\nBlurb: [%s]" % (bd)

except IOError:
	print 'Failed ', filename

