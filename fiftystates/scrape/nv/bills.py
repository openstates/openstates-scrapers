import re
import datetime


from fiftystates.scrape.nv import metadata
from fiftystates.scrape.nv.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree

class NVBillScraper(BillScraper):
    state = 'nv'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year < 2001:
            raise NoDataForYear(year)

        time = datetime.datetime.now()
        curyear = time.year
        if ((int(year) - curyear) % 2) == 1:
            session = ((int(year) -  curyear) / 2) + 76
        elif( ((int(year) - curyear) % 2) == 0) and year >= 2010:
            session = ((int(year) - curyear) / 2) + 26
        else:
            raise NoDataForYear(year)

        sessionsuffix = 'th'
        if str(session)[-1] == '1':
            sessionsuffix = 'st'
        elif str(session)[-1] == '2':
            sessionsuffix = 'nd'
        elif str(session)[-1] == '3':
            sessionsuffix = 'rd'
        insert = str(session) + sessionsuffix + str(year)
        if session == 26:
            insert = str(session) + sessionsuffix + str(year) + "Special"

        if chamber == 'upper':
            self.scrape_senate_bills(chamber, insert, session)
        elif chamber == 'lower':
            self.scrape_assem_bills(chamber, insert, session)


    def scrape_senate_bills(self, chamber, insert, session):

        doc_type = [2, 4, 7, 8]
        for doc in doc_type:
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/Reports/HistListBills.cfm?DoctypeID=%s' % (insert, doc)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count = count + 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)
                with self.urlopen(page_path) as page:
                    root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                    bill_id = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[1]/td[1]/font)')
                    title = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[5]/td)')
                    bill = Bill(session, chamber, bill_id, title)

                    primary, secondary = self.scrape_sponsors(page_path)

                    if primary[0] == 'By:':
                        primary.pop(0)

                        if primary[0] == 'ElectionsProceduresEthicsand':
                            primary[0] = 'Elections Procedures Ethics and'

                        full_name = ''
                        for part_name in primary:
                            full_name = full_name + part_name + " "
                        bill.add_sponsor('primary', full_name)
                    else:
                        for leg in primary:
                            bill.add_sponsor('primary', leg)
                    for leg in secondary:
                        bill.add_sponsor('cosponsor', leg)

                    self.scrape_actions(page_path, bill, "Senate")
                    self.scrape_votes(page_path, bill, "Senate", insert, title)
                    bill.add_source(page_path)
                    self.save_bill(bill)



    def scrape_assem_bills(self, chamber, insert, session):
        
        doc_type = [1, 3, 5, 6]
        for doc in doc_type:
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/Reports/HistListBills.cfm?DoctypeID=%s' % (insert, doc)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count = count + 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)
                with self.urlopen(page_path) as page:
                    root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                    bill_id = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[1]/td[1]/font)')
                    title = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[5]/td)')
                    bill = Bill(session, chamber, bill_id, title)

                    primary, secondary = self.scrape_sponsors(page_path)
                    
                    if primary[0] == 'By:':
                        primary.pop(0)
                        
                        if primary[0] == 'ElectionsProceduresEthicsand':
                            primary[0] = 'Elections Procedures Ethics and'

                        full_name = ''
                        for part_name in primary:
                            full_name = full_name + part_name + " "
                        bill.add_sponsor('primary', full_name)
                    else:
                        for leg in primary:
                            bill.add_sponsor('primary', leg)
                    for leg in secondary:
                        bill.add_sponsor('cosponsor', leg)

                    self.scrape_actions(page_path, bill, "Assembly")
                    self.scrape_votes(page_path, bill, "Assembly", insert, title)
                    bill.add_source(page_path)
                    self.save_bill(bill)

    def scrape_links(self, url):

        links = []

        with self.urlopen(url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            path = '/html/body/div[@id="ScrollMe"]/table/tr[1]/td[1]/a'
            for mr in root.xpath(path):
                web_end = mr.xpath('string(@href)')
                links.append(web_end)
        return links


    def scrape_sponsors(self, url):
        primary = []
        with self.urlopen(url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            path = 'string(/html/body/div[@id="content"]/table[1]/tr[4]/td)'
            sponsors = root.xpath(path)
            sponsors = sponsors.replace(', ', '')
            sponsors = sponsors.split()

            if '(Bolded' in sponsors:
                sponsors.remove('By:')
                sponsors.remove('(Bolded')
                sponsors.remove('name')
                sponsors.remove('indicates')
                sponsors.remove('primary')
                sponsors.remove('sponsorship)')          

            for mr in root.xpath('/html/body/div[@id="content"]/table[1]/tr[4]/td/b[position() > 2]'):
                name = mr.xpath('string()')
                name = name.replace(' ', '')
                primary.append(name)

            for unwanted in primary:
                if unwanted in sponsors:
                    sponsors.remove(unwanted)

            if len(primary) == 0:
                primary = sponsors
                sponsors = []

            return primary, sponsors

    def scrape_actions(self, url, bill, actor):
        with self.urlopen(url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            path = '/html/body/div[@id="content"]/table/tr/td/p[1]'
            count = 6
            for mr in root.xpath(path):
                date = mr.xpath('string()')
                date = date.split()[0] + " " + date.split()[1] + " " + date.split()[2]

                count = count + 1
                action_path = '/html/body/div[@id="content"]/table[%s]/tr/td/ul/li' % (count)
                for el in root.xpath(action_path):
                    action = el.xpath('string()')
                    bill.add_action(actor, action, date)

    def scrape_votes(self, bill_url, bill, chamber, insert, motion):
        with self.urlopen(bill_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            url_path = ('/html/body/div[@id="content"]/table[5]/tr/td/a')
            for mr in root.xpath(url_path):
                url_end = mr.xpath('string(@href)')
                vote_url = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, url_end)
                
                with self.urlopen(vote_url) as page:
                    root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                    date = root.xpath('string(/html/body/center/font)').split()[-1]
                    yes_count = root.xpath('string(/html/body/center/table/tr/td[1])').split()[0]
                    no_count = root.xpath('string(/html/body/center/table/tr/td[2])').split()[0]
                    excused = root.xpath('string(/html/body/center/table/tr/td[3])').split()[0]
                    not_voting = root.xpath('string(/html/body/center/table/tr/td[4])').split()[0]
                    absent = root.xpath('string(/html/body/center/table/tr/td[5])').split()[0]
                    
                    if yes_count > no_count:
                        passed = True
                    else:
                        passed = False

                    vote = Vote(chamber, date, motion, passed, yes_count, no_count, '', not_voting = not_voting, absent = absent)

                    for el in root.xpath('/html/body/table[2]/tr'):
                        name = el.xpath('string(td[1])').strip()
                        full_name = ''
                        for part in name:
                            full_name = full_name + part + " "
                        name = str(name)
                        vote_result = el.xpath('string(td[2])').split()[0]
                        
                        if vote_result == 'Yea':
                            vote.yes(name)
                        elif vote_result == 'Nay':
                            vote.no(name)
                        else:
                            vote.other(name)
                    bill.add_vote(vote)
