import datetime
import re

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import lxml.html

BASE_URL = 'http://www.legislature.mi.gov'

def jres_id(n):
    """ joint res ids go from A-Z, AA-ZZ, etc. """
    return chr(ord('A')+(n-1)%25)*((n/26)+1)

bill_types = {'B':'bill',
              'R':'resolution',
              'CR':'concurrent resolution',
              'JR':'joint resolution'}

class MIBillScraper(BillScraper):
    state = 'mi'

    def scrape_bill(self, chamber, session, bill_id):
        # try and get bill for current year
        url = 'http://legislature.mi.gov/doc.aspx?%s-%s' % (
            session[:4], bill_id.replace(' ', '-'))
        html = self.urlopen(url)
        # if first page isn't found, try second year
        if 'Page Not Found' in html:
            html = self.urlopen('http://legislature.mi.gov/doc.aspx?%s-%s'
                                % (session[-4:], bill_id.replace(' ','-')))
            if 'Page Not Found' in html:
                return None

        doc = lxml.html.fromstring(html)

        title = doc.xpath('//span[@id="frg_billstatus_ObjectSubject"]')[0].text_content()

        # get B/R/JR/CR part and look up bill type
        bill_type = bill_types[bill_id.split(' ')[0][1:]]

        bill = Bill(session=session, chamber=chamber, bill_id=bill_id,
                    title=title, type=bill_type)
        bill.add_source(url)

        # sponsors
        sp_type = 'primary'
        for sponsor in doc.xpath('//span[@id="frg_billstatus_SponsorList"]/a/text()'):
            bill.add_sponsor(sp_type, sponsor)
            sp_type = 'cosponsor'

        bill['subjects'] = doc.xpath('//span[@id="frg_billstatus_CategoryList"]/a/text()')

        # actions (skip header)
        for row in doc.xpath('//table[@id="frg_billstatus_HistoriesGridView"]/tr')[1:]:
            tds = row.xpath('td')  # date, journal link, action
            date = tds[0].text_content()
            journal = tds[1].text_content()
            action = tds[2].text_content()
            date = datetime.datetime.strptime(date, "%m/%d/%Y")
            # instead of trusting upper/lower case, use journal for actor
            actor = 'upper' if 'SJ' in journal else 'lower'
            bill.add_action(actor, action, date)

            # check if action mentions a vote
            rcmatch = re.search('Roll Call # (\d+)', action, re.IGNORECASE)
            if rcmatch:
                rc_num = rcmatch.groups()[0]
                # in format mileg.aspx?page=getobject&objectname=2011-SJ-02-10-011
                journal_link = tds[1].xpath('a/@href')
                if journal_link:
                    objectname = journal_link[0].rsplit('=', 1)[-1]
                    chamber_name = {'upper': 'Senate', 'lower': 'House'}[actor]
                    vote_url = BASE_URL + '/documents/%s/Journal/%s/htm/%s.htm' % (
                        session, chamber_name, objectname)
                    vote = Vote(actor, date, action, False, 0, 0, 0)
                    self.parse_roll_call(vote, vote_url, rc_num)
                    # TODO: use the counts, base passed on real data
                    vote['yes_count'] = len(vote['yes_votes'])
                    vote['no_count'] = len(vote['no_votes'])
                    vote['other_count'] = len(vote['other_votes'])
                    vote['passed'] = vote['yes_count'] > vote['no_count']
                    vote.add_source(vote_url)
                    bill.add_vote(vote)
                else:
                    self.warning("missing journal link for %s %s" % 
                                 (bill_id, journal))

        # versions
        for row in doc.xpath('//table[@id="frg_billstatus_DocumentGridTable"]/tr'):
            version = self.parse_doc_row(row)
            if version:
                bill.add_version(*version)

        # documents
        for row in doc.xpath('//table[@id="frg_billstatus_HlaTable"]/tr'):
            document = self.parse_doc_row(row)
            if document:
                bill.add_document(*document)
        for row in doc.xpath('//table[@id="frg_billstatus_SfaTable"]/tr'):
            document = self.parse_doc_row(row)
            if document:
                bill.add_document(*document)

        self.save_bill(bill)
        return True

    def scrape(self, chamber, session):
        bill_types = {
            'upper': [('SB', 1), ('SR', 1), ('SCR', 1), ('SJR', 1)],
            'lower': [('HB', 4001), ('HR', 1), ('HCR', 1, ('HJR', 1))]
            #JRs are A..Z,AA..ZZ,AAA..ZZZ
        }

        for abbr, start_num in bill_types[chamber]:
            n = start_num
            # keep trying bills until scrape_bill returns None
            while True:
                if 'JR' in abbr:
                    bill_id = '%s %s' % (abbr, jres_id(n))
                else:
                    bill_id = '%s %04d' % (abbr, n)
                if not self.scrape_bill(chamber, session, bill_id):
                    break
                n += 1

    def parse_doc_row(self, row):
        # first anchor in the row is HTML if present, otherwise PDF
        a = row.xpath('.//a')
        if a:
            name = row.xpath('.//b/text()')[0]
            url = BASE_URL + a[0].get('href').replace('../', '')
            return name, url

    def parse_roll_call(self, vote, url, rc_num):
        with self.urlopen(url) as html:
            vote_doc = lxml.html.fromstring(html)

            # split the file into lines using the <p> tags
            pieces = [p.text_content() for p in vote_doc.xpath('//p')]

            # go until we find the roll call
            for i, p in enumerate(pieces):
                if p.startswith(u'Roll Call No.\xa0%s' % rc_num):
                    break

            # once we find the roll call, go through voters
            for p in pieces[i:]:
                # mdash: \xe2\x80\x94 splits Yeas/Nays/Excused/NotVoting
                if 'Yeas' in p:
                    vtype = vote.yes
                elif 'Nays' in p:
                    vtype = vote.no
                elif 'Excused' in p or 'Not Voting' in p:
                    vtype = vote.other
                elif p.startswith('In The Chair:'):
                    break
                else:
                    for l in p.split():
                        vtype(l)
