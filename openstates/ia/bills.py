import re
import datetime

from billy.scrape.bills import BillScraper, Bill

import lxml.html


def get_popup_url(link):
    onclick = link.attrib['onclick']
    return re.match(r'openWin\("(.*)"\)$', onclick).group(1)


class IABillScraper(BillScraper):
    state = 'ia'

    def scrape(self, chamber, session):
        url = ("http://coolice.legis.state.ia.us/Cool-ICE/default.asp?"
               "category=billinfo&service=Billbook&frm=2&hbill=HF697%20"
               "%20%20%20&cham=House&amend=%20%20%20%20%20%20&am2nd=%20"
               "%20%20%20%20%20&am3rd=%20%20%20%20%20%20&version=red;"
               "%20%20%20%20&menu=true&ga=84")
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
                version_url = re.sub(r'frm=2', 'frm=3', url)
            else:
                version_url = option.attrib['value'] + "&frm=3"
            bill.add_version(version_name, version_url)

        if not bill['versions']:
            version_url = re.sub(r'frm=2', 'frm=3', url)
            bill.add_version('Introduced', version_url)

        sponsors = page.xpath("string(//table[2]/tr[3])").strip()
        sponsor_re = r'\w+(?:, [A-Z]\.)?(?:,|(?: and)|\.$)'
        for sponsor in re.findall(sponsor_re, sponsors):
            sponsor = sponsor.replace(' and', '').strip(' .,')
            if sponsor == 'Means':
                # oops, gets mangled by the regex
                sponsor = 'Ways & Means'
            bill.add_sponsor('sponsor', sponsor)

        for tr in page.xpath("//table[3]/tr"):
            date = tr.xpath("string(td[1])").strip()
            if date.startswith("***"):
                continue
            date = datetime.datetime.strptime(date, "%B %d, %Y").date()

            action = tr.xpath("string(td[2])").strip()
            action = re.sub(r'\s+', ' ', action)

            if 'S.J.' in action or 'SCS' in action:
                actor = 'upper'
            elif 'H.J.' in action or 'HCS' in action:
                actor = 'lower'

            if action.startswith('Introduced'):
                atype = 'bill:introduced'
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
            else:
                atype = 'other'

            bill.add_action(actor, action, date, type=atype)

        self.save_bill(bill)
