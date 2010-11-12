import os
import re
import tempfile
import datetime

from fiftystates.scrape import ScrapeError
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote
from fiftystates.scrape.utils import pdf_to_lxml
from fiftystates.scrape.la import metadata, internal_sessions

import lxml.html


class LABillScraper(BillScraper):
    state = 'la'

    def scrape(self, chamber, session):
        types = {'upper': ['SB', 'SCR'], 'lower': ['HB', 'HCR']}
        for session in internal_sessions[int(session)]:
            s_id = re.findall('\/(\w+)\.htm', session[0])[0]

            # Fake it until we can make it
            for abbr in types[chamber]:
                bill_number = 1
                failures = 0
                while failures < 5:
                    bill_url = ('http://www.legis.state.la.us/billdata/'
                                'byinst.asp?sessionid=%s&billtype=%s'
                                '&billno=%d' % (
                                    s_id, abbr, bill_number))

                    if self.scrape_bill(bill_url, chamber, session[1]):
                        failures = 0
                    else:
                        failures += 1

                    bill_number += 1

    def scrape_bill(self, bill_url, chamber, session):
        with self.urlopen(bill_url) as text:
            if "Specified Bill could not be found" in text:
                return False
            page = lxml.html.fromstring(text)
            page.make_links_absolute(bill_url)

            bill_id = page.xpath("string(//h2)").split()[0]

            summary = page.xpath(
                "string(//*[starts-with(text(), 'Summary: ')])")
            summary = summary.replace('Summary: ', '')

            match = re.match(r"^([^:]+): "
                             r"((\(Constitutional Amendment\) )?[^(]+)",
                             summary)

            if match:
                subjects = [match.group(1).strip()]
                title = match.group(2).strip()
            else:
                raise ScrapeError("Bad title")

            if bill_id.startswith('SB') or bill_id.startswith('HB'):
                bill_type = ['bill']
            elif bill_id.startswith('SCR') or bill_id.startswith('HCR'):
                bill_type = ['concurrent resolution']
            else:
                raise ScrapeError("Invalid bill ID format: %s" % bill_id)

            if title.startswith("(Constitutional Amendment)"):
                bill_type.append('constitutional amendment')
                title = title.replace('(Constitutional Amendment) ', '')

            bill = Bill(session, chamber, bill_id, title,
                        subjects=subjects, type=bill_type)
            bill.add_source(bill_url)

            history_link = page.xpath("//a[text() = 'History']")[0]
            history_url = history_link.attrib['href']
            self.scrape_history(bill, history_url)

            authors_link = page.xpath("//a[text() = 'Authors']")[0]
            authors_url = authors_link.attrib['href']
            self.scrape_authors(bill, authors_url)

            try:
                versions_link = page.xpath(
                    "//a[text() = 'Text - All Versions']")[0]
                versions_url = versions_link.attrib['href']
                self.scrape_versions(bill, versions_url)
            except IndexError:
                # Only current version
                try:
                    version_link = page.xpath(
                        "//a[text() = 'Text - Current']")[0]
                    version_url = version_link.attrib['href']
                    bill.add_version("%s Current" % bill_id, version_url)
                except IndexError:
                    # Some bills don't have any versions :(
                    pass

            try:
                votes_link = page.xpath("//a[text() = 'Votes']")[0]
                self.scrape_votes(bill, votes_link.attrib['href'])
            except IndexError:
                # Some bills don't have any votes
                pass

            self.save_bill(bill)

            return True

    def scrape_history(self, bill, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)
            bill.add_source(url)

            action_table = page.xpath("//td/b[text() = 'Action']/../../..")[0]

            for row in reversed(action_table.xpath('tr')[1:]):
                cells = row.xpath('td')
                date = cells[0].text.strip()
                date = datetime.datetime.strptime(date, '%m/%d/%Y').date()

                chamber = cells[1].text.strip()
                if chamber == 'S':
                    chamber = 'upper'
                elif chamber == 'H':
                    chamber = 'lower'

                action = cells[3].text.strip()

                atype = []

                if action.startswith('Prefiled'):
                    atype.append('bill:introduced')

                if 'referred to the committee' in action.lower():
                    atype.append('committee:referred')

                if action.startswith('Signed by the Governor.'):
                    atype.append('governor:signed')

                if 'Amendments proposed' in action:
                    atype.append('amendment:introduced')

                if 'finally passed' in action:
                    atype.append('bill:passed')

                match = re.match(r'House conferees appointed: (.*)', action)
                if match:
                    names = match.group(1).split(', ')
                    names[-1] = names[-1].strip('.').replace('and ', '')
                    conf = bill.get('conference_committee', {})
                    conf['lower'] = names
                    bill['conference_committee'] = conf

                match = re.match(
                    r'Senate conference committee appointed: (.*)',
                    action)
                if match:
                    names = match.group(1).split(', ')
                    names[-1] = names[-1].strip('.').replace('and ', '')
                    conf = bill.get('conference_committee', {})
                    conf['upper'] = names
                    bill['conference_committee'] = conf

                bill.add_action(chamber, action, date, type=atype)

    def scrape_authors(self, bill, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)
            bill.add_source(url)

            author_table = page.xpath(
                "//td[contains(text(), 'Author)')]/../..")[0]

            for row in author_table.xpath('tr')[1:]:
                author = row.xpath('string()').strip()

                if "(Primary Author)" in author:
                    type = 'primary author'
                    author = author.replace(" (Primary Author)", '')
                else:
                    type = 'author'

                bill.add_sponsor(type, author)

    def scrape_versions(self, bill, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)
            page.make_links_absolute(url)
            bill.add_source(url)

            for a in reversed(page.xpath(
                    "//a[contains(@href, 'streamdocument.asp')]")):
                version_url = a.attrib['href']
                version = a.text.strip()

                bill.add_version(version, version_url)

    def scrape_votes(self, bill, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)
            page.make_links_absolute(url)

            for a in page.xpath("//a[contains(@href, 'streamdocument.asp')]"):
                self.scrape_vote(bill, a.text, a.attrib['href'])

    def scrape_vote(self, bill, name, url):
        match = re.match('^(Senate|House) Vote on [^,]*,(.*)$', name)

        if not match:
            return

        chamber = {'Senate': 'upper', 'House': 'lower'}[match.group(1)]
        motion = match.group(2).strip()

        if motion.startswith('FINAL PASSAGE'):
            type = 'passage'
        elif motion.startswith('AMENDMENT'):
            type = 'amendment'
        elif 'ON 3RD READINT' in motion:
            type = 'reading:3'
        else:
            type = 'other'

        vote = Vote(chamber, None, motion, None,
                    None, None, None)
        vote['type'] = type
        vote.add_source(url)

        with self.urlopen(url) as text:
            (fd, temp_path) = tempfile.mkstemp()
            with os.fdopen(fd, 'wb') as w:
                w.write(text)
            html = pdf_to_lxml(temp_path)
            os.remove(temp_path)

            vote_type = None
            total_re = re.compile('^Total--(\d+)$')
            body = html.xpath('string(/html/body)')
            for line in body.replace(u'\xa0', '\n').split('\n'):
                line = line.replace('&nbsp;', '').strip()
                if not line:
                    continue

                if line in ('YEAS', 'NAYS', 'ABSENT'):
                    vote_type = {'YEAS': 'yes', 'NAYS': 'no',
                                 'ABSENT': 'other'}[line]
                elif vote_type:
                    match = total_re.match(line)
                    if match:
                        vote['%s_count' % vote_type] = int(match.group(1))
                    elif vote_type == 'yes':
                        vote.yes(line)
                    elif vote_type == 'no':
                        vote.no(line)
                    elif vote_type == 'other':
                        vote.other(line)

        # The PDFs oddly don't say whether a vote passed or failed.
        # Hopefully passage just requires yes_votes > not_yes_votes
        if vote['yes_count'] > (vote['no_count'] + vote['other_count']):
            vote['passed'] = True
        else:
            vote['passed'] = False

        bill.add_vote(vote)
