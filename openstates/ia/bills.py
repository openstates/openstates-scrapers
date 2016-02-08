import re
import datetime
import lxml.html
from collections import defaultdict
from billy.scrape.bills import BillScraper, Bill
from openstates.utils import LXMLMixin
from .scraper import InvalidHTTPSScraper


def get_popup_url(link):
    onclick = link.attrib['onclick']
    return re.match(r'openWin\("(.*)"\)$', onclick).group(1)


class IABillScraper(InvalidHTTPSScraper, BillScraper, LXMLMixin):
    jurisdiction = 'ia'

    _subjects = defaultdict(list)

    def _build_subject_map(self, session):
        # if already built a subject map, skip doing it again
        if self._subjects:
            return

        session_id = self.metadata['session_details'][session]['number']
        url = ('http://coolice.legis.state.ia.us/Cool-ICE/default.asp?'
               'Category=BillInfo&Service=DspGASI&ga=%s&frame=y') % session_id
        doc = self.lxmlize(url)

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
        bill_offset = "HF697"  # Try both. We need a good bill page to scrape
        bill_offset = "HF27"   # from. Check for "HF " + bill_offset

        base_url = "https://www.legis.iowa.gov/legislation/BillBook?ga=%s&ba=%s"

        url = (base_url % (session_id, bill_offset))
        page = self.lxmlize(url)

        if chamber == 'upper':
            bname = 'senateBills'
        else:
            bname = 'houseBills'

        for option in page.xpath("//select[@name = '%s']/option" % bname):
            bill_id = option.text.strip()

            if bill_id.lower() == 'pick one':
                continue

            bill_url = (base_url % (session_id, bill_id))

            self.scrape_bill(chamber, session, session_id, bill_id, bill_url)

    def scrape_bill(self, chamber, session, session_id, bill_id, url):
        sidebar = self.lxmlize(url)

        try:
            hist_url = sidebar.xpath('//a[contains(., "Bill History")]')[0].attrib['href']
        except IndexError:
            # where is it?
            return

        try:
            page = self.lxmlize(hist_url)
        except:
            self.warning("URL: %s gives us a 500 error. Aborting." % url)
            return 

        title = page.xpath('string(//div[@id="content"]/div[@class='
            '"divideVert"]/div[not(@class)])').strip()

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

        # base url for text version (version_abbrev, session_id, bill_id)
        version_html_url_template = 'https://www.legis.iowa.gov/docs/'\
            'publications/LG{}/{}/attachments/{}.html'
        version_pdf_url_template = 'https://www.legis.iowa.gov/docs/'\
            'publications/LG{}/{}/{}.pdf'
        
        # get pieces of version_link
        vpieces = sidebar.xpath('//select[@id="billVersions"]/option')
        if vpieces:
            for version in vpieces:
                version_name = version.text 
                version_abbrev = version.xpath('string(@value)')

                # Get HTML document of bill version.
                version_html_url = version_html_url_template.format(
                    version_abbrev.upper(),
                    session_id,
                    bill_id.replace(' ', ''))

                bill.add_version(version_name, version_html_url,
                    mimetype='text/html')

                # Get PDF document of bill version.
                version_pdf_url = version_pdf_url_template.format(
                    version_abbrev.upper(),
                    session_id,
                    bill_id.replace(' ', ''))

                bill.add_version(version_name, version_pdf_url,
                    mimetype='application/pdf')

        sponsors_str = page.xpath("string(//div[@id='content']/div[@class='divideVert']/div[@class='divideVert'])").strip()
        if re.search('^By ', sponsors_str):
            sponsors = re.split(',| and ', sponsors_str.split('By ')[1])
        # for some bills sponsors listed in different format
        else:
            sponsors = re.findall('[\w-]+(?:, [A-Z]\.)?(?:,|(?: and)|\.$)', sponsors_str)

        for sponsor in sponsors:
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

        for tr in page.xpath("//table[contains(@class, 'billActionTable')]/tbody/tr"):
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
                        # These links aren't given hrefs for some reason (needs to be fixed upstream)
                        try:
                            url = anchor.attrib['href']
                        except:
                            continue 

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

            if re.search('END OF \d+ ACTIONS', action):
                continue 

            bill.add_action(actor, action, date, type=atype)

        bill['subjects'] = self._subjects[bill_id]
        self.save_bill(bill)
