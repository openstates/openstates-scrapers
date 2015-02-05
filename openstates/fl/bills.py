import os
import re
import datetime

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import convert_pdf

import lxml.html


class FLBillScraper(BillScraper):
    jurisdiction = 'fl'

    def scrape(self, chamber, session):
        self.validate_session(session)

        cname = {'upper': 'Senate', 'lower': 'House'}[chamber]
        url = "http://flsenate.gov/Session/Bills/%s?chamber=%s"
        url = url % (session, cname)
        while True:
            html = self.urlopen(url)
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
                url = link.attrib['href'] + '/ByCategory'
                self.scrape_bill(chamber, session, bill_id, title,
                                 sponsor, url)

            try:
                next_link = page.xpath("//a[contains(., 'Next')]")[0]
                url = next_link.attrib['href']
            except (KeyError, IndexError):
                self.logger.info('Hit last page of search results.')
                break

    def accept_response(self, response):
        normal = super(FLBillScraper, self).accept_response(response)
        bill_check = True
        text_check = True

        if not response.url.lower().endswith('pdf'):
            if response.url.startswith("http://flsenate.gov/Session/Bill/20"):
                bill_check = "tabBodyVoteHistory" in response.text

            text_check = \
                    'he page you have requested has encountered an error.' \
                    not in response.text

        valid = (normal and
                bill_check and
                text_check)
        if not valid:
            raise Exception('Response was invalid. Timsucks.')
        return valid

    def scrape_bill(self, chamber, session, bill_id, title, sponsor, url):
        try:
            html = self.urlopen(url)
        except:
            return
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        bill = Bill(session, chamber, bill_id, title)
        bill.add_source(url)

        bill.add_sponsor('primary', sponsor)

        next_href = url + '/?Tab=BillHistory'
        html = self.urlopen(next_href)
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

        if bill_id.startswith('SB ') or \
                bill_id.startswith('HB ') or \
                bill_id.startswith('SPB ') or \
                bill_id.startswith('HPB '):
            bill_type = 'bill'
        elif bill_id.startswith('HR ') or bill_id.startswith('SR '):
            bill_type = 'resolution'
        elif bill_id.startswith('HJR ') or bill_id.startswith('SJR '):
            bill_type = 'joint resolution'
        elif bill_id.startswith('SCR ') or bill_id.startswith('HCR '):
            bill_type = 'concurrent resolution'
        elif bill_id.startswith('SM ') or bill_id.startswith('HM '):
            bill_type = 'memorial'
        else:
            raise Exception('Failed to identify bill type.')

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
                elif action.startswith('CS passed'):
                    atype.append('bill:passed')

                bill.add_action(actor, action, date, type=atype)

        try:
            version_table = page.xpath(
                "//div[@id = 'tabBodyBillText']/table")[0]
            for tr in version_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                version_url = tr.xpath("td/a[1]")[0].attrib['href']
                if version_url.endswith('PDF'):
                    mimetype = 'application/pdf'
                elif version_url.endswith('HTML'):
                    mimetype = 'text/html'
                bill.add_version(name, version_url, mimetype=mimetype)
        except IndexError:
            self.log("No version table for %s" % bill_id)

        try:
            analysis_table = page.xpath(
                "//div[@id = 'tabBodyAnalyses']/table")[0]
            for tr in analysis_table.xpath("tbody/tr"):
                name = tr.xpath("string(td[1])").strip()
                name += " -- " + tr.xpath("string(td[3])").strip()
                name = re.sub(r'\s+', " ", name)
                date = tr.xpath("string(td[4])").strip()
                if date:
                    name += " (%s)" % date
                analysis_url = tr.xpath("td/a")[0].attrib['href']
                bill.add_document(name, analysis_url)
        except IndexError:
            self.log("No analysis table for %s" % bill_id)

        next_href = url + '/?Tab=VoteHistory'
        html = self.urlopen(next_href)
        vote_page = lxml.html.fromstring(html)
        vote_page.make_links_absolute(url)

        vote_tables = vote_page.xpath(
            "//div[@id = 'tabBodyVoteHistory']//table")

        for vote_table in vote_tables:
            for tr in vote_table.xpath("tbody/tr"):
                vote_date = tr.xpath("string(td[3])").strip()
                if vote_date.isalpha():
                    vote_date = tr.xpath("string(td[2])").strip()
                version = tr.xpath("string(td[1])").strip().split()
                version_chamber = version[0]

                vote_chamber = chamber
                try:
                    vote_date = datetime.datetime.strptime(
                        vote_date, "%m/%d/%Y %H:%M %p").date()
                except ValueError:
                    msg = 'Got bogus vote date: %r'
                    self.logger.warning(msg % vote_date)

                vote_url = tr.xpath("td[4]/a")[0].attrib['href']
                self.scrape_vote(bill, vote_chamber, vote_date,
                                 vote_url)
        else:
            self.log("No vote table for %s" % bill_id)

        self.save_bill(bill)

    def scrape_vote(self, bill, chamber, date, url):
        (path, resp) = self.urlretrieve(url)
        text = convert_pdf(path, 'text')
        lines = text.split("\n")
        os.remove(path)

        (_, motion) = lines[5].split("FINAL ACTION:")
        motion = motion.strip()
        if not motion:
            self.warning("Vote appears to be empty")
            return

        vote_top_row = [
                lines.index(x) for x in lines if 
                re.search(r'^\s+Yea\s+Nay.*?(?:\s+Yea\s+Nay)+$', x)
                ][0]
        yea_columns_end = lines[vote_top_row].index("Yea") + len("Yea")
        nay_columns_begin = lines[vote_top_row].index("Nay")

        votes = {'yes': [], 'no': [], 'other': []}
        for line in lines[(vote_top_row + 1): ]:
            if line.strip():
                member = re.search(r'''(?x)
                        ^\s+(?:[A-Z\-]+)?\s+  # Possible vote indicator
                        ([A-Z][a-z]+  # Name must have lower-case characters
                        [\w\-\s]+)  # Continue looking for the rest of the name
                        (?:,[A-Z\s]+?)?  # Leadership has an all-caps title
                        (?:\s{2,}.*)?  # Name ends when many spaces are seen
                        ''', line).group(1)
                # Usually non-voting members won't even have a code listed
                did_vote = bool(re.search(r'^\s+([A-Z\-]+)\s+[A-Z][a-z]', line))
                if did_vote:
                    # Check where the "X" or vote code is on the page
                    vote_column = len(line) - len(line.lstrip())
                    if vote_column <= yea_columns_end:
                        votes['yes'].append(member)
                    elif vote_column >= nay_columns_begin:
                        votes['no'].append(member)
                    else:
                        raise AssertionError(
                                "Unparseable vote found for {0} in {1}:\n{2}".
                                format(member, url, line)
                                )
                else:
                    votes['other'].append(member)

            # End loop as soon as no more members are found
            else:
                break

        totals = re.search(r'(?ms)\s+(\d+)\s+(\d+)\s+.*?TOTALS', text).groups()
        yes_count = int(totals[0])
        no_count = int(totals[1])
        if yes_count != len(votes['yes']) or no_count != len(votes['no']):
            raise AssertionError(
                    "Should have {0} yes votes: {1}\n".
                    format(yes_count, votes['yes']) +
                    "and {0} no votes: {1}".
                    format(no_count, votes['no'])
                    )
        passed = (yes_count > no_count)
        other_count = len(votes['other'])

        vote = Vote(chamber, date, motion, passed, yes_count, no_count,
                    other_count)
        vote.add_source(url)
        vote['yes_votes'] = votes['yes']
        vote['no_votes'] = votes['no']
        vote['other_votes'] = votes['other']

        bill.add_vote(vote)
