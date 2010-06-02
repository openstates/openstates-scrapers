import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.oh.utils import clean_committee_name

import lxml.etree

class OHLegislatorScraper(LegislatorScraper):
	state = 'oh'



	def scrape_legislators(self, chamber, year):
		if year != '2009':
			raise NoDataForYear(year)

		if chamber == 'upper':
			self.scrape_senators(year)
		else:
			self.scrape_reps()

	
	def scrape_reps(self):

		self.follow_robots = False;


		# There is only 99 districts and 1 representative for each district
		for district in range(1,100):

			rep_url = 'http://www.house.state.oh.us/components/com_displaymembers/page.php?district=' + str(district)
			with self.urlopen(rep_url) as (response, page):
				root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

				for el in root.xpath('//table[@class="page"]'):
					rep_link = el.xpath('tr/td/title')[0]
					full_name = rep_link.text
					district = el.xpath('string(tr/td[@class="info"]/strong)')
					party = el.xpath('string(tr/td/h2/[@class="title"]/div')[-1]

					leg = Legislator( '128', 'lower', district, full_name, party)
					leg.add_source(rep_url)


			
				self.save_legislator(leg)

