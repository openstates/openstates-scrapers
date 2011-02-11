import datetime as dt
import re
from collections import defaultdict

import lxml.html

from billy.scrape.bills import BillScraper, Bill

class NCBillScraper(BillScraper):

    state = 'nc'

    _action_classifiers = {
        'Vetoed': 'governor:vetoed',
        'Signed By Gov': 'governor:signed',
        'Withdrawn from ': 'bill:withdrawn',
        'Ref ': 'committee:referred',
        'Re-ref ': 'committee:referred',
        'Reptd Fav': 'committee:passed:favorable',
        'Reptd Unfav': 'committee:passed:unfavorable',
        'Pres. To Gov': 'other',
        'Passed 3rd Reading': 'bill:passed',
        'Passed 2nd & 3rd Reading': 'bill:passed',
        'Failed 3rd Reading': 'bill:failed',
        'Filed': 'bill:introduced',
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
            with self.urlopen(url) as html:
                doc = lxml.html.fromstring(html)
                for td in doc.xpath('//td[@class="tableText"]'):
                    if td.get('style') == 'font-weight: bold;':
                        cur_subject = td.text_content()
                    else:
                        bill_link = td.xpath('a/text()')
                        if bill_link:
                            self.subject_map[bill_link[0]].append(cur_subject)

    def get_bill_info(self, session, bill_id):
        bill_detail_url = 'http://www.ncga.state.nc.us/gascripts/'\
            'BillLookUp/BillLookUp.pl?Session=%s&BillID=%s' % (
            session, bill_id)

        if bill_id[0] == 'H':
            chamber = 'lower'
        else:
            chamber = 'upper'

        # parse the bill data page, finding the latest html text
        with self.urlopen(bill_detail_url) as data:
            doc = lxml.html.fromstring(data)

            title_div_txt = doc.xpath('//div[@id="title"]/text()')[0]
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
            bill_title = doc.xpath(title_style_xpath)[0]

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
                bill.add_version(version_name, version_url)

            # sponsors
            pri_td = doc.xpath('//th[text()="Primary:"]/following-sibling::td')
            pri_text = pri_td[0].text_content().replace(u'\xa0', ' ').split('; ')
            for leg in pri_text:
                leg = leg.strip()
                if leg:
                    if leg[-1] == ';':
                        leg = leg[:-1]
                    bill.add_sponsor('primary', leg)

            # cosponsors
            co_td = doc.xpath('//th[text()="Co:"]/following-sibling::td')
            co_text = co_td[0].text_content().replace(u'\xa0', ' ').split('; ')
            for leg in co_text:
                leg = leg.strip()
                if leg and leg != 'N/A':
                    if leg[-1] == ';':
                        leg = leg[:-1]
                    bill.add_sponsor('cosponsor', leg)

            # actions
            action_tr_xpath = '//td[starts-with(text(),"History")]/../../tr'
            # skip two header rows
            for row in doc.xpath(action_tr_xpath)[2:]:
                tds = row.xpath('td')
                act_date = tds[0].text
                actor = tds[1].text or ''
                action = tds[2].text.strip()

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

            if self.is_latest_session(session):
                subj_key = bill_id[0] + ' ' + bill_id.split(' ')[-1]
                bill['subjects'] = self.subject_map[subj_key]

            self.save_bill(bill)

    def scrape(self, chamber, session):
        chamber = {'lower': 'House', 'upper': 'Senate'}[chamber]
        url = 'http://www.ncga.state.nc.us/gascripts/SimpleBillInquiry/'\
            'displaybills.pl?Session=%s&tab=Chamber&Chamber=%s' % (
            session, chamber)

        if self.is_latest_session(session):
            self.build_subject_map()

        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)
            for row in doc.xpath('//table[@cellpadding=3]/tr')[1:]:
                bill_id = row.xpath('td[1]/a/text()')[0]
                self.get_bill_info(session, bill_id)
