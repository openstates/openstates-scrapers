import re
import datetime
import itertools

from billy.scrape import NoDataForPeriod
from billy.scrape.votes import VoteScraper, Vote
import lxml.html

class MNVoteScraper(VoteScraper):
    state = 'mn'

    yeanay_re = re.compile(r'(\d+) YEA and (\d+) Nay')
    date_re = re.compile(r'Date: (\d+/\d+/\d+)')

    def scrape(self, chamber, session):
        self.validate_session(session)
        votes_url = self.metadata['session_details'][session].get('votes_url')
        if not votes_url:
            self.warning('no house votes URL for %s', session)
            return
        with self.urlopen(votes_url) as html:
            doc = lxml.html.fromstring(html)
            prefix = {'lower': 'H', 'upper': 'S'}[chamber]
            xpath = '//a[contains(@href, "votesbynumber.asp?billnum=%s")]' % prefix
            links = doc.xpath(xpath)
            for link in links:
                bill_id = link.text
                link_url = link.get('href')
                self.scrape_votes(chamber, session, bill_id, link_url)

    def scrape_votes(self, chamber, session, bill_id, link_url):
        with self.urlopen(link_url) as html:
            doc = lxml.html.fromstring(html)
            for vote_url in doc.xpath('//a[starts-with(text(), "View Vote")]/@href'):
                self.scrape_vote(chamber, session, bill_id, vote_url)

    def scrape_vote(self, chamber, session, bill_id, vote_url):
        NO_VOTE_URL = 'http://www.house.leg.state.mn.us/votes/novotefound.asp'
        with self.urlopen(vote_url) as html:

            # sometimes the link is broken, will redirect to NO_VOTE_URL
            if html.response.url == NO_VOTE_URL:
                return

            doc = lxml.html.fromstring(html)
            paragraphs = doc.xpath('//h1/following-sibling::p')

            # first paragraph has motion and vote total
            top_par = paragraphs[0].text_content()
            lines = top_par.splitlines()
            # 3rd line is the motion except in cases where first line is gone
            motion = lines[2] or lines[1]
            # last line is "__ YEA and __ Nay"
            yeas, nays = self.yeanay_re.match(lines[-1]).groups()
            yeas = int(yeas)
            nays = int(nays)

            # second paragraph has date
            date = self.date_re.match(paragraphs[1].text_content()).groups()[0]
            date = datetime.datetime.strptime(date, '%m/%d/%Y')

            vote = Vote('lower', date, motion, yeas>nays, yeas, nays, 0,
                        session=session, bill_id=bill_id, bill_chamber=chamber)
            vote.add_source(vote_url)

            # first table has YEAs
            for name in doc.xpath('//table[1]/tr/td/font/text()'):
                vote.yes(name.strip())

            # second table is nays
            for name in doc.xpath('//table[2]/tr/td/font/text()'):
                vote.no(name.strip())

            self.save_vote(vote)
