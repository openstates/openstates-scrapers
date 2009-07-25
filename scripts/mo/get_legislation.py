#!/usr/bin/env python

# Notes about this scraper:
# 1. This scripts bills after 2005.

from BeautifulSoup import BeautifulSoup
import re
import urllib,urllib2
import datetime

# ugly hack
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import LegislationScraper, NoDataForYear

# take in a url, return a beautiful soup
def soup_web(url):
    # get the file, parse it with BeautifulSoup
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    doc = response.read()
    soup = BeautifulSoup(doc)#this gives us an index page
    return soup
    
# remove whitespace, linebreaks, and end parentheses
def clean_text(text):
    newtext = re.sub(r"[\r\n]+"," ",text)
    newtext = re.sub(r"\s{2,}"," ",newtext)
    m = re.match(r"(.*)\(.*?\)",newtext)
    if m == None:
        return newtext
    else:
        return m.group(1)

# look in the action to try to parse out the chamber
# that took the action
def house_get_chamber_from_action(text):
    m = re.search(r"\((H|S)\)",text)
    if m == None:
        return None
    abbrev = m.group(1)
    if abbrev == 'S':
        return 'upper'
    return 'lower'

# look in the action to try to parse out the chamber
# that took the action
def senate_get_chamber_from_action(text):
    if re.search("Prefiled",text):
        return 'upper'
    m = re.search(r"^(H|S)",text)
    if m == None:
        m = re.search(r" (H|S) ",text)
    if m != None:
        if m.group(1) == 'S':
            return 'upper'
        else:
            return 'lower'
    return None

