"""
Senate data prior to 105th session is not currently available on the TN site (2011-03-15)
"""


from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
class TNLegislatorScraper(LegislatorScraper):
    state = 'tn'
    
    urls = {
        '99th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/99GA/Members.htm',
            'upper': None,
            'version': 1
        },
        '100th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/100GA/Members.htm',
            'upper': None,
            'version': 1
        },
        '101st General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/101GA/Members.htm',
            'upper': None,
            'version': 1
        },
        '102nd General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/102GA/Members/Members.htm',
            'upper': None,
            'version': 1
        },
        '103rd General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/103GA/Members/HMembers.htm',
            'upper': None,
            'version': 1
        },
        '104th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/104GA/Members/HMembers.htm',
            'upper': None,
            'version': 1
        },
        '105th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/105GA/Members/HMembers.htm',
            'upper': 'http://www.capitol.tn.gov/senate/archives/105GA/Members/sMembers105a.htm',
            'version': 1
        },
        '106th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/archives/106GA/Members/index.html',
            'upper': 'http://www.capitol.tn.gov/senate/archives/106GA/Members/index.html',
            'version': 2
        },
        '107th General Assembly': {
            'lower': 'http://www.capitol.tn.gov/house/members/',
            'upper': 'http://www.capitol.tn.gov/senate/members/',
            'version': 3
        }
    }


    def scrape(self, chamber, term):
        url = self.urls[term][chamber]
        version = self.urls[term]['version']
        
        if url is None:
            raise NoDataForPeriod(term)
        
        with self.urlopen(url) as page:
            # FIXME: mark white's tr is missing, fixes invalid html
            page = page.replace('<td><a href="h83.html">White</a>, Mark </td>',
                            '<tr><td><a href="h83.html">White</a>, Mark </td>')
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
                if version >= 2:
                    party = row.xpath("td")[1].text_content().strip()
                    district = row.xpath("td")[3].text_content().replace("District ","").strip()
                    phone = email = ''
                    
                    if version >= 3:
                        phone = row.xpath("td")[6].text_content().strip()
                        email = row.xpath("td")[6].text_content().strip()
                else:
                    party, district = row.xpath("td")[1].text_content().split("-")
                    party = party.strip()
                    district = district.strip()
                    phone = email = ''
                
                leg = Legislator(term, chamber, district, fullname, party=party, email=email)
                leg.add_source(url)
                self.save_legislator(leg)
                
                
