from fiftystates.scrape import ScrapeError, NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html

class TNLegislatorScraper(LegislatorScraper):
    state = 'tn'
    urls = {
        '99th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/99GA/Members.htm',
            'upper': None
        },
        '100th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/100GA/Members.htm',
            'upper': None
        },
        '101st General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/101GA/Members.htm',
            'upper': None
        },
        '102nd General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/102GA/Members/Members.htm',
            'upper': None
        },
        '103rd General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/103GA/Members/HMembers.htm',
            'upper': None
        },
        '104th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/104GA/Members/HMembers.htm',
            'upper': None
        },
        '105th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/105GA/Members/HMembers.htm',
            'upper': 'http://www.capitol.tn.gov/senate/archives/105GA/Members/sMembers105a.htm'
        },
        '106th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/106GA/Members/index.html',
            'upper': 'http://www.capitol.tn.gov/senate/archives/106GA/Members/index.html'
        }
    }


    def scrape(self, chamber, term):
        url = self.urls[term][chamber]
        
        if url is None:
            #raise NoDataForPeriod(term)
            return 'Nuthin'
        
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            print page.text_content()
