import re
import datetime
import lxml.html
from collections import defaultdict
from pupa.scrape import Scraper, Bill


class IABillScraper(Scraper):

    _subjects = defaultdict(list)

    def _build_subject_map(self, session):
        # if already built a subject map, skip doing it again
        if self._subjects:
            return

        session_id = self.get_session_id(session)
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

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        self._build_subject_map(session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        # We need a good bill page to scrape from. Check for "HF " + bill_offset
        bill_offset = "HF27"

        base_url = "https://www.legis.iowa.gov/legislation/BillBook?ga=%s&ba=%s"

        session_id = self.get_session_id(session)
        url = (base_url % (session_id, bill_offset))
        page = lxml.html.fromstring(self.get(url).text)

        if chamber == 'upper':
            bname = 'senateBills'
        else:
            bname = 'houseBills'

        for option in page.xpath("//select[@name = '%s']/option" % bname):
            bill_id = option.text.strip()

            if bill_id.lower() == 'pick one':
                continue

            bill_url = (base_url % (session_id, bill_id))

            yield self.scrape_bill(chamber, session, session_id, bill_id, bill_url)

    def scrape_bill(self, chamber, session, session_id, bill_id, url):
        sidebar = lxml.html.fromstring(self.get(url).text)
        sidebar.make_links_absolute("https://www.legis.iowa.gov")

        try:
            hist_url = sidebar.xpath('//a[contains(., "Bill History")]')[0].attrib['href']
        except IndexError:
            # where is it?
            return

        page = lxml.html.fromstring(self.get(hist_url).text)
        page.make_links_absolute("https://www.legis.iowa.gov")

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

        bill = Bill(
                bill_id,
                legislative_session=session,
                chamber=chamber,
                title=title,
                classification=bill_type)

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

                bill.add_version_link(
                    note=version_name,
                    url=version_html_url,
                    media_type='text/html')

                # Get PDF document of bill version.
                version_pdf_url = version_pdf_url_template.format(
                    version_abbrev.upper(),
                    session_id,
                    bill_id.replace(' ', ''))

                bill.add_version_link(
                    note=version_name,
                    url=version_pdf_url,
                    media_type='application/pdf')

        sponsors_str = page.xpath(
            "string(//div[@id='content']/div[@class='divideVert']/div[@class='divideVert'])"
        ).strip()
        if re.search('^By ', sponsors_str):
            sponsors = re.split(',| and ', sponsors_str.split('By ')[1])
        # for some bills sponsors listed in different format
        else:
            sponsors = re.findall(r'[\w-]+(?:, [A-Z]\.)?(?:,|(?: and)|\.$)', sponsors_str)

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

            bill.add_sponsorship(
                    name=sponsor,
                    classification='primary',
                    entity_type='person',
                    primary=True)

        for tr in page.xpath("//table[contains(@class, 'billActionTable')][1]/tbody/tr"):
            date = tr.xpath("string(td[contains(text(), ', 20')])").strip()
            if date.startswith("***"):
                continue
            elif "No history is recorded at this time." in date:
                return
            if date == "":
                continue

            date = datetime.datetime.strptime(date, "%B %d, %Y").date()

            action = tr.xpath("string(td[3])").strip()
            action = re.sub(r'\s+', ' ', action)

            # Capture any amendment links.
            links = [link for link in [version['links'] for version in bill.versions]]
            version_urls = [link['url'] for link in [i for sub in links for i in sub]]
            if 'amendment' in action.lower():
                for anchor in tr.xpath('td[2]/a'):
                    if '-' in anchor.text:
                        # These links aren't given hrefs for some reason
                        # (needs to be fixed upstream)
                        try:
                            url = anchor.attrib['href']
                        except KeyError:
                            continue

                        if url not in version_urls:
                            bill.add_version_link(
                                    note=anchor.text,
                                    url=url,
                                    media_type='text/html')
                            version_urls.append(url)

            if 'S.J.' in action or 'SCS' in action:
                actor = 'upper'
            elif 'H.J.' in action or 'HCS' in action:
                actor = 'lower'
            else:
                actor = "legislature"

            action = re.sub(r'(H|S)\.J\.\s+\d+\.$', '', action).strip()

            if action.startswith('Introduced'):
                atype = ['introduction']
                if ', referred to' in action:
                    atype.append('referral-committee')
            elif action.startswith('Read first time'):
                atype = 'reading-1'
            elif action.startswith('Referred to'):
                atype = 'referral-committee'
            elif action.startswith('Sent to Governor'):
                atype = 'executive-receipt'
            elif action.startswith('Reported Signed by Governor'):
                atype = 'executive-signature'
            elif action.startswith('Signed by Governor'):
                atype = 'executive-signature'
            elif action.startswith('Vetoed by Governor'):
                atype = 'executive-veto'
            elif action.startswith('Item veto'):
                atype = 'executive-veto-line-item'
            elif re.match(r'Passed (House|Senate)', action):
                atype = 'passage'
            elif re.match(r'Amendment (S|H)-\d+ filed', action):
                atype = ['amendment-introduction']
                if ', adopted' in action:
                    atype.append('amendment-passage')
            elif re.match(r'Amendment (S|H)-\d+( as amended,)? adopted',
                          action):
                atype = 'amendment-passage'
            elif re.match(r'Amendment (S|N)-\d+ lost', action):
                atype = 'amendment-failure'
            elif action.startswith('Resolution filed'):
                atype = 'introduction'
            elif action.startswith('Resolution adopted'):
                atype = 'passage'
            elif (action.startswith('Committee report') and
                  action.endswith('passage.')):
                    atype = 'committee-passage'
            elif action.startswith('Withdrawn'):
                atype = 'withdrawal'
            else:
                atype = None

            if action.strip() == "":
                continue

            if re.search(r'END OF \d+ ACTIONS', action):
                continue

            if '$history' not in action:
                bill.add_action(
                        description=action,
                        date=date,
                        chamber=actor,
                        classification=atype)

        for subject in self._subjects[bill_id]:
            bill.add_subject(subject['Name'])

        yield bill

    def get_session_id(self, session):
        return {"2011-2012": "84",
                "2013-2014": "85",
                "2015-2016": "86",
                "2017-2018": "87"}[session]
