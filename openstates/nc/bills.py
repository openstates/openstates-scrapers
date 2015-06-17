import datetime as dt
import re
from collections import defaultdict

import lxml.html

from billy.scrape.bills import BillScraper, Bill

class NCBillScraper(BillScraper):

    jurisdiction = 'nc'

    _action_classifiers = {
        'Vetoed': 'governor:vetoed',
        'Signed By Gov': 'governor:signed',
        'Signed by Gov': 'governor:signed',
        'Pres. To Gov.': 'governor:received',
        'Withdrawn from ': 'bill:withdrawn',
        'Ref ': 'committee:referred',
        'Re-ref ': 'committee:referred',
        'Reptd Fav': 'committee:passed:favorable',
        'Reptd Unfav': 'committee:passed:unfavorable',
        'Passed 1st Reading': 'bill:reading:1',
        'Passed 2nd Reading': 'bill:reading:2',
        'Passed 3rd Reading': ['bill:passed', 'bill:reading:3'],
        'Passed 2nd & 3rd Reading': ['bill:passed', 'bill:reading:2',
                                     'bill:reading:3'],
        'Failed 3rd Reading': ['bill:failed', 'bill:reading:3'],
        'Filed': 'bill:introduced',
        'Adopted': 'bill:passed',       # resolutions
        'Concurred In': 'amendment:passed',
        'Com Amend Adopted': 'amendment:passed',
        'Became Law w/o Signature': 'other',
        'Assigned To': 'committee:referred',
        'Amendment Withdrawn': 'amendment:withdrawn',
        'Amendment Offered': 'amendment:introduced',
        'Amend Failed': 'amendment:failed',
        'Amend Adopted': 'amendment:passed',
    }

    def is_latest_session(self, session):
        return self.metadata['terms'][-1]['sessions'][-1] == session

    def build_subject_map(self):
        # don't scan subject list twice in one run
        if hasattr(self, 'subject_map'):
            return

        self.subject_map = defaultdict(list)
        cur_subject = None

        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        for letter in letters:
            url = 'http://www.ncga.state.nc.us/gascripts/Reports/keywords.pl?Letter=' + letter
            html = self.get(url).text
            doc = lxml.html.fromstring(html)
            for td in doc.xpath('//td[@class="tableText"]'):
                if td.get('style') == 'font-weight: bold;':
                    cur_subject = td.text_content()
                else:

                    if cur_subject is None:
                        continue

                    bill_link = td.xpath('a/text()')
                    if bill_link:
                        self.subject_map[bill_link[0]].append(cur_subject)

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

        bill_detail_url = 'http://www.ncga.state.nc.us/gascripts/'\
            'BillLookUp/BillLookUp.pl?Session=%s&BillID=%s' % (
            session, bill_id)

        # parse the bill data page, finding the latest html text
        data = self.get(bill_detail_url).text
        doc = lxml.html.fromstring(data)

        title_div_txt = doc.xpath('//td[@style="text-align: center; white-space: nowrap; width: 60%; font-weight: bold; font-size: x-large;"]/text()')[0]
        if 'Joint Resolution' in title_div_txt:
            bill_type = 'joint resolution'
            bill_id = bill_id[0] + 'JR ' + bill_id[1:]
        elif 'Resolution' in title_div_txt:
            bill_type = 'resolution'
            bill_id = bill_id[0] + 'R ' + bill_id[1:]
        elif 'Bill' in title_div_txt:
            bill_type = 'bill'
            bill_id = bill_id[0] + 'B ' + bill_id[1:]

        title_style_xpath = '//div[@style="text-align: center; font: bold 20px Arial; margin-top: 15px; margin-bottom: 8px;"]/text()'
        bill_title = doc.xpath('//div[@id="title"]')[0].text_content()

        bill = Bill(session, chamber, bill_id, bill_title, type=bill_type)
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
            bill.add_version(version_name, version_url,
                             mimetype='text/html', on_duplicate='use_new')

        # sponsors
        spon_td = doc.xpath('//th[text()="Sponsors:"]/following-sibling::td')[0]
        for leg in spon_td.xpath('a'):
            type = 'primary' if 'Primary' in leg.tail else 'cosponsor'
            name = leg.text_content().replace(u'\xa0', ' ')
            bill.add_sponsor('primary', name, chamber=chamber)

        # actions
        action_tr_xpath = '//td[starts-with(text(),"History")]/../../tr'
        # skip two header rows
        for row in doc.xpath(action_tr_xpath)[2:]:
            tds = row.xpath('td')
            act_date = tds[0].text
            actor = tds[1].text or ''
            # if text is blank, try diving in
            action = tds[2].text.strip() or tds[2].text_content().strip()

            act_date = dt.datetime.strptime(act_date, '%m/%d/%Y')

            if actor == 'Senate':
                actor = 'upper'
            elif actor == 'House':
                actor = 'lower'
            else:
                actor = 'executive'

            for pattern, atype in self._action_classifiers.iteritems():
                if action.startswith(pattern):
                    break
            else:
                atype = 'other'

            bill.add_action(actor, action, act_date, type=atype)

        if hasattr(self, 'subject_map'):
            subj_key = bill_id[0] + ' ' + bill_id.split(' ')[-1]
            bill['subjects'] = self.subject_map[subj_key]

        self.save_bill(bill)

    def scrape(self, session, chambers):
        if self.is_latest_session(session):
            self.build_subject_map()
        for chamber in chambers:
            self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        url = 'http://www.ncga.state.nc.us/gascripts/SimpleBillInquiry/'\
            'displaybills.pl?Session=%s&tab=Chamber&Chamber=%s' % (
            session, chamber)

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        for row in doc.xpath('//table[@cellpadding=3]/tr')[1:]:
            bill_id = row.xpath('td[1]/a/text()')[0]
            self.scrape_bill(chamber, session, bill_id)
