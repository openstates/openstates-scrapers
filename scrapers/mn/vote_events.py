import re
import datetime
import scrapelib
import lxml.html

from openstates.scrape import Scraper, VoteEvent

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
    "2019-2020": "https://www.house.leg.state.mn.us/votes/getVotesls91.asp",
    "2020s1": "https://www.house.leg.state.mn.us/votes/getVotesls9120201.asp",
    "2020s2": "https://www.house.leg.state.mn.us/votes/getVotesls9120202.asp",
    "2020s3": "https://www.house.leg.state.mn.us/votes/getVotesls9120203.asp",
    "2020s4": "https://www.house.leg.state.mn.us/votes/getVotesls9120204.asp",
    "2020s5": "https://www.house.leg.state.mn.us/votes/getVotesls9120205.asp",
    "2020s6": "https://www.house.leg.state.mn.us/votes/getVotesls9120206.asp",
    "2020s7": "https://www.house.leg.state.mn.us/votes/getVotesls9120207.asp",
    "2021-2022": "https://www.house.leg.state.mn.us/votes/getVotesls92.asp",
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
        try:
            resp = self.get(vote_url)
            html = resp.text
        except scrapelib.HTTPError:
            return

        doc = lxml.html.fromstring(html)
        motion = doc.xpath("//p[1]//b[1]/text()")[-1].strip()
        if len(motion) == 0:
            print(motion)
            motion = doc.xpath("//h2[1]/text()")[0].strip()

        vote_count = (
            doc.xpath("//h3[contains(text(),'YEA and ')]/text()")[0].strip().split()
        )
        yeas = int(vote_count[0])
        nays = int(vote_count[3])

        date = doc.xpath("//b[contains(text(),'Date:')]/../text()")[1].strip()
        date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

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
        vote.dedupe_key = vote_url

        # first table has YEAs
        for name in doc.xpath("//table[1]//font/text()"):
            vote.yes(name.strip())

        # second table is nays
        for name in doc.xpath("//table[2]//font/text()"):
            vote.no(name.strip())

        yield vote
