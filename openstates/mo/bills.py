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


    def scrape(self, chamber, year):
        # wrapper to call senate or house scraper. No year check
        # here, since house and senate have different backdates
        if chamber == 'upper':
            self.scrape_senate(year)
        elif chamber == 'lower':
            self.scrape_house(year)

    def scrape_senate(self, year):
        # We only have data from 2005-2009
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
                # TODO add the type of action
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
        #we only have data from 1998-2009
        assert int(year) >= 1998, "no lower chamber data from before 1998"
        assert int(year) <= 2009, "no future data"

        sessions = {
            1998: ['bills98'],
            1999: ['bills99'],
            2000: ['bills00'],
            2001: ['bills01', 'spec01'],
            2002: ['bills02'],
            2003: ['bills03', 'bills033', 'bills034'],
            2004: ['bills041'],
            2005: ['bills051', 'bills053'],
            2006: ['bills061'],
            2007: ['bills071', 'bills073'],
            2008: ['bills081'],
            2009: ['bills091']}

        for session_code in sessions[int(year)]:
            bill_page_url = ('http://www.house.mo.gov/billtracking/%s/billist.htm' % session_code)
            self.parse_house_billpage(bill_page_url, year)

    def parse_house_billpage(self, url, year):
        url_root = re.match("(.*//.*?/)", url).group(1)

        with self.urlopen(url) as bill_list_page:
            bill_list_page = BeautifulSoup(bill_list_page)
            # find the first center tag, take the text after
            # 'House of Representatives' and before 'Bills' as
            # the session name
            header_tag = str(bill_list_page.find('center'))
            if header_tag.find('1st Extraordinary Session') != -1:
                session = year + ' 1st Extraordinary Session'
            elif header_tag.find('2nd Extraordinary Session') != -1:
                session = year + ' 2nd Extraordinary Session'
            else:
                session = year

            bills = bill_list_page.findAll('b')

            for bill in bills:
                bill_link = bill.find(href=re.compile("bills", re.I))
                if bill_link:
                    bill_url = bill_link['href']
                    self.parse_house_bill(bill_url, session)


    def parse_house_bill(self, url, session):
        url = re.sub("content", "print", url)

        with self.urlopen(url) as bill_page_data:
            bill_page = BeautifulSoup(bill_page_data)
            header_table = bill_page.table

            # get all the info needed to record the bill
            bill_id = header_table.b.contents[0]
            bill_id = clean_text(bill_id)

            bill_desc = header_table.findAll('td')[1].contents[0]
            bill_desc = clean_text(bill_desc)

            lr_label_tag = bill_page.find(text=re.compile("LR Number:"))
            bill_lr = lr_label_tag.next.contents[0].strip()

            # could substitute the description for the name,
            # but keeping it separate for now.
            bill = Bill(session, 'lower', bill_id, bill_desc,
                        bill_url=url, bill_lr=bill_lr)
            bill.add_source(url)

            # get the sponsors and cosponsors
            sponsor_dirty = bill_page.em.contents[0]
            m = re.search("(.*)\(.*\)", sponsor_dirty)
            if m:
                bill_sponsor = m.group(1)
            else:
                bill_sponsor = sponsor_dirty

            # find the table with bill details...it'll be useful later
            bill_details_tbl = bill_page.table.nextSibling.nextSibling

            bill_sponsor_link = None
            if bill_details_tbl.a:
                bill_sponsor_link = bill_details_tbl.a['href']

            bill.add_sponsor('primary', bill_sponsor,
                             sponsor_link=bill_sponsor_link)

            # check for cosponsors
            cosponsor_cell = bill_details_tbl.find(
                text=re.compile("CoSponsor")).next

            if cosponsor_cell.a:
                self.parse_house_cosponsors(bill, cosponsor_cell)

            # parse out all the actions
            actions_link_tag = bill_page.find(
                'a', text='ACTIONS').previous.previous

            actions_link = actions_link_tag['href']
            actions_link = re.sub("content", "print", actions_link)
            self.parse_house_actions(bill, actions_link)

            # get bill versions
            version_tags = bill_page.findAll(href=re.compile("biltxt"))
            if version_tags:
                for version_tag in version_tags:
                    if version_tag.b:
                        version = clean_text(version_tag.b.contents[0])
                        text_url = version_tag['href']
                        pdf_url = version_tag.previousSibling
                        pdf_url = pdf_url.previousSibling['href']
                        bill.add_version(version, text_url, pdf_url=pdf_url)

        self.save_bill(bill)

    def parse_house_actions(self, bill, url):
        bill.add_source(url)
        with self.urlopen(url) as actions_page:
            actions_page = BeautifulSoup(actions_page)
            rows = actions_page.findAll('tr')

            # start with index 0 because the table doesn't have an opening <tr>
            first_row = rows[0]
            date = first_row.td.contents[0].strip()
            date = dt.datetime.strptime(date, '%m/%d/%Y')
            action = first_row.td.nextSibling.nextSibling.contents[0].strip()

            for row in rows[1:]:
                # new actions are represented by having dates in the first td
                # otherwise, it's a continuation of the description from the
                # previous action
                if row.td != None:
                    if len(row.td.contents) > 0 and row.td.contents[0] != ' ':
                        actor = house_get_actor_from_action(action)
                        #TODO probably need to add the type here as well
                        bill.add_action(actor, action, date)
                        date = row.td.contents[0].strip()
                        date = dt.datetime.strptime(date, '%m/%d/%Y')
                        action = row.td.nextSibling.nextSibling
                        action = action.contents[0].strip()
                    else:
                        action += ('\n' +
                                   row.td.nextSibling.nextSibling.contents[0])
                        action = action.rstrip()

        # add that last action
        actor = house_get_actor_from_action(action)
        #TODO probably need to add the type here as well
        bill.add_action(actor, action, date)

    def parse_house_cosponsors(self, bill, cell):
        # if there's only one sponsor, we don't have to worry about this.
        if (not cell.a.nextSibling or
            not cell.a.nextSibling.nextSibling or
            not 'href' in cell.a.nextSibling.nextSibling):

            cosponsor_dirty = cell.a.em.contents[0]
            cosponsor = clean_text(cosponsor_dirty)
            bill.add_sponsor('cosponsor', cosponsor,
                             sponsor_link=cell.a['href'])
        else:
            # there are several sponsors, and we have to go to the bill text
            bill_text_url = cell.a.nextSibling.nextSibling['href']

            try:
                doc = self.urlopen(bill_text_url)

                # people between (Sponsor) and (Co-Sponsor) are the cosponsors
                m = re.search(r"\(Sponsor\),?(.*)\(Co", doc, re.DOTALL)
                if m:
                    cosponsor_list = clean_text(m.group(1))
                    cosponsor_list = re.split(" ?(?:,| AND ) ?",
                                              cosponsor_list)

                    for cosponsor_dirty in cosponsor_list:
                        cosponsor = clean_text(cosponsor_dirty)
                        bill.add_sponsor('cosponsor', cosponsor)
            except urllib2.HTTPError as e:
                if e.code == 404:
                    # Some of the bill text pages are broken, but the
                    # rest of the bill metadata is valid so just
                    # log the error and move on
                    self.log('404 on %s, continuing' % bill_text_url)
                else:
                    raise e
