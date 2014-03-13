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
            raise ValueError('Response was invalid. Timsucks.')
        return valid

    def scrape_bill(self, chamber, session, bill_id, title, sponsor, url):
        html = self.urlopen(url)
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

        # now try and get second h1
        bill_type_h2 = page.xpath('//h2/text()')[-1]
        if re.findall('[SH]B', bill_type_h2):
            bill_type = 'bill'
        elif re.findall('[SH]PB', bill_type_h2):
            bill_type = 'proposed bill'
        elif re.findall('[SH]R', bill_type_h2):
            bill_type = 'resolution'
        elif re.findall('[SH]JR', bill_type_h2):
            bill_type = 'joint resolution'
        elif re.findall('[SH]CR', bill_type_h2):
            bill_type = 'concurrent resolution'
        elif re.findall('[SH]M', bill_type_h2):
            bill_type = 'memorial'
        elif re.findall('\s+Senate \d+', bill_type_h2):
            bill_type = 'bill'
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
                version = tr.xpath("string(td[1])").strip().split()
                version_chamber = version[0]

                vote_chamber = chamber
                vote_date = datetime.datetime.strptime(
                    vote_date, "%m/%d/%Y %H:%M %p").date()

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

        y, n, o = 0, 0, 0
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
                    name = match.group(2)
                    if match.group(1) == 'Y':
                        vote.yes(name)
                    elif match.group(1) == 'N':
                        vote.no(name)
                    else:
                        vote.other(name)
                else:
                    if "PAIR" in line:
                        break_outter = True
                        break
                    vote.other(col.strip())

        # vote.validate()
        if not vote['motion']:
            vote['motion'] = '[No motion given.]'

        bill.add_vote(vote)
