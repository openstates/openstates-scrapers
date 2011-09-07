import re
import datetime
from collections import defaultdict

from billy.scrape.bills import BillScraper, Bill

import lxml.html


def get_popup_url(link):
    onclick = link.attrib['onclick']
    return re.match(r'openWin\("(.*)"\)$', onclick).group(1)


class IABillScraper(BillScraper):
    state = 'ia'

    session_id_map = {'2011-2012': '84'}
    _subjects = defaultdict(list)

    def _build_subject_map(self, session):
        # if already built a subject map, skip doing it again
        if self._subjects:
            return

        session_id = self.session_id_map[session]
        url = ('http://coolice.legis.state.ia.us/Cool-ICE/default.asp?'
               'Category=BillInfo&Service=DspGASI&ga=%s&frame=y') % session_id
        doc = lxml.html.fromstring(self.urlopen(url))

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
            subj_doc = lxml.html.fromstring(self.urlopen(subj_url))
            bill_ids = subj_doc.xpath('//td[@width="10%"]/a/text()')
            for bill_id in bill_ids:
                self._subjects[bill_id.replace(' ', '')].append(subject)


    def scrape(self, chamber, session):

        self._build_subject_map(session)

        url = ("http://coolice.legis.state.ia.us/Cool-ICE/default.asp?"
               "category=billinfo&service=Billbook&frm=2&hbill=HF697%20"
               "%20%20%20&cham=House&amend=%20%20%20%20%20%20&am2nd=%20"
               "%20%20%20%20%20&am3rd=%20%20%20%20%20%20&version=red;"
               "%20%20%20%20&menu=true&ga=") + self.session_id_map[session]
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        if chamber == 'upper':
            bname = 'sbill'
        else:
            bname = 'hbill'

        for option in page.xpath("//select[@name = '%s']/option" % bname):
            bill_id = option.text.strip()
            if bill_id == 'Pick One':
                continue

            if 'HSB' in bill_id or 'SSB' in bill_id:
                continue

            bill_url = option.attrib['value'].strip() + '&frm=2'

            self.scrape_bill(chamber, session, bill_id, bill_url)

    def scrape_bill(self, chamber, session, bill_id, url):
        sidebar = lxml.html.fromstring(self.urlopen(url))

        try:
            hist_url = get_popup_url(
                sidebar.xpath("//a[contains(., 'Bill History')]")[0])
        except IndexError:
            # where is it?
            return

        page = lxml.html.fromstring(self.urlopen(hist_url))
        page.make_links_absolute(hist_url)

        title = page.xpath("string(//table[2]/tr[4])").strip()

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

        for option in sidebar.xpath("//select[@name='BVer']/option"):
            version_name = option.text.strip()
            if option.get('selected'):
                version_url = re.sub(r'frm=2', 'frm=1', url)
            else:
                version_url = option.attrib['value']
            bill.add_version(version_name, version_url)

        if not bill['versions']:
            version_url = re.sub(r'frm=2', 'frm=3', url)
            bill.add_version('Introduced', version_url)

        sponsors = page.xpath("string(//table[2]/tr[3])").strip()
        sponsor_re = r'[\w-]+(?:, [A-Z]\.)?(?:,|(?: and)|\.$)'
        for sponsor in re.findall(sponsor_re, sponsors):
            sponsor = sponsor.replace(' and', '').strip(' .,')

            # a few sponsors get mangled by our regex
            sponsor = {
                'Means': 'Ways & Means',
                'Safety': 'Public Safety',
                'Resources': 'Human Resources',
                'Affairs': 'Veterans Affairs',
                'Protection': 'Environmental Protection',
                'Government': 'State Government',
                'Boef': 'De Boef'}.get(sponsor, sponsor)

            bill.add_sponsor('sponsor', sponsor)

        for tr in page.xpath("//table[3]/tr"):
            date = tr.xpath("string(td[1])").strip()
            if date.startswith("***"):
                continue
            elif "No history is recorded at this time." in date:
                return
            date = datetime.datetime.strptime(date, "%B %d, %Y").date()

            action = tr.xpath("string(td[2])").strip()
            action = re.sub(r'\s+', ' ', action)

            if 'S.J.' in action or 'SCS' in action:
                actor = 'upper'
            elif 'H.J.' in action or 'HCS' in action:
                actor = 'lower'

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

            bill.add_action(actor, action, date, type=atype)

        bill['subjects'] = self._subjects[bill_id]
        self.save_bill(bill)
