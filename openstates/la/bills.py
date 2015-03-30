from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from billy.scrape.utils import pdf_to_lxml
from openstates.utils import LXMLMixin

import datetime as dt
import lxml.html
import scrapelib
import tempfile
import os
import re


URL = "http://www.legis.la.gov/Legis/BillSearchListQ.aspx?r=%s1*"

bill_types = {
    "upper": ["SB", "SCR"],
    "lower": ["HB", "HCR"]
}


class LABillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'la'

    def do_post_back(self, page, event_target, event_argument):
        form = page.xpath("//form[@id='aspnetForm']")[0]
        block = {name: value for name, value in [(obj.name, obj.value)
                    for obj in form.xpath(".//input")]}
        block['__EVENTTARGET'] = event_target
        block['__EVENTARGUMENT'] = event_argument
        if form.method == "GET":
            ret = lxml.html.fromstring(self.get(form.action, data=block).text)
        elif form.method == "POST":
            ret = lxml.html.fromstring(self.post(form.action, data=block).text)
        else:
            raise AssertionError("Unrecognized request type found: {}".format(
                                 form.method))

        ret.make_links_absolute(form.action)
        return ret

    def bill_pages(self, bill_type):
        page = self.lxmlize(URL % (bill_type))
        yield page

        while True:
            hrefs = page.xpath("//a[text()=' > ']")
            if hrefs == [] or "disabled" in hrefs[0].attrib:
                return

            href = hrefs[0].attrib['href']
            tokens = re.match(".*\(\'(?P<token>.*)\',\'.*", href).groupdict()

            page = self.do_post_back(
                page,
                tokens['token'],
                ""
            )
            if page:
                yield page

    def scrape_bare_page(self, url):
        page = self.lxmlize(url)
        return page.xpath("//a")

    def scrape(self, chamber, session):
        for bill_type in bill_types[chamber]:
            for bill_page in self.bill_pages(bill_type):
                for bill in bill_page.xpath(
                        "//a[contains(@href, 'BillInfo.aspx')]"):
                    self.scrape_bill_page(chamber,
                                          session,
                                          bill.attrib['href'],
                                          bill_type)


    def get_one_xpath(self, page, xpath):
        ret = page.xpath(xpath)
        if len(ret) != 1:
            raise Exception
        return ret[0]

    def scrape_votes(self, bill, url):
        text = self.get(url).text
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)

        for a in page.xpath("//a[contains(@href, 'ViewDocument.aspx')]"):
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
        elif 'ON 3RD READING' in motion:
            type = 'reading:3'
        else:
            type = 'other'

        vote = Vote(chamber, None, motion, None,
                    None, None, None)
        vote['type'] = type
        vote.add_source(url)

        (fd, temp_path) = tempfile.mkstemp()
        self.urlretrieve(url, temp_path)

        html = pdf_to_lxml(temp_path)
        os.close(fd)
        os.remove(temp_path)

        vote_type = None
        total_re = re.compile('^Total--(\d+)$')
        body = html.xpath('string(/html/body)')

        date_match = re.search('Date: (\d{1,2}/\d{1,2}/\d{4})', body)
        try:
            date = date_match.group(1)
        except AttributeError:
            self.warning("BAD VOTE: date error")
            return

        vote['date'] = dt.datetime.strptime(date, '%m/%d/%Y')

        for line in body.replace(u'\xa0', '\n').split('\n'):
            line = line.replace('&nbsp;', '').strip()
            if not line:
                continue

            if line in ('YEAS', 'NAYS', 'ABSENT'):
                vote_type = {'YEAS': 'yes', 'NAYS': 'no',
                             'ABSENT': 'other'}[line]
            elif line in ('Total', '--'):
                vote_type = None
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

        # tally counts
        vote['yes_count'] = len(vote['yes_votes'])
        vote['no_count'] = len(vote['no_votes'])
        vote['other_count'] = len(vote['other_votes'])

        # The PDFs oddly don't say whether a vote passed or failed.
        # Hopefully passage just requires yes_votes > not_yes_votes
        if vote['yes_count'] > (vote['no_count'] + vote['other_count']):
            vote['passed'] = True
        else:
            vote['passed'] = False

        bill.add_vote(vote)

    def scrape_bill_page(self, chamber, session, bill_url, bill_type):
        page = self.lxmlize(bill_url)
        author = self.get_one_xpath(
            page,
            "//a[@id='ctl00_PageBody_LinkAuthor']/text()"
        )

        sbp = lambda x: self.scrape_bare_page(page.xpath(
            "//a[contains(text(), '%s')]" % (x))[0].attrib['href'])

        authors = [x.text for x in sbp("Authors")]

        try:
            digests = sbp("Digests")
        except IndexError:
            digests = []

        try:
            versions = sbp("Text")
        except IndexError:
            versions = []

        title = page.xpath(
            "//span[@id='ctl00_PageBody_LabelShortTitle']/text()")[0]
        actions = page.xpath(
            "//div[@id='ctl00_PageBody_PanelBillInfo']/"
            "/table[@style='font-size:small']/tr")

        bill_id = page.xpath(
            "//span[@id='ctl00_PageBody_LabelBillID']/text()")[0]

        bill_type = {"B": "bill", "CR": "concurrent resolution"}[bill_type[1:]]
        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(bill_url)

        authors.remove(author)
        bill.add_sponsor('primary', author)
        for author in authors:
            bill.add_sponsor('cosponsor', author)

        for digest in digests:
            bill.add_document(digest.text,
                              digest.attrib['href'],
                              mimetype="application/pdf")

        for version in versions:
            bill.add_version(version.text,
                             version.attrib['href'],
                             mimetype="application/pdf")

        flags = {
            "prefiled": ["bill:filed"],
            "referred to the committee": ["committee:referred"],
            "sent to the house": ['bill:passed'],
            "ordered returned to the house": ['bill:passed'],
            "ordered to the senate": ['bill:passed'],
            "signed by the governor": ['governor:signed'],
            "sent to the governor": ['governor:received'],
        }

        try:
            votes_link = page.xpath("//a[text() = 'Votes']")[0]
            self.scrape_votes(bill, votes_link.attrib['href'])
        except IndexError:
            # Some bills don't have any votes
            pass


        for action in actions:
            date, chamber, page, text = [x.text for x in action.xpath(".//td")]
            date += "/%s" % (session)  # Session is April --> June. Prefiles
            # look like they're in January at earliest.
            date = dt.datetime.strptime(date, "%m/%d/%Y")
            chamber = {"S": "upper", "H": "lower", "J": 'joint'}[chamber]

            cat = []
            for flag in flags:
                if flag in text.lower():
                    cat += flags[flag]

            if cat == []:
                cat = ["other"]
            bill.add_action(chamber, text, date, cat)

        self.save_bill(bill)
