import re
import datetime
import itertools

from billy.scrape import NoDataForPeriod
from billy.scrape.votes import VoteScraper, Vote
import lxml.html

class MNVoteScraper(VoteScraper):
    jurisdiction = 'mn'

    yeanay_re = re.compile(r'(\d+) YEA and (\d+) Nay')
    date_re = re.compile(r'Date: (\d+/\d+/\d+)')

    def scrape(self, chamber, session):
        self.validate_session(session)
        votes_url = self.metadata['session_details'][session].get('votes_url')
        if not votes_url:
            self.warning('no house votes URL for %s', session)
            return
        html = self.get(votes_url).text
        doc = lxml.html.fromstring(html)
        prefix = {'lower': 'H', 'upper': 'S'}[chamber]
        xpath = '//a[contains(@href, "votesbynumber.asp?billnum=%s")]' % prefix
        links = doc.xpath(xpath)
        for link in links:
            bill_id = link.text
            link_url = link.get('href')
            self.scrape_votes(chamber, session, bill_id, link_url)

    def scrape_votes(self, chamber, session, bill_id, link_url):
        html = self.get(link_url).text
        doc = lxml.html.fromstring(html)
        for vote_url in doc.xpath('//a[starts-with(text(), "View Vote")]/@href'):
            self.scrape_vote(chamber, session, bill_id, vote_url)

    def scrape_vote(self, chamber, session, bill_id, vote_url):
        NO_VOTE_URL = 'http://www.house.leg.state.mn.us/votes/novotefound.asp'
        resp = self.get(vote_url)
        html = resp.text

        # sometimes the link is broken, will redirect to NO_VOTE_URL
        if resp.url == NO_VOTE_URL:
            return

        doc = lxml.html.fromstring(html)
        try:
            motion = doc.xpath("//div[@id='leg_PageContent']/div/h2/text()")[0]
        except IndexError:
            self.logger.warning("Bill was missing a motion number, skipping")
            return


        vote_count = doc.xpath(".//div[@id='leg_PageContent']/div/h3/text()")[1].split()
        yeas = int(vote_count[0])
        nays = int(vote_count[3])

        # second paragraph has date
        paragraphs = doc.xpath(".//div[@id='leg_PageContent']/div/p/text()")
        date = None
        for p in paragraphs:
            try:
                date = datetime.datetime.strptime(p.strip(), '%m/%d/%Y')
                break
            except ValueError:
                pass
        if date is None:
            self.logger.warning("No date could be found for vote on %s" % motion)
            return


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