class MOLegislationScraper(LegislationScraper):
    state = 'mo'
    house_root = 'http://www.house.mo.gov'
    senate_root = 'http://www.senate.mo.gov'

    # wrapper to call senate or house scraper.  No year check
    # here, since house and senate have different backdates
    def scrape_bills(self,chamber,year):
        print "chamber: %s, year: %s" % (chamber, year)
        if chamber == 'upper':
            self.scrape_senate(year)
        elif chamber == 'lower':
            self.scrape_house(year)
        else:
            print >> sys.stder, "Need to pick a chamber"

    def scrape_senate(self,year):
    
        #we only have data from 2005-2009
        if int(year) < 2005 or int(year) > datetime.date.today().year:
            raise NoDataForYear(year)
    
        year2 = "%02d" % (int(year) % 100)
    
        # year is mixed in to the directory.  set a root_url, since
        # we'll use it later
        bill_root = self.senate_root+'/'+year2+'info/BTS_Web/'
        index_file = bill_root + 'BillList.aspx?SessionType=R'
    
        soup = soup_web(index_file)
    
        # each bill is in it's own table (nested in a larger table)
        bill_tables = soup.findAll(id="Table2")
    
        if bill_tables == None:
            return
    
        for bill_table in bill_tables:
    
            # here we just search the whole table string to get 
            # the BillID that the MO senate site uses
            m = re.search(r"BillID=(\d*)", str(bill_table))
            if m != None:
                bill_web_id = m.group(1)
                bill_url= bill_root + '/Bill.aspx?SessionType=R&BillID='+bill_web_id
                self.read_senate_billpage(bill_url, year)

    # parse through a senate bill from its page. year
    # is passed in, since it's not obvious how to retrieve
    # it from the page. calls add_bill, and add_sponsorship. 
    # also calls methods to parse actions and cosponsors.
    def read_senate_billpage(self, bill_url, year):
        soup = soup_web(bill_url)

        # get all the info needed to record the bill
        bill_id   = soup.find(id="lblBillNum").b.font.string
        bill_name = soup.find(id="lblBillTitle").font.string
        bill_desc = soup.find(id="lblBriefDesc").font.string
        bill_lr   = soup.find(id="lblLRNum").font.string

        self.add_bill('upper',year, bill_id, bill_name, bill_url=bill_url, bill_lr=bill_lr, bill_desc=bill_desc)


        # get the sponsor
        bill_sponsor = soup.find(id="hlSponsor").i.font.string
        bill_sponsor_link = soup.find(id="hlSponsor").href

        self.add_sponsorship('upper',year,bill_id,'primary',bill_sponsor,sponsor_link=bill_sponsor_link)

        # cosponsors show up on their own page, if they exist
        cosponsor_tag = soup.find(id="hlCoSponsors")
        if cosponsor_tag != None and cosponsor_tag.has_key('href'):
            self.read_senate_cosponsors(cosponsor_tag['href'], bill_id, year)

        # get the actions
        action_url = soup.find(id="hlAllActions")['href']
        self.read_senate_actions(action_url,bill_id,year)

        # stored on a separate page
        versions_url=soup.find(id="hlFullBillText")
        if versions_url != None:
            self.read_senate_bill_versions(versions_url['href'],year,bill_id)

    # add all the available versions
    def read_senate_bill_versions(self, url,year,bill_id):
        soup = soup_web(url)
        version_tags = soup.findAll('li')
        if version_tags != None:
            for version_tag in version_tags:
                pdf_url = version_tag.font.a['href']
                version = version_tag.font.a.string
                self.add_bill_version('upper',year,bill_id,version,pdf_url,pdf_url=pdf_url,txt_url=None)
        
    # parse through a senate actions page. calls add_action
    def read_senate_actions(self,url,bill,session):
        soup = soup_web(url)
        bigtable = soup.find(id='Table5')
        actionrow = bigtable.next.next.nextSibling.next.nextSibling.nextSibling
        actiontable = actionrow.td.div.table
        for row in actiontable.findAll('tr'):
            date = row.td.string
            action = row.td.nextSibling.nextSibling.string
            action_chamber = senate_get_chamber_from_action(action)
            self.add_action('upper',session,bill,action_chamber,action,date)

    # parse through a senate cosponsors page. calls add_sponsorship
    def read_senate_cosponsors(self, url, bill_id, year):
        soup = soup_web(url)

        #cosponsors are all in a table
        cosponsor_table = soup.find(id="dgCoSponsors")
        cosponsors = cosponsor_table.findAll("tr")

        for cosponsor_row in cosponsors:
            #cosponsors include district, so parse that out
            cosponsor_string = cosponsor_row.font.string
            cosponsor = clean_text(cosponsor_string)

            # they give us a link to the congressperson, so we might
            # as well keep it.
            cosponsor_url = cosponsor_row.a.href

            self.add_sponsorship('upper',year,bill_id,'cosponsor',
                                 cosponsor,sponsor_link=cosponsor_url)
        
    
    # parse out the house data
    def scrape_house(self,year):

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
            bill_page = self.house_root + '/billtracking/' + session_code + '/billist.htm'
            self.read_house_billpage(bill_page,year)

    # get the list of bills off an index page, call a function
    # to parse each of them
    def read_house_billpage(self,url,year):

        url_root = re.match("(.*//.*?/)",url).group(1)
        soup = soup_web(url) 
    
        # find the first center tag, take the text after 'House of Representatives'
        # and before 'Bills' as the session name
        header_tag = soup.find('center')
        m = re.search("House of Representatives(.*?)Bills", str(header_tag), re.I | re.DOTALL) 
        session = m.group(1)
        session = re.sub("<.*?>", '', session).strip()

        #get bills
        bills = soup.findAll('b')

        for bill in bills:
            bill_link = bill.find(href = re.compile("bills", re.I))
            if bill_link != None:
                bill_url = url_root + bill_link['href']
                self.read_house_bill(bill_url,session)

    # parse out a bill. calls add_bill, add_sponsorship,
    # add_bill_version. helper functions for cosponsors and actions
    def read_house_bill(self,url,session):
        url = re.sub("content","print",url)
        soup = soup_web(url)

        header_table = soup.table

        # get all the info needed to record the bill
        bill_id = header_table.b.string
        bill_id = clean_text(bill_id)

        bill_desc = header_table.td.td.string
        bill_desc = clean_text(bill_desc)

        # no bill name is provided, just a description
        bill_name = None

        lr_label_tag = soup.find(text = re.compile("LR"))
        bill_lr      = lr_label_tag.next.string.strip()

        # could substitute the description for the name, but keeping it separate for now.
        self.add_bill('lower',session, bill_id, bill_name, bill_url=url, bill_lr=bill_lr, bill_desc=bill_desc)

        # get the sponsors and cosponsors
        sponsor_dirty = soup.em.string
        m = re.search("(.*)\(.*\)",sponsor_dirty)
        if m != None:
            bill_sponsor = m.group(1)
        else:
            bill_sponsor = sponsor_dirty

        # find the table with bill details...it'll be useful later     
        bill_details_tbl = soup.table.nextSibling.nextSibling

        bill_sponsor_link = None
        if bill_details_tbl.a != None:
            bill_sponsor_link = bill_details_tbl.a['href']

        self.add_sponsorship('lower',session,bill_id,'primary',bill_sponsor,sponsor_link=bill_sponsor_link)
        
        # check for cosponsors
        cosponsor_cell = bill_details_tbl.find(text = re.compile("CoSponsor")).next
        if cosponsor_cell.a != None:
            self.read_house_cosponsors(cosponsor_cell,session,bill_id)

        # parse out all the actions
        actions_link_tag = soup.find('a',text='ACTIONS').previous.previous
        
        actions_link = self.house_root + actions_link_tag['href']
        actions_link = re.sub("content","print",actions_link)
        self.read_house_actions(actions_link,bill_id,session)

        # get bill versions
        version_tags = soup.findAll(href=re.compile("biltxt"))
        if version_tags != None:
            for version_tag in version_tags:
                version  = clean_text(version_tag.b.string)
                text_url = self.house_root + version_tag['href']
                pdf_url  = self.house_root + version_tag.previousSibling.previousSibling['href']
                self.add_bill_version('lower',session,bill_id,version,text_url,pdf_url=pdf_url,txt_url=text_url)

    # parses the house action table
    def read_house_actions(self,url,bill,session):
        soup = soup_web(url)
        rows = soup.findAll('tr')

        # start with index 0 because the table doesn't have an opening <tr>
        first_row = rows[0]
        date = first_row.td.string
        action = first_row.td.nextSibling.nextSibling.string
        
        for row in rows[1:]:
            # new actions are represented by having dates in the first td
            # otherwise, it's a continuation of the description from the 
            # previous action
            if row.td != None:
                if row.td.string != None and row.td.string != ' ':
                    action_chamber = house_get_chamber_from_action(action)
                    self.add_action('lower',session,bill,action_chamber,action, date)
                    date = row.td.string
                    action = row.td.nextSibling.nextSibling.string
                else:
                    action += ' ' + row.td.nextSibling.nextSibling.string

        # add that last action
        action_chamber = house_get_chamber_from_action(action)
        self.add_action('lower',session,bill,action_chamber,action, date)
        
        
    # parse out lists of house cosponsors from the bill page
    # loads the text of the bill in cases of more than one cosponsor
    def read_house_cosponsors(self,cell,session,bill_id):

        # if there's only one sponsor, we don't have to worry about this.
        if cell.a.nextSibling == None or \
           cell.a.nextSibling.nextSibling == None or \
           not cell.a.nextSibling.nextSibling.has_key('href'):

            cosponsor_dirty = cell.a.em.string
            cosponsor = clean_text(cosponsor_dirty)

            self.add_sponsorship('lower',session,bill_id,'cosponsor',
                                 cosponsor,sponsor_link = cell.a['href'])

        else: #there are several sponsors, and we have to go to the bill text
            bill_text_url = self.house_root + cell.a.nextSibling.nextSibling['href']
            #don't need to parse bill in to soup
            req = urllib2.Request(bill_text_url)
            response = urllib2.urlopen(req)
            doc = response.read()
            
            # people between (Sponsor) and (Co-Sponsor) are the cosponsors
            m = re.search(r"\(Sponsor\),(.*)\(Co", doc, re.DOTALL) 
            cosponsor_list = clean_text(m.group(1))
            cosponsor_list = re.split(" ?(?:,| AND ) ?",cosponsor_list)

            for cosponsor_dirty in cosponsor_list:
                cosponsor = clean_text(cosponsor_dirty)
                self.add_sponsorship('lower',session,bill_id,
                                     'cosponsor',cosponsor)


if __name__ == '__main__':
    MOLegislationScraper().run()
