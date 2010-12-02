import re
from datetime import datetime

from fiftystates.scrape.nv import metadata
from fiftystates.scrape.nv.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree

class NVBillScraper(BillScraper):
    state = 'nv'

    def scrape(self, chamber, session):
        if session.find('Special') != -1:
            year = session[0:4]
        elif int(session) >= 71:
            year = ((int(session) - 71) * 2) + 2001
        else:
            raise NoDataForPeriod(session)

        sessionsuffix = 'th'
        if str(session)[-1] == '1':
            sessionsuffix = 'st'
        elif str(session)[-1] == '2':
            sessionsuffix = 'nd'
        elif str(session)[-1] == '3':
            sessionsuffix = 'rd'

        if session.find('Special') != -1:
            session = session[-2: len(session)]
            insert = str(session) + sessionsuffix + str(year) + "Special"
        else:
            insert = str(session) + sessionsuffix + str(year)

        if chamber == 'upper':
            self.scrape_senate_bills(chamber, insert, session, year)
        elif chamber == 'lower':
            self.scrape_assem_bills(chamber, insert, session, year)


    def scrape_senate_bills(self, chamber, insert, session, year):
        doc_type = {2: 'bill', 4: 'resolution', 7: 'concurrent resolution',
                    8: 'joint resolution'}

        for docnum, bill_type in doc_type.iteritems():
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/Reports/HistListBills.cfm?DoctypeID=%s' % (insert, docnum)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count = count + 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)

                with self.urlopen(page_path) as page:
                    page = page.decode("utf8").replace(u"\xa0", " ")
                    root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                    bill_id = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[1]/td[1]/font)')
                    title = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[5]/td)')

                    if insert.find('Special') != -1:
                        session = insert
                    bill = Bill(session, chamber, bill_id, title,
                                type=bill_type)

                    bill_text = root.xpath("string(/html/body/div[@id='content']/table[6]/tr/td[2]/a/@href)")
                    text_url = "http://www.leg.state.nv.us" + bill_text
                    bill.add_version("Bill Text", text_url)

                    primary, secondary = self.scrape_sponsors(page)

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


                    minutes_count = 2
                    for mr in root.xpath('//table[4]/tr/td[3]/a'):
                        minutes =  mr.xpath("string(@href)")
                        minutes_url = "http://www.leg.state.nv.us" + minutes
                        minutes_date_path = "string(//table[4]/tr[%s]/td[2])" % minutes_count
                        minutes_date = mr.xpath(minutes_date_path).split()
                        minutes_date = minutes_date[0] + minutes_date[1] + minutes_date[2] + " Minutes"
                        bill.add_document(minutes_date, minutes_url)
                        minutes_count = minutes_count + 1

                    self.scrape_actions(page, bill, "upper")
                    self.scrape_votes(page, bill, "upper", insert, title, year)
                    bill.add_source(page_path)
                    self.save_bill(bill)



    def scrape_assem_bills(self, chamber, insert, session, year):

        doc_type = {1: 'bill', 3: 'resolution', 5: 'concurrent resolution',
                    6: 'joint resolution'}
        for docnum, bill_type in doc_type.iteritems():
            parentpage_url = 'http://www.leg.state.nv.us/Session/%s/Reports/HistListBills.cfm?DoctypeID=%s' % (insert, docnum)
            links = self.scrape_links(parentpage_url)
            count = 0
            for link in links:
                count = count + 1
                page_path = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (insert, link)
                with self.urlopen(page_path) as page:
                    page = page.decode("utf8").replace(u"\xa0", " ")
                    root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                    bill_id = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[1]/td[1]/font)')
                    title = root.xpath('string(/html/body/div[@id="content"]/table[1]/tr[5]/td)')

                    if insert.find('Special') != -1:
                        session = insert
                    bill = Bill(session, chamber, bill_id, title,
                                type=bill_type)
                    bill_text = root.xpath("string(/html/body/div[@id='content']/table[6]/tr/td[2]/a/@href)")
                    text_url = "http://www.leg.state.nv.us" + bill_text
                    bill.add_version("Bill Text", text_url)


                    primary, secondary = self.scrape_sponsors(page)
                    
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

                    minutes_count = 2
                    for mr in root.xpath('//table[4]/tr/td[3]/a'):
                        minutes =  mr.xpath("string(@href)")
                        minutes_url = "http://www.leg.state.nv.us" + minutes
                        minutes_date_path = "string(//table[4]/tr[%s]/td[2])" % minutes_count
                        minutes_date = mr.xpath(minutes_date_path).split()
                        minutes_date = minutes_date[0] + minutes_date[1] + minutes_date[2] + " Minutes"
                        bill.add_document(minutes_date, minutes_url)
                        minutes_count = minutes_count + 1


                    self.scrape_actions(page, bill, "lower")
                    self.scrape_votes(page, bill, "lower", insert, title, year)
                    bill.add_source(page_path)
                    self.save_bill(bill)

    def scrape_links(self, url):
        links = []

        with self.urlopen(url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            path = '/html/body/div[@id="ScrollMe"]/table/tr[1]/td[1]/a'
            for mr in root.xpath(path):
                if '*' not in mr.text:
                    web_end = mr.xpath('string(@href)')
                    links.append(web_end)
        return links


    def scrape_sponsors(self, page):
        primary = []
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

    def scrape_actions(self, page, bill, actor):
        root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
        path = '/html/body/div[@id="content"]/table/tr/td/p[1]'
        count = 6
        for mr in root.xpath(path):
            date = mr.xpath('string()')
            date = date.split()[0] + " " + date.split()[1] + " " + date.split()[2]
            date = datetime.strptime(date, "%b %d, %Y")
            count = count + 1
            action_path = '/html/body/div[@id="content"]/table[%s]/tr/td/ul/li' % (count)
            for el in root.xpath(action_path):
                action = el.xpath('string()')
                bill.add_action(actor, action, date)

    def scrape_votes(self, bill_page, bill, chamber, insert, motion, year):
        root = lxml.etree.fromstring(bill_page, lxml.etree.HTMLParser())
        for href in root.xpath('//a[contains(text(), "Passage")]/@href'):
            vote_url = 'http://www.leg.state.nv.us/Session/%s/Reports/%s' % (
                insert, href)
            bill.add_source(vote_url)
            with self.urlopen(vote_url) as page:
                page = page.decode("utf8").replace(u"\xa0", " ")
                root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())

                date = root.xpath('string(/html/body/center/font)').split()[-1]
                date = date + "-" + str(year)
                date = datetime.strptime(date, "%m-%d-%Y")
                yes_count = root.xpath('string(/html/body/center/table/tr/td[1])').split()[0]
                no_count = root.xpath('string(/html/body/center/table/tr/td[2])').split()[0]
                excused = root.xpath('string(/html/body/center/table/tr/td[3])').split()[0]
                not_voting = root.xpath('string(/html/body/center/table/tr/td[4])').split()[0]
                absent = root.xpath('string(/html/body/center/table/tr/td[5])').split()[0]
                other_count = 0    
                if yes_count > no_count:
                    passed = True
                else:
                    passed = False

                vote = Vote(chamber, date, motion, passed, int(yes_count),
                            int(no_count), other_count,
                            not_voting=int(not_voting), absent=int(absent))

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
