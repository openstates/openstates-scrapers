from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

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
            raise NoDataForPeriod(term)
        
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            
            for row in page.xpath("//tr")[1:]:
                name = row.xpath("td")[0].text_content()
                name = name.split(",")
                if len(name) == 2:
                    fullname = "%s %s" % (name[1].strip(), name[0].strip())
                elif len(name) == 3:
                    fullname = "%s %s, %s" % (name[1].strip(), name[0].strip(), name[2].strip())
                else:
                    fullname = ' '.join(name).strip()
                
                # Most recent general assembly legislators list is slightly different than archived versions
                if term == "106th General Assembly":
                    party = row.xpath("td")[1].text_content().strip()
                    district = row.xpath("td")[3].text_content().replace("District ","").strip()
                else:
                    party, district = row.xpath("td")[1].text_content().split("-")
                    party = party.strip()
                    district = district.strip()
                
                leg = Legislator(term, chamber, district, fullname, party=party)
                leg.add_source(url)
                self.save_legislator(leg)
                
                
