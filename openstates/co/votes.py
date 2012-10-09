from billy.scrape.votes import VoteScraper, Vote
import subprocess
import lxml
import os
import re

journals = "http://www.leg.state.co.us/CLICS/CLICS%s/csljournals.nsf/jouNav?Openform&%s"

# session - 2012A
# chamber - last argument, House / Senate


class COVoteScraper(VoteScraper):
    state = 'co'

    def lxmlize(self, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape_senate(self, session):
        url = journals % (session, 'Senate')
        page = self.lxmlize(url)
        hrefs = page.xpath("//font//a")
        for href in hrefs:
            (path, response) = self.urlretrieve(href.attrib['href'])
            try:
                subprocess.check_call([
                    "pdftotext", "-layout", path
                ])
            except subprocess.CalledProcessError:
                # XXX: log this error
                continue

            txt = "%s.txt" % (path)
            vote_re = (r"\s*"
                       "YES\s*(?P<yes_count>\d+)\s*"
                       "NO\s*(?P<no_count>\d+)\s*"
                       "EXCUSED\s*(?P<excused_count>\d+)\s*"
                       "ABSENT\s*(?P<abs_count>\d+).*")

            cur_bill_id = None
            cur_vote_count = None

            for line in open(txt).readlines():
                summ = re.findall(vote_re, line)
                if summ != []:
                    cur_vote_count = summ[0]

                if line.strip() == "":
                    continue
                first = line[0]
                if first != " ":
                    if " " not in line:
                        # wtf
                        continue

                    bill_id, kruft = line.split(" ", 1)
                    if len(bill_id) < 3:
                        continue
                    if bill_id[0] != "H" and bill_id[0] != "S":
                        continue
                    if bill_id[2] not in ['B', 'J', 'R', 'M']:
                        continue

                    cur_bill_id = bill_id

            os.unlink(path)
            os.unlink(txt)

    def scrape_house(self, session):
        pass

    def scrape(self, chamber, session):
        if chamber == 'upper':
            self.scrape_senate(session)
        if chamber == 'lower':
            self.scrape_house(session)
