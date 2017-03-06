import datetime as dt
import lxml.html
from pupa.scrape import Scraper, Bill


class NCBillScraper(Scraper):

    _action_classifiers = {
        'Vetoed': 'executive-veto',
        'Signed By Gov': 'executive-signature',
        'Signed by Gov': 'executive-signature',
        'Pres. To Gov.': 'executive-receipt',
        'Withdrawn from ': 'withdrawal',
        'Ref ': 'referral-committee',
        'Re-ref ': 'referral-committee',
        'Reptd Fav': 'committee-passage-favorable',
        'Reptd Unfav': 'committee-passage-unfavorable',
        'Passed 1st Reading': 'reading-1',
        'Passed 2nd Reading': 'reading-2',
        'Passed 3rd Reading': ['passage', 'reading-3'],
        'Passed 2nd & 3rd Reading': ['passage', 'reading-2',
                                     'reading-3'],
        'Failed 3rd Reading': ['failure', 'reading-3'],
        'Filed': 'introduction',
        'Adopted': 'passage',       # resolutions
        'Concurred In': 'amendment-passage',
        'Com Amend Adopted': 'amendment-passage',
        'Assigned To': 'referral-committee',
        'Amendment Withdrawn': 'amendment-withdrawal',
        'Amendment Offered': 'amendment-introduction',
        'Amend Failed': 'amendment-failure',
        'Amend Adopted': 'amendment-passage',
    }

    def is_latest_session(self, session):
        return self.metadata['terms'][-1]['sessions'][-1] == session

    def scrape_bill(self, chamber, session, bill_id):
        # there will be a space in bill_id if we're doing a one-off bill scrape
        # convert HB 102 into H102
        if ' ' in bill_id:
            bill_id = bill_id[0] + bill_id.split(' ')[-1]

        # if chamber comes in as House/Senate convert to lower/upper
        if chamber == 'Senate':
            chamber = 'upper'
        elif chamber == 'House':
            chamber = 'lower'

        bill_detail_url = ('http://www.ncga.state.nc.us/gascripts/'
                           'BillLookUp/BillLookUp.pl?Session=%s&BillID=%s') % (session, bill_id)

        # parse the bill data page, finding the latest html text
        data = self.get(bill_detail_url).text
        doc = lxml.html.fromstring(data)

        title_div_txt = doc.xpath('//td[@style="text-align: center; white-space: nowrap; '
                                  'width: 60%; font-weight: bold; font-size: x-large;"]/text()')[0]
        if 'Joint Resolution' in title_div_txt:
            bill_type = 'joint resolution'
            bill_id = bill_id[0] + 'JR ' + bill_id[1:]
        elif 'Resolution' in title_div_txt:
            bill_type = 'resolution'
            bill_id = bill_id[0] + 'R ' + bill_id[1:]
        elif 'Bill' in title_div_txt:
            bill_type = 'bill'
            bill_id = bill_id[0] + 'B ' + bill_id[1:]

        bill_title = doc.xpath('//div[@id="title"]')[0].text_content()

        bill = Bill(bill_id, legislative_session=session, title=bill_title, chamber=chamber,
                    classification=bill_type)
        bill.add_source(bill_detail_url)

        # skip first PDF link (duplicate link to cur version)
        if chamber == 'lower':
            link_xpath = '//a[contains(@href, "/Bills/House/PDF/")]'
        else:
            link_xpath = '//a[contains(@href, "/Bills/Senate/PDF/")]'
        for vlink in doc.xpath(link_xpath)[1:]:
            # get the name from the PDF link...
            version_name = vlink.text.replace(u'\xa0', ' ')
            # but neighboring span with anchor inside has the HTML version
            version_url = vlink.xpath('./following-sibling::span/a/@href')
            version_url = 'http://www.ncga.state.nc.us' + version_url[0]
            bill.add_version_link(version_name, version_url, media_type='text/html',
                                  on_duplicate='ignore')

        # sponsors
        spon_td = doc.xpath('//th[text()="Sponsors:"]/following-sibling::td')[0]
        # first sponsors are primary, until we see (Primary)
        spon_type = 'primary'
        for leg in spon_td.text_content().split(';'):
            name = leg.replace(u'\xa0', ' ').strip()
            if name.startswith('(Primary)'):
                name = name.replace('(Primary)', '').strip()
                spon_type = 'cosponsor'
            if not name:
                continue
            bill.add_sponsorship(name, classification=spon_type, entity_type='person',
                                 primary=(spon_type == 'primary'))

        # keywords
        kw_td = doc.xpath('//th[text()="Keywords:"]/following-sibling::td')[0]
        for subject in kw_td.text_content().split(', '):
            bill.add_subject(subject)

        # actions
        action_tr_xpath = '//td[starts-with(text(),"History")]/../../tr'
        # skip two header rows
        for row in doc.xpath(action_tr_xpath)[2:]:
            tds = row.xpath('td')
            act_date = tds[0].text
            actor = tds[1].text or ''
            # if text is blank, try diving in
            action = tds[2].text.strip() or tds[2].text_content().strip()

            act_date = dt.datetime.strptime(act_date, '%m/%d/%Y').strftime('%Y-%m-%d')

            if actor == 'Senate':
                actor = 'upper'
            elif actor == 'House':
                actor = 'lower'
            else:
                actor = 'executive'

            for pattern, atype in self._action_classifiers.items():
                if action.startswith(pattern):
                    break
            else:
                atype = None

            bill.add_action(action, act_date, chamber=actor, classification=atype)

        return bill

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        url = ('http://www.ncga.state.nc.us/gascripts/SimpleBillInquiry/'
               'displaybills.pl?Session=%s&tab=Chamber&Chamber=%s') % (session, chamber)

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        for row in doc.xpath('//table[@cellpadding=3]/tr')[1:]:
            bill_id = row.xpath('td[1]/a/text()')[0]
            yield self.scrape_bill(chamber, session, bill_id)
