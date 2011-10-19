from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html
import re

class NECommitteeScraper(CommitteeScraper):
    state = 'nd'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        #testing for chamber
        if chamber == 'upper':
            url_chamber_name = 'senate'
        else:
            url_chamber_name = 'house'

        #testing for starting year
        if int(term) == 62:
            start_year = 2011

        committee_types = ["standing-comm", "pro-comm"]
        for committee in committee_types:
           url = "http://www.legis.nd.gov/assembly/%s-%s/%s/%s/" % (term, start_year, url_chamber_name, committee)
           
           with self.urlopen(url) as page:
               page = lxml.html.fromstring(page)

               if committee == 'standing-comm':
                   self.scrapeStanding(chamber, page)
               else:
                   self.scrapeProcedural(chamber, page)

    def scrapeStanding(self, chamber, page):
        for comm_names in page.xpath('//div[@class="content"][1]/p/a/span'):
            name = re.sub('[^A-Za-z0-9]+', ' ', comm_names.text)
            print name

    def scrapeProcedural(self, chamber, page):
        for comm_names in page.xpath('//div[@class="content"][1]/p/a'):
            name = re.sub('[^A-Za-z0-9]+', ' ', comm_names.text)
            print name
