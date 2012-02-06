from billy.scrape.votes import VoteScraper, Vote
from billy.scrape.utils import url_xpath

import urllib
import lxml
import re

RI_URL_BASE = "http://www.rilin.state.ri.us"

class RIVoteScraper(VoteScraper):
    state = 'ri'

    def get_dates(self, page):
        dates = url_xpath( page, "//select[@name='votedate']" )[0].\
                xpath("./*")
        ret = [ a.text for a in dates ]
        return ret

    def get_votes(self, url):
        ret = []
        with self.urlopen(url) as html:
            p = lxml.html.fromstring(html)
            tables = \
                p.xpath("//td[@background='/images/capBG.jpg']/div/table")

            metainf = tables[0]
            table   = tables[1]

            inf = metainf.xpath("./tr/td/pre")[0]
            headers = [ br.tail for br in inf.xpath("./*") ]

            bill_s_n_no = r"(?P<year>[0-9]{4})(?P<chamber>[SH])\s*(?P<bill>[0-9]{4})"
            bill_metainf = None
            for h in headers:
                inf = re.search( bill_s_n_no, h )
                if inf != None:
                    bill_metainf = inf.groupdict()

            if bill_metainf == None:
                self.warning("No metainf for this bill. Aborting snag")
                return None

            for t in table.xpath("./tr/td"):
                votes = []
                nodes = t.xpath("./*")
                for node in nodes:
                    if node.tag == "span":
                        vote = node.text.strip()
                        name = node.tail.strip()
                        votes.append({
                            "name" : name,
                            "vote" : vote
                        })
                if len(votes) > 0:
                    ret.append( votes )
        return ret

    def parse_vote_page(self, page, context_url):
        p = lxml.html.fromstring(page)
        votes = p.xpath( "//center/div[@class='vote']" )
        for vote in votes:
            votes = self.get_votes( context_url + "/" +
                            vote.xpath("./a")[0].attrib["href"] )
            print votes

    def post_to(self, url, vote):
        headers = {
            "votedate" : vote
        }
        headers = urllib.urlencode( headers )
        return self.urlopen( url, method="POST", body=headers)

    def scrape(self, chamber, session):
        url = {
            "upper" : "%s/%s" % ( RI_URL_BASE, "SVotes" ),
            "lower" : "%s/%s" % ( RI_URL_BASE, "HVotes" )
        }
        url = url[chamber]
        action = "%s/%s" % ( url, "votes.asp" )
        dates = self.get_dates( url )
        for date in dates:
            self.parse_vote_page( self.post_to( action, date ), url )
