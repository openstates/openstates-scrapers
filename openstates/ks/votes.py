import billy.scrape.votes

import re
import datetime

import lxml.html

class KSVoteScraper(billy.scrape.votes.VoteScraper):
	state = 'ks'
