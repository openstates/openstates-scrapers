import re
import datetime
from collections import defaultdict

from billy.scrape.bills import BillScraper, Bill

import lxml.html


def chamber_abbr(chamber):
    if chamber == 'upper':
        return 'S'
    else:
        return 'H'


def session_url(session):
    return "http://www.lrc.ky.gov/record/%s/" % session[2:]


class KYBillScraper(BillScraper):
    jurisdiction = 'ky'

    _subjects = defaultdict(list)

    def scrape_subjects(self, session):
        if self._subjects:
            return

        url = session_url(session) + 'indexhd.htm'
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        for subj_link in doc.xpath('//a[contains(@href, ".htm")]/@href'):
            # subject links are 4 numbers
            if re.match('\d{4}', subj_link):
                subj_html = self.get(session_url(session) + subj_link).text
                sdoc = lxml.html.fromstring(subj_html)
                subject = sdoc.xpath('//p[@class="PageHeader"]/text()')[0]
                for bill in sdoc.xpath('//div[@id="bul"]/a/text()'):
                    self._subjects[bill.replace(' ', '')].append(subject)


    def scrape(self, chamber, session):
        self.scrape_subjects(session)
        self.scrape_session(chamber, session)
        for sub in self.metadata['session_details'][session].get('sub_sessions', []):
            self.scrape_session(chamber, sub)

    def scrape_session(self, chamber, session):
        bill_url = session_url(session) + "bills_%s.htm" % chamber_abbr(chamber)
        self.scrape_bill_list(chamber, session, bill_url)

        resolution_url = session_url(session) + "res_%s.htm" % (
            chamber_abbr(chamber))
        self.scrape_bill_list(chamber, session, resolution_url)

    def scrape_bill_list(self, chamber, session, url):
        bill_abbr = None
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a"):
            if re.search(r"\d{1,4}\.htm", link.attrib.get('href', '')):
                bill_id = link.text

                match = re.match(r'([A-Z]+)\s+\d+', link.text)
                if match:
                    bill_abbr = match.group(1)
                    bill_id = bill_id.replace(' ', '')
                else:
                    bill_id = bill_abbr + bill_id

                self.parse_bill(chamber, session, bill_id,
                                link.attrib['href'])

    def parse_bill(self, chamber, session, bill_id, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        try:
            short_bill_id = re.sub(r'(H|S)([JC])R', r'\1\2', bill_id)

            version_link = page.xpath("//a[contains(@href, '%s/bill.doc')]" % short_bill_id)[0]
        except IndexError:
            # Bill withdrawn
            return

        pars = version_link.xpath("following-sibling::p")
        if len(pars) == 2:
            title = pars[0].xpath("string()")
            action_p = pars[1]
        else:
            title = pars[0].getprevious().tail
            if not title:
                self.warning('walking backwards to get bill title, error prone!')
                title = pars[0].getprevious().getprevious()
                while not title.tail:
                    title = title.getprevious()
                title = title.tail
                self.warning('got title the dangerous way: %s' % title)
            action_p = pars[0]

        title = re.sub(ur'[\s\xa0]+', ' ', title).strip()

        if 'CR' in bill_id:
            bill_type = 'concurrent resolution'
        elif 'JR' in bill_id:
            bill_type = 'joint resolution'
        elif 'R' in bill_id:
            bill_type = 'resolution'
        else:
            bill_type = 'bill'

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill['subjects'] = self._subjects[bill_id]
        bill.add_source(url)

        bill.add_version("Most Recent Version",
                         version_link.attrib['href'],
                         mimetype='application/msword')

        for link in page.xpath("//a[contains(@href, 'legislator/')]"):
            bill.add_sponsor('primary', link.text.strip())

        for line in action_p.xpath("string()").split("\n"):
            action = line.strip()
            if (not action or action == 'last action' or
                'Prefiled' in action or 'vetoed' in action):
                continue

            # add year onto date
            action_date = "%s %s" % (action.split('-')[0],
                                     session[0:4])
            action_date = datetime.datetime.strptime(
                action_date, '%b %d %Y')

            action = '-'.join(action.split('-')[1:])

            if action.endswith('House') or action.endswith('(H)'):
                actor = 'lower'
            elif action.endswith('Senate') or action.endswith('(S)'):
                actor = 'upper'
            else:
                actor = chamber

            atype = []
            if action.startswith('introduced in'):
                atype.append('bill:introduced')
                if '; to ' in action:
                    atype.append('committee:referred')
            elif action.startswith('signed by Governor'):
                atype.append('governor:signed')
            elif re.match(r'^to [A-Z]', action):
                atype.append('committee:referred')
            elif action == 'adopted by voice vote':
                atype.append('bill:passed')

            if '1st reading' in action:
                atype.append('bill:reading:1')
            if '3rd reading' in action:
                atype.append('bill:reading:3')
                if 'passed' in action:
                    atype.append('bill:passed')
            if '2nd reading' in action:
                atype.append('bill:reading:2')

            if 'R' in bill_id and 'adopted by voice vote' in action:
                atype.append('bill:passed')

            amendment_re = (r'floor amendments?( \([a-z\d\-]+\))*'
                            r'( and \([a-z\d\-]+\))? filed')
            if re.search(amendment_re, action):
                atype.append('amendment:introduced')

            if not atype:
                atype = ['other']

            bill.add_action(actor, action, action_date, type=atype)

        try:
            votes_link = page.xpath(
                "//a[contains(@href, 'vote_history.pdf')]")[0]
            bill.add_document("Vote History",
                              votes_link.attrib['href'])
        except IndexError:
            # No votes
            pass

        # Ugly Hack Alert!
        # find actions before introduction date and subtract 1 from the year
        # if the date is after introduction
        intro_date = None
        for i, action in enumerate(bill['actions']):
            if 'bill:introduced' in action['type']:
                intro_date = action['date']
                break
        for action in bill['actions'][:i]:
            if action['date'] > intro_date:
                action['date'] = action['date'].replace(year=action['date'].year-1)
                self.debug('corrected year for %s', action['action'])

        self.save_bill(bill)
