import re
import datetime
import requests
from operator import itemgetter
from collections import defaultdict

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from .utils import parse_directory_listing, open_csv

import lxml.html


class SkipBill(Exception):
    pass


class CTBillScraper(BillScraper):
    jurisdiction = 'ct'
    latest_only = True

    def scrape(self, session, chambers):
        self.bills = {}
        self._committee_names = {}
        self._introducers = defaultdict(set)
        self._subjects = defaultdict(list)

        self.scrape_committee_names()
        self.scrape_subjects()
        self.scrape_introducers('upper')
        self.scrape_introducers('lower')
        self.scrape_bill_info(session, chambers)
        for chamber in chambers:
            self.scrape_versions(chamber, session)
        self.scrape_bill_history()

        for bill in self.bills.itervalues():
            self.save_bill(bill)

    def scrape_bill_info(self, session, chambers):
        info_url = "ftp://ftp.cga.ct.gov/pub/data/bill_info.csv"
        data = self.get(info_url)
        page = open_csv(data)

        chamber_map = {'H': 'lower', 'S': 'upper'}

        for row in page:
            bill_id = row['bill_num']
            chamber = chamber_map[bill_id[0]]

            if not chamber in chambers:
                continue

            # assert that the bill data is from this session, CT is tricky
            assert row['sess_year'] == session

            if re.match(r'^(S|H)J', bill_id):
                bill_type = 'joint resolution'
            elif re.match(r'^(S|H)R', bill_id):
                bill_type = 'resolution'
            else:
                bill_type = 'bill'

            bill = Bill(session, chamber, bill_id,
                        row['bill_title'],
                        type=bill_type)
            bill.add_source(info_url)

            for introducer in self._introducers[bill_id]:
                bill.add_sponsor('primary', introducer,
                                 official_type='introducer')

            try:
                self.scrape_bill_page(bill)

                bill['subjects'] = self._subjects[bill_id]

                self.bills[bill_id] = bill
            except SkipBill:
                self.warning('no such bill: ' + bill_id)
                pass

    def scrape_bill_page(self, bill):
        # Removes leading zeroes in the bill number.
        bill_number = ''.join(re.split('0+', bill['bill_id'], 1))
        
        url = ("http://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill"
               "&bill_num=%s&which_year=%s" % (bill_number, bill['session']))

        # Connecticut's SSL is causing problems with Scrapelib, so use Requests
        page = requests.get(url, verify=False).text

        if 'not found in Database' in page:
            raise SkipBill()
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        bill.add_source(url)

        spon_type = 'primary'
        if not bill['sponsors']:
            for sponsor in page.xpath('//h5[text()="Introduced by: "]/../text()'):
                sponsor = sponsor.strip()
                if sponsor:
                    bill.add_sponsor(spon_type, sponsor,
                                     official_type='introducer')
                    spon_type = 'cosponsor'


        for link in page.xpath("//a[contains(@href, '/FN/')]"):
            bill.add_document(link.text.strip(), link.attrib['href'])

        for link in page.xpath("//a[contains(@href, '/BA/')]"):
            bill.add_document(link.text.strip(), link.attrib['href'])

        for link in page.xpath("//a[contains(@href, 'VOTE')]"):
            # 2011 HJ 31 has a blank vote, others might too
            if link.text:
                self.scrape_vote(bill, link.text.strip(),
                                 link.attrib['href'])

    def scrape_vote(self, bill, name, url):
        if "VOTE/H" in url:
            vote_chamber = 'lower'
            cols = (1, 5, 9, 13)
            name_offset = 3
            yes_offset = 0
            no_offset = 1
        else:
            vote_chamber = 'upper'
            cols = (1, 6)
            name_offset = 4
            yes_offset = 1
            no_offset = 2

        # Connecticut's SSL is causing problems with Scrapelib, so use Requests
        page = requests.get(url, verify=False).text

        if 'BUDGET ADDRESS' in page:
            return

        page = lxml.html.fromstring(page)

        yes_count = page.xpath(
            "string(//span[contains(., 'Those voting Yea')])")
        yes_count = int(re.match(r'[^\d]*(\d+)[^\d]*', yes_count).group(1))

        no_count = page.xpath(
            "string(//span[contains(., 'Those voting Nay')])")
        no_count = int(re.match(r'[^\d]*(\d+)[^\d]*', no_count).group(1))

        other_count = page.xpath(
            "string(//span[contains(., 'Those absent')])")
        other_count = int(
            re.match(r'[^\d]*(\d+)[^\d]*', other_count).group(1))

        need_count = page.xpath(
            "string(//span[contains(., 'Necessary for')])")
        need_count = int(
            re.match(r'[^\d]*(\d+)[^\d]*', need_count).group(1))

        date = page.xpath("string(//span[contains(., 'Taken on')])")
        date = re.match(r'.*Taken\s+on\s+(\d+/\s?\d+)', date).group(1)
        date = date.replace(' ', '')
        date = datetime.datetime.strptime(date + " " + bill['session'],
                                          "%m/%d %Y").date()

        vote = Vote(vote_chamber, date, name, yes_count > need_count,
                    yes_count, no_count, other_count)
        vote.add_source(url)

        table = page.xpath("//table")[0]
        for row in table.xpath("tr"):
            for i in cols:
                name = row.xpath("string(td[%d])" % (
                    i + name_offset)).strip()

                if not name or name == 'VACANT':
                    continue

                if "Y" in row.xpath("string(td[%d])" %
                                    (i + yes_offset)):
                    vote.yes(name)
                elif "N" in row.xpath("string(td[%d])" %
                                      (i + no_offset)):
                    vote.no(name)
                else:
                    vote.other(name)

        bill.add_vote(vote)


    def scrape_bill_history(self):
        history_url = "ftp://ftp.cga.ct.gov/pub/data/bill_history.csv"
        page = self.get(history_url)
        page = open_csv(page)

        action_rows = defaultdict(list)

        for row in page:
            bill_id = row['bill_num']

            if bill_id in self.bills:
                action_rows[bill_id].append(row)

        for (bill_id, actions) in action_rows.iteritems():
            bill = self.bills[bill_id]

            actions.sort(key=itemgetter('act_date'))
            act_chamber = bill['chamber']

            for row in actions:
                date = row['act_date']
                date = datetime.datetime.strptime(
                    date, "%Y-%m-%d %H:%M:%S").date()

                action = row['act_desc'].strip()
                act_type = []

                match = re.search('COMM(ITTEE|\.) ON$', action)
                if match:
                    comm_code = row['qual1']
                    comm_name = self._committee_names.get(comm_code,
                                                          comm_code)
                    action = "%s %s" % (action, comm_name)
                    act_type.append('committee:referred')
                elif row['qual1']:
                    if bill['session'] in row['qual1']:
                        action += ' (%s' % row['qual1']
                        if row['qual2']:
                            action += ' %s)' % row['qual2']
                    else:
                        action += ' %s' % row['qual1']

                match = re.search(r'REFERRED TO OLR, OFA (.*)',
                                  action)
                if match:
                    action = ('REFERRED TO Office of Legislative Research'
                              ' AND Office of Fiscal Analysis %s' % (
                                  match.group(1)))

                if (re.match(r'^ADOPTED, (HOUSE|SENATE)', action) or
                    re.match(r'^(HOUSE|SENATE) PASSED', action)):
                    act_type.append('bill:passed')

                match = re.match(r'^Joint ((Un)?[Ff]avorable)', action)
                if match:
                    act_type.append('committee:passed:%s' %
                                    match.group(1).lower())

                if not act_type:
                    act_type = ['other']

                bill.add_action(act_chamber, action, date,
                                type=act_type)

                if 'TRANS.TO HOUSE' in action or action == 'SENATE PASSED':
                    act_chamber = 'lower'

                if ('TRANSMITTED TO SENATE' in action or
                    action == 'HOUSE PASSED'):
                    act_chamber = 'upper'

    def scrape_versions(self, chamber, session):
        chamber_letter = {'upper': 's', 'lower': 'h'}[chamber]
        versions_url = "ftp://ftp.cga.ct.gov/%s/tob/%s/" % (
            session, chamber_letter)

        page = self.get(versions_url).text
        files = parse_directory_listing(page)

        for f in files:
            match = re.match(r'^\d{4,4}([A-Z]+-\d{5,5})-(R\d\d)',
                             f.filename)
            bill_id = match.group(1).replace('-', '')

            try:
                bill = self.bills[bill_id]
            except KeyError:
                continue

            url = versions_url + f.filename
            bill.add_version(match.group(2), url, mimetype='text/html')

    def scrape_subjects(self):
        info_url = "ftp://ftp.cga.ct.gov/pub/data/subject.csv"
        data = self.get(info_url)
        page = open_csv(data)

        for row in page:
            self._subjects[row['bill_num']].append(row['subj_desc'])

    def scrape_committee_names(self):
        comm_url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = self.get(comm_url)
        page = open_csv(page)

        for row in page:
            comm_code = row['comm_code'].strip()
            comm_name = row['comm_name'].strip()
            comm_name = re.sub(r' Committee$', '', comm_name)
            self._committee_names[comm_code] = comm_name

    def scrape_introducers(self, chamber):
        chamber_letter = {'upper': 's', 'lower': 'h'}[chamber]
        url = "https://www.cga.ct.gov/asp/menu/%slist.asp" % chamber_letter

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'MemberBills')]"):
            name = link.xpath("../../td[2]/a/text()")[0].encode('utf-8').strip()
            # we encode the URL here because there are weird characters that
            # cause problems
            url = link.attrib['href'].encode('utf-8')
            self.scrape_introducer(name, url)

    def scrape_introducer(self, name, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        for link in page.xpath("//a[contains(@href, 'billstatus')]"):
            bill_id = link.text.strip()
            self._introducers[bill_id].add(name)
