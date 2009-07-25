#!/usr/bin/env python
from __future__ import with_statement
import re
import datetime as dt
import html5lib
from utils import *

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import *

class MOLegislationScraper(LegislationScraper):

    state = 'mo'

    metadata = {
        'state_name': 'Missouri',
        'legislature_name': 'Missouri General Assembly',
        'lower_chamber_name': 'House of Representatives',
        'upper_chamber_name': 'Senate',
        'lower_title': 'Representative',
        'upper_title': 'Senator',
        'lower_term': 2,
        'upper_term': 4,
        'sessions': ['1998', '1999', '2000', '2001', '2002', '2003',
                     '2004', '2005', '2006', '2007', '2008', '2009',],
        'session_details': {
            '1998': {'years': [1998], 'sub_sessions': []},
            '1999': {'years': [1999], 'sub_sessions': []},
            '2000': {'years': [2000], 'sub_sessions': []},
            '2001': {'years': [2001],
                     'sub_sessions': ['2001 Extraordinary Session']},
            '2002': {'years': [2002], 'sub_sessions': []},
            '2003': {'years': [2003],
                     'sub_sessions': ['2003 1st Extraordinary Session',
                                      '2003 2nd Extraordinary Session']},
            '2004': {'years': [2004], 'sub_sessions': []},
            '2005': {'years': [2005],
                     'sub_sessions': ['2005 Extraordinary Session']},
            '2006': {'years': [2006], 'sub_sessions': []},
            '2007': {'years': [2007],
                     'sub_sessions': ['2007 Extraordinary Session']},
            '2008': {'years': [2008], 'sub_sessions': []},
            '2009': {'years': [2009], 'sub_sessions': []},
        }}

    house_root = 'http://www.house.mo.gov'
    senate_root = 'http://www.senate.mo.gov'

    def scrape_bills(self,chamber,year):
        # wrapper to call senate or house scraper.  No year check
        # here, since house and senate have different backdates
        if chamber == 'upper':
            self.scrape_senate(year)
        elif chamber == 'lower':
            self.scrape_house(year)

    def scrape_senate(self,year):
        # We only have data from 2005-2009
        if int(year) < 2005 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)
    
        year2 = "%02d" % (int(year) % 100)
    
        # year is mixed in to the directory.  set a root_url, since
        # we'll use it later
        bill_root = self.senate_root + '/' + year2 + 'info/BTS_Web/'
        index_url = bill_root + 'BillList.aspx?SessionType=R'
    
        with self.soup_context(index_url) as index_page:
            # each bill is in it's own table (nested in a larger table)
            bill_tables = index_page.findAll(id="Table2")

            if not bill_tables:
                return
    
            for bill_table in bill_tables:
                # here we just search the whole table string to get 
                # the BillID that the MO senate site uses
                m = re.search(r"BillID=(\d*)", str(bill_table))
                if m:
                    bill_web_id = m.group(1)
                    bill_url= bill_root + '/Bill.aspx?SessionType=R&BillID=' + bill_web_id
                    self.parse_senate_billpage(bill_url, year)

    def parse_senate_billpage(self, bill_url, year):
        with self.soup_context(bill_url) as bill_page:
            # get all the info needed to record the bill
            bill_id   = bill_page.find(id="lblBillNum").b.font.contents[0]
            bill_title = bill_page.find(id="lblBillTitle").font.string
            bill_desc = bill_page.find(id="lblBriefDesc").font.contents[0]
            bill_lr   = bill_page.find(id="lblLRNum").font.string

            bill = Bill(year, 'upper', bill_id, bill_desc, bill_url=bill_url,
                        bill_lr=bill_lr, official_title=bill_title)

            # Get the primary sponsor
            bill_sponsor = bill_page.find(id="hlSponsor").i.font.contents[0]
            bill_sponsor_link = bill_page.find(id="hlSponsor").href
            bill.add_sponsor('primary', bill_sponsor,
                             sponsor_link=bill_sponsor_link)

            # cosponsors show up on their own page, if they exist
            cosponsor_tag = bill_page.find(id="hlCoSponsors")
            if cosponsor_tag and cosponsor_tag.has_key('href'):
                self.parse_senate_cosponsors(bill, cosponsor_tag['href'])

            # get the actions
            action_url = bill_page.find(id="hlAllActions")['href']
            self.parse_senate_actions(bill, action_url)

            # stored on a separate page
            versions_url = bill_page.find(id="hlFullBillText")
            if versions_url:
                self.parse_senate_bill_versions(bill, versions_url['href'])

        self.add_bill(bill)

    def parse_senate_bill_versions(self, bill, url):
        with self.soup_context(url) as versions_page:
            version_tags = versions_page.findAll('li')
            if version_tags != None:
                for version_tag in version_tags:
                    pdf_url = version_tag.font.a['href']
                    version = version_tag.font.a.string
                    bill.add_version(version, pdf_url)

    def parse_senate_actions(self, bill, url):
        with self.soup_context(url) as actions_page:
            bigtable = actions_page.find(id='Table5')
            act_row = bigtable.next.next.nextSibling.next.nextSibling.nextSibling
            act_table = act_row.td.div.table

            for row in act_table.findAll('tr'):
                date = row.td.contents[0]
                date = dt.datetime.strptime(date, '%m/%d/%Y')
                action = row.td.nextSibling.nextSibling.contents[0]
                act_chamber = senate_get_chamber_from_action(action)
                bill.add_action(act_chamber, action, date)

    def parse_senate_cosponsors(self, bill, url):
        with self.soup_context(url) as cosponsors_page:
            # cosponsors are all in a table
            cosponsor_table = cosponsors_page.find(id="dgCoSponsors")
            cosponsors = cosponsor_table.findAll("tr")

            for cosponsor_row in cosponsors:
                # cosponsors include district, so parse that out
                cosponsor_string = cosponsor_row.font.contents[0]
                cosponsor = clean_text(cosponsor_string)

                # they give us a link to the congressperson, so we might
                # as well keep it.
                cosponsor_url = cosponsor_row.a.href
                
                bill.add_sponsor('cosponsor', cosponsor,
                                 sponsor_link=cosponsor_url)

    def scrape_house(self, year):
        #we only have data from 1998-2009
        assert int(year) >= 1998, "no lower chamber data from before 1998"
        assert int(year) <= 2009, "no future data"

        sessions = {
            1998: ['bills98'],
            1999: ['bills99'],
            2000: ['bills00'],
            2001: ['bills01','spec01'],
            2002: ['bills02'],
            2003: ['bills03','bills033','bills034'],
            2004: ['bills041'],
            2005: ['bills051','bills053'],
            2006: ['bills061'],
            2007: ['bills071','bills073'],
            2008: ['bills081'],
            2009: ['bills091']
        }
    
        for session_code in sessions[int(year)]:
            bill_page_url = self.house_root + '/billtracking/' + session_code + '/billist.htm'
            self.parse_house_billpage(bill_page_url, year)

    def parse_house_billpage(self, url, year):
        url_root = re.match("(.*//.*?/)",url).group(1)

        with self.soup_context(url) as bill_list_page:
            # find the first center tag, take the text after 'House of Representatives'
            # and before 'Bills' as the session name
            header_tag = str(bill_list_page.find('center'))
            if header_tag.find('1st Extraordinary Session') != -1:
                session = year + ' 1st Extraordinary Session'
            elif header_tag.find('2nd Extraordinary Session') != -1:
                session = year + ' 2nd Extraordinary Session'
            else:
                session = year

            bills = bill_list_page.findAll('b')

            for bill in bills:
                bill_link = bill.find(href = re.compile("bills", re.I))
                if bill_link:
                    bill_url = bill_link['href']
                    self.parse_house_bill(bill_url, session)

    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def parse_house_bill(self, url, session):
        url = re.sub("content", "print", url)

        with self.urlopen_context(url) as bill_page_data:
            bill_page = self.soup_parser(bill_page_data)
            header_table = bill_page.table

            # get all the info needed to record the bill
            bill_id = header_table.b.contents[0]
            bill_id = clean_text(bill_id)

            bill_desc = header_table.findAll('td')[1].contents[0]
            bill_desc = clean_text(bill_desc)

            lr_label_tag = bill_page.find(text = re.compile("LR Number:"))
            bill_lr = lr_label_tag.next.contents[0].strip()

            # could substitute the description for the name, but keeping it separate for now.
            bill = Bill(session, 'lower', bill_id, bill_desc,
                        bill_url=url, bill_lr=bill_lr)

            # get the sponsors and cosponsors
            sponsor_dirty = bill_page.em.contents[0]
            m = re.search("(.*)\(.*\)",sponsor_dirty)
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
            cosponsor_cell = bill_details_tbl.find(text = re.compile("CoSponsor")).next
            if cosponsor_cell.a:
                self.parse_house_cosponsors(bill, cosponsor_cell)

            # parse out all the actions
            actions_link_tag = bill_page.find('a',text='ACTIONS').previous.previous

            actions_link = actions_link_tag['href']
            actions_link = re.sub("content","print",actions_link)
            self.parse_house_actions(bill, actions_link)

            # get bill versions
            version_tags = bill_page.findAll(href=re.compile("biltxt"))
            if version_tags:
                for version_tag in version_tags:
                    if version_tag.b:
                        version = clean_text(version_tag.b.contents[0])
                        text_url = version_tag['href']
                        pdf_url = version_tag.previousSibling.previousSibling['href']
                        bill.add_version(version, text_url, pdf_url=pdf_url)

        self.add_bill(bill)

    def parse_house_actions(self, bill, url):
        with self.soup_context(url) as actions_page:
            rows = actions_page.findAll('tr')

            # start with index 0 because the table doesn't have an opening <tr>
            first_row = rows[0]
            date = first_row.td.contents[0].strip()
            date = dt.datetime.strptime(date, '%m/%d/%Y')
            action = first_row.td.nextSibling.nextSibling.contents[0]
        
            for row in rows[1:]:
                # new actions are represented by having dates in the first td
                # otherwise, it's a continuation of the description from the 
                # previous action
                if row.td != None:
                    if not row.td.contents[0] and row.td.contents[0] != ' ':
                        act_chamber = house_get_chamber_from_action(action)
                        bill.add_action(act_chamber, action, date)
                        date = row.td.contents[0]
                        date = dt.datetime.strptime(date, '%m/%d/%Y')
                        action = row.td.nextSibling.nextSibling.contents[0]
                    else:
                        action += ' ' + row.td.nextSibling.nextSibling.contents[0]

        # add that last action
        act_chamber = house_get_chamber_from_action(action)
        bill.add_action(act_chamber, action, date)

    def parse_house_cosponsors(self, bill, cell):
        # if there's only one sponsor, we don't have to worry about this.
        if (not cell.a.nextSibling or
            not cell.a.nextSibling.nextSibling or
            not cell.a.nextSibling.nextSibling.has_key('href')):

            cosponsor_dirty = cell.a.em.contents[0]
            cosponsor = clean_text(cosponsor_dirty)
            bill.add_sponsor('cosponsor', cosponsor,
                             sponsor_link=cell.a['href'])
        else:
            # there are several sponsors, and we have to go to the bill text
            bill_text_url = cell.a.nextSibling.nextSibling['href']

            #don't need to parse bill in to soup
            with self.urlopen_context(bill_text_url) as doc:
                # people between (Sponsor) and (Co-Sponsor) are the cosponsors
                m = re.search(r"\(Sponsor\),?(.*)\(Co", doc, re.DOTALL)
                if m:
                    cosponsor_list = clean_text(m.group(1))
                    cosponsor_list = re.split(" ?(?:,| AND ) ?", cosponsor_list)

                    for cosponsor_dirty in cosponsor_list:
                        cosponsor = clean_text(cosponsor_dirty)
                        bill.add_sponsor('cosponsor', cosponsor)

if __name__ == '__main__':
    MOLegislationScraper().run()
