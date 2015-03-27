import re
import datetime
from collections import defaultdict

from billy.scrape.bills import BillScraper, Bill

import lxml.html

from .scraper import InvalidHTTPSScraper


def get_popup_url(link):
    onclick = link.attrib['onclick']
    return re.match(r'openWin\("(.*)"\)$', onclick).group(1)


class IABillScraper(InvalidHTTPSScraper, BillScraper):
    jurisdiction = 'ia'

    _subjects = defaultdict(list)

    def _build_subject_map(self, session):
        # if already built a subject map, skip doing it again
        if self._subjects:
            return

        session_id = self.metadata['session_details'][session]['number']
        url = ('http://coolice.legis.state.ia.us/Cool-ICE/default.asp?'
               'Category=BillInfo&Service=DspGASI&ga=%s&frame=y') % session_id
        doc = lxml.html.fromstring(self.get(url).text)

        # get all subjects from dropdown
        for option in doc.xpath('//select[@name="SelectOrig"]/option')[1:]:
            # if it has a "See also" strip that part off
            subject = option.text.strip().split(' - See also')[0]
            # skip sub-subjects
            if subject.startswith('--'):
                continue

            value = option.get('value')

            # open the subject url and get all bill_ids
            subj_url = ('http://coolice.legis.state.ia.us/Cool-ICE/default.asp'
                        '?Category=BillInfo&Service=DsplData&var=gasi&ga=%s&'
                        'typ=o&key=%s') % (session_id, value)
            subj_doc = lxml.html.fromstring(self.get(subj_url).text)
            bill_ids = subj_doc.xpath('//td[@width="10%"]/a/text()')
            for bill_id in bill_ids:
                self._subjects[bill_id.replace(' ', '')].append(subject)

    def scrape(self, chamber, session):

        self._build_subject_map(session)

        session_id = self.metadata['session_details'][session]['number']
        bill_offset = "697"  # Try both. We need a good bill page to scrape
        bill_offset = "27"   # from. Check for "HF " + bill_offset

        url = ("http://coolice.legis.state.ia.us/Cool-ICE/default.asp?"
               "category=billinfo&service=Billbook&frm=2&hbill=HF%s%20"
               "%20%20%20&cham=House&amend=%20%20%20%20%20%20&am2nd=%20"
               "%20%20%20%20%20&am3rd=%20%20%20%20%20%20&version=red;"
               "%20%20%20%20&menu=true&ga=" % (bill_offset)) + session_id
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        if chamber == 'upper':
            bname = 'sbill'
        else:
            bname = 'hbill'

        for option in page.xpath("//select[@name = '%s']/option" % bname):
            bill_id = option.text.strip()
            if bill_id == 'Pick One':
                continue

            bill_url = option.attrib['value'].strip() + '&frm=2'

            self.scrape_bill(chamber, session, bill_id, bill_url)

    def scrape_bill(self, chamber, session, bill_id, url):
        sidebar = lxml.html.fromstring(self.get(url).text)

        try:
            hist_url = get_popup_url(
                sidebar.xpath("//a[contains(., 'Bill History')]")[0])
        except IndexError:
            # where is it?
            return

        page = lxml.html.fromstring(self.get(hist_url).text)
        page.make_links_absolute(hist_url)

        title = page.xpath("string(//table[2]/tr[4])").strip()
        if title == '':
            self.warning("URL: %s gives us an *EMPTY* bill. Aborting." % url)
            return

        if title.lower().startswith("in"):
            title = page.xpath("string(//table[2]/tr[3])").strip()

        if 'HR' in bill_id or 'SR' in bill_id:
            bill_type = ['resolution']
        elif 'HJR' in bill_id or 'SJR' in bill_id:
            bill_type = ['joint resolution']
        elif 'HCR' in bill_id or 'SCR' in bill_id:
            bill_type = ['concurrent resolution']
        else:
            bill_type = ['bill']

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill.add_source(hist_url)

        # get pieces of version_link
        vpieces = sidebar.xpath('//a[contains(string(.), "HTML")]/@href')
        if vpieces:
            version_base, version_type, version_end = vpieces[0].rsplit('/', 2)
            versions = [o.strip() for o in
                        sidebar.xpath("//select[@name='BVer']/option/text()")]
            # if there are no options, put version_type in one
            if not versions:
                versions = [version_type]

            for version_name in versions:
                version_url = '/'.join((version_base, version_name,
                                        version_end))
                bill.add_version(version_name, version_url,
                                 mimetype='text/html')
        else:
            bill.add_version('Introduced',
                sidebar.xpath('//a[contains(string(.), "PDF")]/@href')[0],
                             mimetype='application/pdf'
                            )

        sponsors = page.xpath("string(//table[2]/tr[3])").strip()
        sponsor_re = r'[\w-]+(?:, [A-Z]\.)?(?:,|(?: and)|\.$)'
        for sponsor in re.findall(sponsor_re, sponsors):
            sponsor = sponsor.replace(' and', '').strip(' .,')

            # a few sponsors get mangled by our regex
            sponsor = {
                'Means': 'Ways & Means',
                'Iowa': 'Economic Growth/Rebuild Iowa',
                'Safety': 'Public Safety',
                'Resources': 'Human Resources',
                'Affairs': 'Veterans Affairs',
                'Protection': 'Environmental Protection',
                'Government': 'State Government',
                'Boef': 'De Boef'}.get(sponsor, sponsor)

            if sponsor[0].islower():
                # SSBs catch cruft in it ('charges', 'overpayments')
                # https://sunlight.atlassian.net/browse/DATA-286
                continue

            bill.add_sponsor('primary', sponsor)

        for tr in page.xpath("//table[3]/tr"):
            date = tr.xpath("string(td[contains(text(), ', 20')])").strip()
            if date.startswith("***"):
                continue
            elif "No history is recorded at this time." in date:
                return
            if date == "":
                continue

            date = datetime.datetime.strptime(date, "%B %d, %Y").date()

            action = tr.xpath("string(td[2])").strip()
            action = re.sub(r'\s+', ' ', action)

            # Capture any amendment links.
            version_urls = set(version['url'] for version in bill['versions'])
            if 'amendment' in action.lower():
                for anchor in tr.xpath('td[2]/a'):
                    if '-' in anchor.text:
                        url = anchor.attrib['href']
                        if url not in version_urls:
                            bill.add_version(anchor.text, url, mimetype='text/html')
                            version_urls.add(url)

            if 'S.J.' in action or 'SCS' in action:
                actor = 'upper'
            elif 'H.J.' in action or 'HCS' in action:
                actor = 'lower'
            else:
                actor = "other"

            action = re.sub(r'(H|S)\.J\.\s+\d+\.$', '', action).strip()

            if action.startswith('Introduced'):
                atype = ['bill:introduced']
                if ', referred to' in action:
                    atype.append('committee:referred')
            elif action.startswith('Read first time'):
                atype = 'bill:reading:1'
            elif action.startswith('Referred to'):
                atype = 'committee:referred'
            elif action.startswith('Sent to Governor'):
                atype = 'governor:received'
            elif action.startswith('Reported Signed by Governor'):
                atype = 'governor:signed'
            elif action.startswith('Signed by Governor'):
                atype = 'governor:signed'
            elif action.startswith('Vetoed by Governor'):
                atype = 'governor:vetoed'
            elif action.startswith('Item veto'):
                atype = 'governor:vetoed:line-item'
            elif re.match(r'Passed (House|Senate)', action):
                atype = 'bill:passed'
            elif re.match(r'Amendment (S|H)-\d+ filed', action):
                atype = ['amendment:introduced']
                if ', adopted' in action:
                    atype.append('amendment:passed')
            elif re.match(r'Amendment (S|H)-\d+( as amended,)? adopted',
                          action):
                atype = 'amendment:passed'
            elif re.match('Amendment (S|N)-\d+ lost', action):
                atype = 'amendment:failed'
            elif action.startswith('Resolution filed'):
                atype = 'bill:introduced'
            elif action.startswith('Resolution adopted'):
                atype = 'bill:passed'
            elif (action.startswith('Committee report') and
                  action.endswith('passage.')):
                  atype = 'committee:passed'
            elif action.startswith('Withdrawn'):
                atype = 'bill:withdrawn'
            else:
                atype = 'other'

            if action.strip() == "":
                continue

            bill.add_action(actor, action, date, type=atype)

        bill['subjects'] = self._subjects[bill_id]
        self.save_bill(bill)
