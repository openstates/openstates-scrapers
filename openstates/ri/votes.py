import re
import datetime as dt

import lxml
from pupa.scrape import Scraper, VoteEvent

from openstates.utils import url_xpath

RI_URL_BASE = "http://webserver.rilin.state.ri.us"


class RIVoteScraper(Scraper):
    def get_dates(self, page):
        dates = url_xpath(page, "//select[@name='votedate']")[0].xpath("./*")
        return [a.text for a in dates]

    def get_votes(self, url, session):
        ret = {}
        html = self.get(url).text
        p = lxml.html.fromstring(html)
        tables = \
            p.xpath("//td[@background='/images/capBG.jpg']/div/table")

        metainf = tables[0]
        table = tables[1]

        inf = metainf.xpath("./tr/td/pre")[0]
        headers = [br.tail for br in inf.xpath("./*")]

        dateinf = metainf.xpath("./tr/td")[3]
        date = dateinf.text
        time = dateinf.xpath("./*")[0].tail

        vote_digest = metainf.xpath("./tr/td[@colspan='3']")
        digest = vote_digest[2].text_content()
        dig = []
        for d in digest.split("\n"):
            lis = d.strip().split("-")
            for l in lis:
                if l is not None and l != "":
                    dig.append(l.strip())
        digest = dig

        il = iter(digest)
        d = dict(zip(il, il))
        vote_count = d
        vote_count['passage'] = int(vote_count['YEAS']) > int(vote_count['NAYS'])
        # XXX: This here has a greater then normal chance of failing.
        # However, it's an upstream issue.

        time_string = "%s %s" % (time, date)

        fmt_string = "%I:%M:%S %p %A, %B %d, %Y"
        # 4:31:14 PM TUESDAY, JANUARY 17, 2012
        date_time = dt.datetime.strptime(time_string, fmt_string)

        bill_s_n_no = r"(?P<year>[0-9]{2,4})(-?)(?P<chamber>[SH])\s*(?P<bill>[0-9]+)"
        # This is technically wrong, but it's close enough to be fine.
        # something like "123S  3023" is technically valid, even though it's
        # silly

        bill_metainf = None
        remaining = None

        for hid in range(0, len(headers)):
            h = headers[hid]
            inf = re.search(bill_s_n_no, h)
            if inf is not None:
                bill_metainf = inf.groupdict()
                if bill_metainf['year'][-2:] != session[-2:]:
                    self.info(
                        "Skipping vote - it's in the %s session, we're in the %s session." % (
                            bill_metainf['year'][-2:],
                            session[-2:]
                        )
                    )
                    return ret
                remaining = headers[hid + 1:]

        if bill_metainf is None:
            self.warning("No metainf for this bill. Aborting snag")
            return ret

        try:
            motion = remaining[-2]
        except IndexError:
            self.warning("Mission motion on this vote")
            motion = "Unknown"  # XXX: Because the motion is not on some page

        bill_metainf['extra'] = {"motion": motion}

        votes = []

        for t in table.xpath("./tr/td"):
            nodes = t.xpath("./*")
            for node in nodes:
                if node.tag == "span":
                    vote = node.text.strip().upper()
                    name = node.tail.strip()
                    votes.append({
                        "name": name,
                        "vote": vote
                    })
            if len(votes) > 0:
                bid = bill_metainf['bill']
                ret[bid] = {
                    "votes": votes,
                    "meta": bill_metainf,
                    "time": date_time,
                    "count": vote_count,
                    "source": url
                }
        return ret

    def parse_vote_page(self, page, context_url, session):
        ret = []
        p = lxml.html.fromstring(page)
        votes = p.xpath("//center/div[@class='vote']")
        for vote in votes:
            votes = self.get_votes(
                context_url + "/" + vote.xpath("./a")[0].attrib["href"], session)
            ret.append(votes)
        return ret

    def post_to(self, url, vote):
        headers = {"votedate": vote}
        return self.post(url, data=headers).text

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber is not None else ['upper', 'lower']

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        url = {
            "upper": "%s/%s" % (RI_URL_BASE, "SVotes"),
            "lower": "%s/%s" % (RI_URL_BASE, "HVotes")
        }[chamber]
        action = "%s/%s" % (url, "votes.asp")
        dates = self.get_dates(url)
        for date in dates:
            votes = self.parse_vote_page(self.post_to(action, date), url, session)
            for vote_dict in votes:
                for vote in vote_dict:
                    vote = vote_dict[vote]
                    count = vote['count']
                    chamber = {
                        "H": "lower",
                        "S": "upper"
                    }[vote['meta']['chamber']]
                    v = VoteEvent(
                        chamber=chamber,
                        start_date=vote['time'].strftime('%Y-%m-%d'),
                        motion_text=vote['meta']['extra']['motion'],
                        result='pass' if count['passage'] else 'fail',
                        classification='passage',
                        legislative_session=session,
                        bill=vote['meta']['bill'],
                    )
                    v.set_count('yes', int(count['YEAS']))
                    v.set_count('no', int(count['NAYS']))
                    v.set_count('other', int(count['NOT VOTING']))
                    v.add_source(vote['source'])
                    for vt in vote['votes']:
                        key = {
                            'Y': 'yes',
                            'N': 'no',
                        }.get(vt['vote'], 'other')
                        v.vote(key, vt['name'])
                    yield v
