from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import lxml.html

class NECommitteeScraper(CommitteeScraper):
    state = 'ne'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        standing_comm()
   
   def select_comm(self):


   def standing_comm(self):
       main_url = 'http://www.nebraskalegislature.gov/committees/standing-committees.php'
       with self.urlopen(main_url) as page:
           page = lxml.html.fromstring(page)
           
           for comm_link in page.xpath(''):
