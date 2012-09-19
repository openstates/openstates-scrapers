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
            with self.urlopen(url) as html:
                page = lxml.html.fromstring(html)
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

    def accept_response(self, response):
        normal = super(FLBillScraper, self).accept_response(response)
        bill_check = True
        text_check = True

        if not response.url.lower().endswith('pdf'):
            if response.url.startswith("http://flsenate.gov/Session/Bill/20"):
                bill_check = "tabBodyVoteHistory" in response.text

            text_check = \
                    'The page you have requested has encountered an error.' \
                    not in response.text

        return (normal and
                bill_check and
                text_check)


    def scrape_bill(self, chamber, session, bill_id, title, sponsor, url):
        with self.urlopen(url) as html:
            page = lxml.html.fromstring(html)
            page.make_links_absolute(url)

            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(url)

            bill.add_sponsor('primary', sponsor)

            next_href = page.xpath("//a[@id='optionBillHistory']")[0]
            next_href = next_href.attrib['href']
            with self.urlopen(next_href) as html:
                hist_page = lxml.html.fromstring(html)
                hist_page.make_links_absolute(url)

            try:
                hist_table = hist_page.xpath(
                    "//div[@id = 'tabBodyBillHistory']//table")[0]
            except IndexError:
                self.warning('no tabBodyBillHistory in %s, attempting to '
                             'refetch once' % url)
                html = self.urlopen(url)
                hist_page = lxml.html.fromstring(next_href)
                hist_page.make_links_absolute(next_href)

                hist_table = hist_page.xpath(
                    "//div[@id = 'tabBodyBillHistory']//table")[0]

            # now try and get second h1
            bill_type_h1 = page.xpath('//h1/text()')[1]
            if re.findall('[SH]B', bill_type_h1):
                bill_type = 'bill'
            if re.findall('[SH]PB', bill_type_h1):
                bill_type = 'proposed bill'
            elif re.findall('[SH]R', bill_type_h1):
                bill_type = 'resolution'
            elif re.findall('[SH]JR', bill_type_h1):
                bill_type = 'joint resolution'
            elif re.findall('[SH]CR', bill_type_h1):
                bill_type = 'concurrent resolution'
            elif re.findall('[SH]M', bill_type_h1):
                bill_type = 'memorial'

            bill['type'] = [bill_type]

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
                        atype.append("bill:withdrawn")
                    elif action.startswith("Died"):
                        atype.append("bill:failed")
                    elif action.startswith('Introduced'):
                        atype.append('bill:introduced')
                    elif action.startswith('Read 2nd time'):
                        atype.append('bill:reading:2')
                    elif action.startswith('Read 3rd time'):
                        atype.append('bill:reading:3')
                    elif action.startswith('Adopted'):
                        atype.append('bill:passed')

                    bill.add_action(actor, action, date, type=atype)

            try:
                version_table = page.xpath(
                    "//div[@id = 'tabBodyBillText']/table")[0]
                for tr in version_table.xpath("tbody/tr"):
                    name = tr.xpath("string(td[1])").strip()
                    url = tr.xpath("td/a[1]")[0].attrib['href']
                    if url.endswith('PDF'):
                        mimetype = 'application/pdf'
                    elif url.endswith('HTML'):
                        mimetype = 'text/html'
                    bill.add_version(name, url, mimetype=mimetype)
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

            next_href = page.xpath("//a[@id='optionVoteHistory']")[0]

            next_href = next_href.attrib['href']
            with self.urlopen(next_href) as html:
                vote_page = lxml.html.fromstring(html)
                vote_page.make_links_absolute(url)

            vote_tables = vote_page.xpath(
                "//div[@id = 'tabBodyVoteHistory']//table")

            for vote_table in vote_tables:
                for tr in vote_table.xpath("tbody/tr"):
                    vote_chamber = tr.xpath("string(td[3])").strip()
                    vote_date = tr.xpath("string(td[2])").strip()
                    version = tr.xpath("string(td[1])").strip().split()
                    version_chamber = version[0]

                    # sometimes these are flipped
                    if ' at ' in vote_chamber:
                        vote_date, vote_chamber = vote_chamber, vote_date
                    try:
                        vote_chamber = {'Senate': 'upper',
                                        'House': 'lower'}[vote_chamber]
                    except KeyError:
                        vote_chamber = {'S': 'upper',
                                        'H': 'lower',
                                        'J': 'joint'}[version_chamber]

                    vote_date = datetime.datetime.strptime(
                        vote_date, "%m/%d/%Y at %H:%M %p").date()

                    vote_url = tr.xpath("td[4]/a")[0].attrib['href']
                    self.scrape_vote(bill, vote_chamber, vote_date,
                                     vote_url)
            else:
                self.log("No vote table for %s" % bill_id)

            self.save_bill(bill)

    def scrape_vote(self, bill, chamber, date, url):
        (path, resp) = self.urlretrieve(url)
        text = convert_pdf(path, 'text')
        os.remove(path)

        try:
            motion = text.split('\n')[4].strip()
        except IndexError:
            return

        try:
            yes_count = int(re.search(r'Yeas - (\d+)', text).group(1))
        except AttributeError:
            return

        no_count = int(re.search(r'Nays - (\d+)', text).group(1))
        other_count = int(re.search(r'Not Voting - (\d+)', text).group(1))
        passed = yes_count > (no_count + other_count)

        vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                    other_count)
        vote.add_source(url)

        y,n,o = 0,0,0
        break_outter = False

        for line in text.split('\n')[9:]:
            if break_outter:
                break

            if 'after roll call' in line:
                break
            if 'Indication of Vote' in line:
                break
            if 'Presiding' in line:
                continue

            for col in re.split(r'-\d+', line):
                col = col.strip()
                if not col:
                    continue

                match = re.match(r'(Y|N|EX|\*)\s+(.+)$', col)

                if match:
                    if match.group(2) == "PAIR":
                        break_outter = True
                        break
                    if match.group(1) == 'Y':
                        vote.yes(match.group(2))
                    elif match.group(1) == 'N':
                        vote.no(match.group(2))
                    else:
                        vote.other(match.group(2))
                else:
                    vote.other(col.strip())

        vote.validate()
        bill.add_vote(vote)
