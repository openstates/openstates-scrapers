import os
import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

import lxml.html


class FLBillScraper(BillScraper):
    state = 'fl'

    def scrape(self, chamber, session):
        self.validate_session(session)

        cname = {'upper': 'Senate', 'lower': 'House'}[chamber]
        url = ("http://flsenate.gov/Session/Bills.cfm?"
               "SessionName=%s&PageNumber=1&Chamber=%s&LastAction="
               "&Senator=&SearchQuery=" % (session, cname))
        while True:
            with self.urlopen(url) as page:
                page = lxml.html.fromstring(page)
                page.make_links_absolute(url)

                link_path = ("//a[contains(@href, '/Session/Bill/%s')"
                             "and starts-with(., '%s')]" % (
                                 session, cname[0]))
                for link in page.xpath(link_path):
                    bill_id = link.text.strip()
                    title = link.xpath(
                        "string(../following-sibling::td[1])").strip()
                    sponsor = link.xpath(
                        "string(../following-sibling::td[2])").strip()
                    self.scrape_bill(chamber, session, bill_id, title,
                                     sponsor, link.attrib['href'])

                try:
                    next_link = page.xpath("//a[. = 'Next']")[0]
                    url = next_link.attrib['href']
                except (KeyError, IndexError):
                    break

    def scrape_bill(self, chamber, session, bill_id, title, sponsor, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            bill.add_sponsor('introducer', sponsor)

            try:
                hist_table = page.xpath(
                    "//div[@id = 'tabBodyBillHistory']/table")[0]
                for tr in hist_table.xpath("tbody/tr"):
                    date = tr.xpath("string(td[1])")
                    date = datetime.datetime.strptime(
                        date, "%m/%d/%Y").date()

                    actor = tr.xpath("string(td[2])")
                    actor = {'Senate': 'upper', 'House': 'lower'}.get(
                        actor, actor)

                    if not actor:
                        continue

                    act_text = tr.xpath("string(td[3])").strip()
                    for action in act_text.split(u'\u2022'):
                        action = action.strip()
                        if not action:
                            continue

                        action = re.sub(r'-(H|S)J\s+(\d+)$', '',
                                        action)

                        atype = []
                        if action.startswith('Referred to'):
                            atype.append('committee:referred')
                        elif action.startswith('Favorable by'):
                            atype.append('committee:passed')
                        elif action == "Filed":
                            atype.append("bill:filed")
                        elif action.startswith("Withdrawn"):
                            atype.append("bill:failed")
                        elif action.startswith('Introduced'):
                            atype.append('bill:introduced')

                        bill.add_action(actor, action, date, type=atype)
            except IndexError:
                self.log("No bill history for %s" % bill_id)

            try:
                version_table = page.xpath(
                    "//div[@id = 'tabBodyBillText']/table")[0]
                for tr in version_table.xpath("tbody/tr"):
                    name = tr.xpath("string(td[1])").strip()
                    url = tr.xpath("td/a[1]")[0].attrib['href']
                    bill.add_version(name, url)
            except IndexError:
                self.log("No version table for %s" % bill_id)

            try:
                analysis_table = page.xpath(
                    "//div[@id = 'tabBodyAnalyses']/table")[0]
                for tr in analysis_table.xpath("tbody/tr"):
                    name = tr.xpath("string(td[1])").strip()
                    name += " -- " + tr.xpath("string(td[3])").strip()
                    date = tr.xpath("string(td[4])").strip()
                    if date:
                        name += " (%s)" % date
                    url = tr.xpath("td/a")[0].attrib['href']
                    bill.add_document(name, url)
            except IndexError:
                self.log("No analysis table for %s" % bill_id)

            try:
                vote_table = page.xpath(
                    "//div[@id = 'tabBodyVoteHistory']/table")[1]
                for tr in vote_table.xpath("tbody/tr"):
                    vote_chamber = tr.xpath("string(td[2])").strip()
                    vote_chamber = {'Senate': 'upper',
                                    'House': 'lower'}[vote_chamber]
                    rc_num = tr.xpath("string(td[3])")

                    vote_date = tr.xpath("string(td[4])")
                    vote_date = datetime.datetime.strptime(
                        vote_date, "%m/%d/%Y").date()

                    vote_url = tr.xpath("td[5]/a")[0].attrib['href']
                    self.scrape_vote(bill, vote_chamber, vote_date,
                                     vote_url)
            except IndexError:
                self.log("No vote table for %s" % bill_id)

            self.save_bill(bill)

    def scrape_vote(self, bill, chamber, date, url):
        (path, resp) = self.urlretrieve(url)
        text = convert_pdf(path, 'text')

        motion = text.split('\n')[4].strip()

        yes_count = int(re.search(r'Yeas - (\d+)', text).group(1))
        no_count = int(re.search(r'Nays - (\d+)', text).group(1))
        other_count = int(re.search(r'Not Voting - (\d+)', text).group(1))
        passed = yes_count > (no_count + other_count)

        vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                    other_count)
        vote.add_source(url)

        for match in re.finditer(r'(Y|EX|N)\s+([^-]+)-\d+', text):
            vtype = match.group(1)
            name = match.group(2)

            if vtype == 'Y':
                vote.yes(name)
            elif vtype == 'N':
                vote.no(name)
            else:
                vote.other(name)

        bill.add_vote(vote)
