from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html

class NECommitteeScraper(CommitteeScraper):
    state = 'nd'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            url_chamber_name = 'senate'
        else:
            url_chamber_name = 'house'

        
        committee_types = ["standing-comm", "pro-comm"]
        for committee in committee_types:
           url = "http://www.legis.nd.gov/assembly/%s/%s/%s/" % (term, url_chamber_name, committee)
           print url
