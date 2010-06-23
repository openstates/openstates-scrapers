import re
import datetime as dt

from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.la import metadata, internal_sessions

from BeautifulSoup import BeautifulSoup


class LABillScraper(BillScraper):
    state = 'la'

    def scrape(self, chamber, year):
        year = int(year)
        abbr = {'upper': 'SB', 'lower': 'HB'}
        for session in internal_sessions[year]:
            s_id = re.findall('\/(\w+)\.htm', session[0])[0]

            # Fake it until we can make it
            bill_number = 1
            failures = 0
            while failures < 5:
                bill_url = 'http://www.legis.state.la.us/billdata/'\
                            'byinst.asp?sessionid=%s&billtype=%s&billno=%d' % (
                             s_id, abbr[chamber], bill_number)
                bill_number = bill_number + 1
                if self.scrape_a_bill(bill_url, chamber, session[1]):
                    failures = 0
                else:
                    failures = failures + 1

    def scrape_a_bill(self, bill, chamber, session_name):
        abbr = {'upper': 'SB', 'lower': 'HB'}
        bill_info = re.findall(
            r'sessionid=(\w+)&billtype=(\w+)&billno=(\d+)', bill)[0]

        with self.urlopen(bill) as bill_summary:
            bill_summary = BeautifulSoup(bill_summary)
            # Check to see if the bill actually exists
            if bill_summary.findAll(
                    text='Specified Bill could not be found.') != []:
                return False
            title = unicode(bill_summary.findAll(
                    text=re.compile('Summary'))[0].parent)
            title = title[(title.find('</b>') + 5):-5]

        bill_id = "%s %s" % (bill_info[1], bill_info[2])
        the_bill = Bill(session_name, chamber, bill_id, title)

        versions = self.scrape_versions(the_bill, bill_info[0],
                                        bill_info[1], bill_info[2])

        history = self.scrape_history(the_bill, bill_info[0],
                                      bill_info[1], bill_info[2])
        # sponsor names are really different than what we pull off
        # of the rosters. thanks louisiana
        sponsors = self.scrape_sponsors(the_bill, bill_info[0],
                                        bill_info[1], bill_info[2])

        documents = self.scrape_docs(the_bill, bill_info[0],
                                     bill_info[1], bill_info[2])

        self.save_bill(the_bill)
        return True

    def scrape_docs(self, bill, session, chamber, bill_no):
        url = 'http://www.legis.state.la.us/billdata/'\
            'byinst.asp?sessionid=%s&billid=%s%s&doctype=AMD' % (
            session, chamber, bill_no)
        bill.add_source(url)

        with self.urlopen(url) as docs:
            docs = BeautifulSoup(docs)
            for doc in docs.findAll('table')[2].findAll('tr'):
                if not doc.td or not doc.td.a.string:
                    continue
                bill.add_document(doc.td.a.string,
                                  "http://www.legis.state.la.us/"\
                                      "billdata/%s" % doc.td.a['href'])

    def scrape_versions(self, bill, session, chamber, bill_no):
        url = 'http://www.legis.state.la.us/billdata/'\
            'byinst.asp?sessionid=%s&billid=%s%s&doctype=BT' % (
            session, chamber, bill_no)
        bill.add_source(url)

        with self.urlopen(url) as versions:
            versions = BeautifulSoup(versions)
            for version in versions.findAll('table')[2].findAll('tr'):
                if version.td is None:
                    continue
                bill.add_version(version.td.a.string,
                                 "http://www.legis.state.la.us/"\
                                     "billdata/%s" % version.td.a['href'])

    def scrape_history(self, bill, session, chamber, bill_no):
        abbr = {'S': 'upper', 'H': 'lower'}
        url = 'http://www.legis.state.la.us/billdata/History.asp'\
            '?sessionid=%s&billid=%s%s' % (session, chamber, bill_no)
        bill.add_source(url)

        with self.urlopen(url) as history:
            history = BeautifulSoup(history)
            for action in history.findAll('table')[2].findAll('tr'):
                (date, house, _, matter) = action.findAll('td')
                if date.b:
                    continue
                act_date = dt.datetime.strptime(date.string, "%m/%d/%Y")
                bill.add_action(abbr[house.string], matter.string, act_date)

    def scrape_sponsors(self, bill, session, chamber, bill_no):
        abbr = {'S': 'upper', 'H': 'lower'}
        url = 'http://www.legis.state.la.us/billdata/Authors.asp'\
            '?sessionid=%s&billid=%s%s' % (session, chamber, bill_no)
        bill.add_source(url)

        with self.urlopen(url) as history:
            history = BeautifulSoup(history)
            for sponsor in history.findAll('table')[2].findAll('tr'):
                name = sponsor.td.string
                t = ''
                if name is None:
                    continue
                elif name.count('(Primary Author)') > 0:
                    t = 'primary'
                    name = name.replace('(Primary Author)', '')
                else:
                    t = 'cosponsor'
                bill.add_sponsor(t, name)

    def flatten(self, tree):
        if tree.string:
            s = tree.string
        else:
            s = map(lambda x: self.flatten(x), tree.contents)
            if len(s) == 1:
                s = s[0]

        return s
