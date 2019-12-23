import re
import datetime

import lxml.html

from pupa.scrape import Scraper, VoteEvent

VOTES_URLS = {
    "2009-2010": "http://www.house.leg.state.mn.us/votes/getVotesls86.asp",
    "2010 1st Special Session": "http://www.house.leg.state.mn.us/votes/getVotesls8620101.asp",
    "2011-2012": "http://www.house.leg.state.mn.us/votes/getVotesls87.asp",
    "2011s1": "http://www.house.leg.state.mn.us/votes/getVotesls8720111.asp",
    "2012s1": "http://www.house.leg.state.mn.us/votes/getVotesls8720121.asp",
    "2013-2014": "http://www.house.leg.state.mn.us/votes/getVotesls88.asp",
    "2013s1": "http://www.house.leg.state.mn.us/votes/getVotesls8820131.asp",
    "2015-2016": "http://www.house.leg.state.mn.us/votes/getVotesls89.asp",
    "2015s1": "http://www.house.leg.state.mn.us/votes/getVotesls8920151.asp",
    "2017-2018": "http://www.house.leg.state.mn.us/votes/getVotesls90.asp",
    "2017s1": "http://www.house.leg.state.mn.us/votes/getVotesls9020171.asp",
}


class MNVoteScraper(Scraper):
    # bad SSL as of August 2017
    verify = False

    date_re = re.compile(r"Date: (\d+/\d+/\d+)")

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber else ["upper", "lower"]

        votes_url = VOTES_URLS.get(session)
        if not votes_url:
            self.warning("no house votes URL for %s", session)
            return
        html = self.get(votes_url).text
        doc = lxml.html.fromstring(html)
        for chamber in chambers:
            prefix = {"lower": "H", "upper": "S"}[chamber]
            xpath = '//a[contains(@href, "votesbynumber.asp?billnum=%s")]' % prefix
            links = doc.xpath(xpath)
            for link in links:
                bill_id = link.text
                link_url = link.get("href")
                yield from self.scrape_votes(chamber, session, bill_id, link_url)

    def scrape_votes(self, chamber, session, bill_id, link_url):
        html = self.get(link_url).text
        doc = lxml.html.fromstring(html)
        for vote_url in doc.xpath('//a[starts-with(text(), "View Vote")]/@href'):
            yield from self.scrape_vote(chamber, session, bill_id, vote_url)

    def scrape_vote(self, chamber, session, bill_id, vote_url):
        NO_VOTE_URL = "http://www.house.leg.state.mn.us/votes/novotefound.asp"
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
                date = datetime.datetime.strptime(p.strip(), "%m/%d/%Y").date()
                break
            except ValueError:
                pass
        if date is None:
            self.logger.warning("No date could be found for vote on %s" % motion)
            return

        vote = VoteEvent(
            chamber="lower",
            start_date=date,
            motion_text=motion,
            result="pass" if yeas > nays else "fail",
            classification="passage",
            legislative_session=session,
            bill=bill_id,
            bill_chamber=chamber,
        )
        vote.set_count("yes", yeas)
        vote.set_count("no", nays)
        vote.add_source(vote_url)
        vote.pupa_id = vote_url

        # first table has YEAs
        for name in doc.xpath("//table[1]/tr/td/font/text()"):
            vote.yes(name.strip())

        # second table is nays
        for name in doc.xpath("//table[2]/tr/td/font/text()"):
            vote.no(name.strip())

        yield vote
