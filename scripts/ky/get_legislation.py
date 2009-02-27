import urllib, urllib2
import re
import time
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import LegislationScraper

class KentuckyScraper(LegislationScraper):
    def scrape_legislation(self, chamber, year, download):
        # this needs to call scrape_session
        # sessions = ['%sRS','%sSS','%sS2']
        pass

    def scrape_session(self, chamber, session, download):
        if chamber == 'upper':
            chamber_abbr = 'H'
            bill_abbr = 'HB'
        elif chamber == 'lower':
            chamber_abbr = 'S'
            bill_abbr = 'SB'

        local_filename = ''
        index_file = "http://www.lrc.ky.gov/recarch/%s/bills_%s.htm" % (session, chamber_abbr)
        req = urllib2.Request(index_file)
        response = urllib2.urlopen(req)
        doc = response.read()
        soup = BeautifulSoup(doc)
        re_str = "%s\d{1,4}.htm" % bill_abbr
        links = soup.findAll(href=re.compile(re_str))

        for link in links:
            bill_id = link['href'].replace('.htm', '')
            bill_url = "http://www.lrc.ky.gov/recarch/%s/%s" % (session, link['href'])

            if download:
                local_filename = 'data/ky/legislation/%s%s%s.htm' % (chamber, session, bill_id) 
                urllib.urlretrieve(bill_url, local_filename)
                time.sleep(0.5)

            self.add_bill('KY', chamber, session, bill_id, bill_url, local_filename)

if __name__ == '__main__':
    KentuckyScraper('test.csv').run()
