import re
import datetime as dt
import urllib2

import lxml.html

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill

from utils import (clean_text, house_get_actor_from_action,
                   senate_get_actor_from_action)

class MOBillScraper(BillScraper):

    state = 'mo'
    senate_base_url = 'http://www.house.mo.gov'


    def scrape(self, chamber, year):
        # wrapper to call senate or house scraper. No year check
        # here, since house and senate have different backdates
        if chamber == 'upper':
            self.scrape_senate(year)
        elif chamber == 'lower':
            self.scrape_house(year)

    def scrape_senate(self, year):
        # We only have data from 2005-present
        if int(year) < 2005 or int(year) > dt.date.today().year:
            raise NoDataForPeriod(year)

        year2 = "%02d" % (int(year) % 100)

        # year is mixed in to the directory. set a root_url, since
        # we'll use it later
        bill_root = 'http://www.senate.mo.gov/%sinfo/BTS_Web/' % year2
        index_url = bill_root + 'BillList.aspx?SessionType=R'
        #print "index = %s" % index_url

        with self.urlopen(index_url) as index_page:
            index_page = lxml.html.fromstring(index_page)
            # each bill is in it's own table (nested in a larger table)
            bill_tables = index_page.xpath('//a[@id]')

            if not bill_tables:
                return

            for bill_table in bill_tables:
                # here we just search the whole table string to get
                # the BillID that the MO senate site uses
                if re.search(r'dgBillList.*hlBillNum',bill_table.attrib['id']):
                    #print "keys = %s" % bill_table.attrib['id']
                    #print "table = %s " % bill_table.attrib.get('href')
                    self.parse_senate_billpage(bill_root + bill_table.attrib.get('href'), year)
                    #print "one down!"

    def parse_senate_billpage(self, bill_url, year):
        with self.urlopen(bill_url) as bill_page:
            bill_page = lxml.html.fromstring(bill_page)
            # get all the info needed to record the bill
            # TODO probably still needs to be fixed
            bill_id = bill_page.xpath('//*[@id="lblBillNum"]')[0].text_content()
            bill_title = bill_page.xpath('//*[@id="lblBillTitle"]')[0].text_content()
            bill_desc = bill_page.xpath('//*[@id="lblBriefDesc"]')[0].text_content()
            bill_lr = bill_page.xpath('//*[@id="lblLRNum"]')[0].text_content()
            #print "bill id = "+ bill_id

            bill = Bill(year, 'upper', bill_id, bill_desc, bill_url=bill_url,
                        bill_lr=bill_lr, official_title=bill_title)
            bill.add_source(bill_url)

            # Get the primary sponsor
            sponsor = bill_page.xpath('//*[@id="hlSponsor"]')[0]
            bill_sponsor = sponsor.text_content()
            bill_sponsor_link = sponsor.attrib.get('href')
            bill.add_sponsor('primary', bill_sponsor, sponsor_link=bill_sponsor_link)

            # cosponsors show up on their own page, if they exist
            cosponsor_tag = bill_page.xpath('//*[@id="hlCoSponsors"]')
            if len(cosponsor_tag) > 0 and cosponsor_tag[0].attrib.has_key('href'):
                self.parse_senate_cosponsors(bill, cosponsor_tag[0].attrib['href'])

            # get the actions
            action_url = bill_page.xpath('//*[@id="hlAllActions"]')
            if len(action_url) > 0:
                action_url =  action_url[0].attrib['href']
                #print "actions = %s" % action_url
                self.parse_senate_actions(bill, action_url)

            # stored on a separate page
            versions_url = bill_page.xpath('//*[@id="hlFullBillText"]')
            if len(versions_url) > 0 and versions_url[0].attrib.has_key('href'):
                self.parse_senate_bill_versions(bill, versions_url[0].attrib['href'])

        self.save_bill(bill)

    def parse_senate_bill_versions(self, bill, url):
        bill.add_source(url)
        with self.urlopen(url) as versions_page:
            versions_page = lxml.html.fromstring(versions_page)
            version_tags = versions_page.xpath('//li/font/a')
            for version_tag in version_tags:
                description = version_tag.text_content()
                pdf_url = version_tag.attrib['href']
                bill.add_version(description, pdf_url)

    def parse_senate_actions(self, bill, url):
        bill.add_source(url)
        with self.urlopen(url) as actions_page:
            actions_page = lxml.html.fromstring(actions_page)
            bigtable = actions_page.xpath('/html/body/font/form/table/tr[3]/td/div/table/tr')

            for row in bigtable:
                date = row[0].text_content()
                date = dt.datetime.strptime(date, '%m/%d/%Y')
                action = row[1].text_content()
                actor = senate_get_actor_from_action(action)
                # TODO add the type of action (see MA for an example)
                bill.add_action(actor, action, date)

    def parse_senate_cosponsors(self, bill, url):
        bill.add_source(url)
        with self.urlopen(url) as cosponsors_page:
            cosponsors_page = lxml.html.fromstring(cosponsors_page)
            # cosponsors are all in a table
            cosponsors = cosponsors_page.xpath('//table[@id="dgCoSponsors"]/tr/td/a')
            #print "looking for cosponsors = %s" % cosponsors

            for cosponsor_row in cosponsors:
                # cosponsors include district, so parse that out
                cosponsor_string = cosponsor_row.text_content()
                cosponsor = clean_text(cosponsor_string)
                cosponsor = cosponsor.split(',')[0]

                # they give us a link to the congressperson, so we might
                # as well keep it.
                cosponsor_url = cosponsor_row.attrib['href']

                bill.add_sponsor('cosponsor', cosponsor, sponsor_link=cosponsor_url)

    def scrape_house(self, year):
        if int(year) < 2000 or int(year) > dt.date.today().year:
            raise NoDataForPeriod(year)

        bill_page_url = ('%s/BillList.aspx?year=%s' % (self.senate_base_url,year))
        self.parse_house_billpage(bill_page_url, year)

    def parse_house_billpage(self, url, year):
        url_root = re.match("(.*//.*?/)", url).group(1)

        with self.urlopen(url) as bill_list_page:
            bill_list_page = lxml.html.fromstring(bill_list_page)
            # find the first center tag, take the text after
            # 'House of Representatives' and before 'Bills' as
            # the session name
            header_tag = bill_list_page.xpath('//*[@id="ContentPlaceHolder1_lblAssemblyInfo"]')[0].text_content()
            if header_tag.find('1st Extraordinary Session') != -1:
                session = year + ' 1st Extraordinary Session'
            elif header_tag.find('2nd Extraordinary Session') != -1:
                session = year + ' 2nd Extraordinary Session'
            else:
                session = year

            bills = bill_list_page.xpath('//table[@id="billAssignGroup"]/tr')

            isEven = False
            for bill in bills:
                if not isEven: 
                    # the non even rows contain bill links, the other rows contain brief
                    # descriptions of the bill.
                    #print "bill = %s" % bill[0][0].attrib['href']
                    self.parse_house_bill(bill[0][0].attrib['href'], session)
                isEven = not isEven


    def parse_house_bill(self, url, session):
        # using the print page makes the page simpler, and also *drastically* smaller (8k rather than 100k)
        url = re.sub("billsummary", "billsummaryprn", url)
        url = '%s/%s' % (self.senate_base_url,url)

        with self.urlopen(url) as bill_page:
            bill_page = lxml.html.fromstring(bill_page)

            # get all the info needed to record the bill
            bill_id = bill_page.xpath('//*[@class="entry-title"]')[0].text_content()
            bill_id = clean_text(bill_id)

            bill_desc = bill_page.xpath('//*[@class="BillDescription"]')[0].text_content()
            bill_desc = clean_text(bill_desc)

            table_rows = bill_page.xpath('//table/tr')
            # if there is a cosponsor all the rows are pushed down one for the extra row for the cosponsor:
            cosponsorOffset = 0
            if table_rows[2][0].text_content().strip() == 'Co-Sponsor:':
                cosponsorOffset = 1
                
            lr_label_tag = table_rows[3+cosponsorOffset]
            assert lr_label_tag[0].text_content().strip() == 'LR Number:'
            bill_lr = lr_label_tag[1].text_content()

            official_title_tag = table_rows[6+cosponsorOffset]
            assert official_title_tag[0].text_content().strip() == 'Bill String:'
            official_title = official_title_tag[1].text_content()

            # could substitute the description for the name,
            # but keeping it separate for now.
            bill = Bill(session, 'lower', bill_id, bill_desc, bill_url=url, bill_lr=bill_lr, official_title=official_title)
            bill.add_source(url)

            # get the sponsors and cosponsors
            # badly formed html: the first row has now <tr> tag:
            sponsor_dirty = table_rows[0][1].text_content().strip()
            m = re.search("(.*)\(.*\)", sponsor_dirty)
            if m:
                bill_sponsor = m.group(1).strip()
            else:
                bill_sponsor = sponsor_dirty.strip()

            bill_sponsor_link = table_rows[0][1][0].attrib['href']
            if bill_sponsor_link:
                bill_sponsor_link = '%s%s' % (self.senate_base_url,bill_sponsor_link)

            bill.add_sponsor('primary', bill_sponsor, sponsor_link=bill_sponsor_link)

            # check for cosponsors
            if cosponsorOffset == 1:
                if len(table_rows[2][1]) == 1: # just a name
                    cosponsor_cell = table_rows[2][1][0]
                    bill.add_sponsor('cosponsor', cosponsor.text_content(), sponsor_link='%s/%s' % (self.senate_base_url,cosponsor.attrib['href']))
                else: # name ... etal
                    self.parse_cosponsors_from_bill(bill,'%s/%s' % (self.senate_base_url,table_rows[2][1][1].attrib['href']))

            actions_link_tag = bill_page.xpath('//div[@class="Sections"]/a')[0]
            actions_link = '%s/%s' % (self.senate_base_url,actions_link_tag.attrib['href'])
            actions_link = re.sub("content", "print", actions_link)
            self.parse_house_actions(bill, actions_link)

            # get bill versions
            version_tags = bill_page.xpath('//div[@class="BillDocsSection"][2]/span')
            for version_tag in reversed(version_tags):
                version = clean_text(version_tag.text_content())
                text_url = '%s/%s' % (self.senate_base_url,version_tag[0].attrib['href'])
                pdf_url = '%s/%s' % (self.senate_base_url,version_tag[1].attrib['href'])
                bill.add_version(version, text_url, pdf_url=pdf_url)

        self.save_bill(bill)

    def parse_cosponsors_from_bill(self, bill, url):
        with self.urlopen(url) as bill_page:
            bill_page = lxml.html.fromstring(bill_page)
            sponsors_text = bill_page.xpath('/html/body/p[6]/span')[0].text_content()
            sponsors = clean_text(sponsors_text).split(',')
            for part in sponsors[1::]:
                for sponsor in part.split(' AND '):
                    bill.add_sponsor('cosponsor', clean_text(sponsor))

    def parse_house_actions(self, bill, url):
        url = re.sub("BillActions", "BillActionsPrn", url)
        bill.add_source(url)
        with self.urlopen(url) as actions_page:
            actions_page = lxml.html.fromstring(actions_page)
            rows = actions_page.xpath('//table/tr')

            for row in rows[1:]:
                # new actions are represented by having dates in the first td
                # otherwise, it's a continuation of the description from the
                # previous action
                if len(row) > 0 and row[0].tag == 'td':
                    if len(row[0].text_content().strip()) > 0:
                        date = row[0].text_content().strip()
                        date = dt.datetime.strptime(date, '%m/%d/%Y')
                        action = row[2].text_content().strip()
                    else:
                        action += ('\n' + row[2].text_content())
                        action = action.rstrip()
                    actor = house_get_actor_from_action(action)
                    #TODO probably need to add the type here as well
                    bill.add_action(actor, action, date)

        # add that last action
        actor = house_get_actor_from_action(action)
        #TODO probably need to add the type here as well
        bill.add_action(actor, action, date)
