#!/usr/bin/python

# Notes about this scraper:
# 1. This scripts bills after 2005.

from BeautifulSoup import BeautifulSoup
import re
import urllib,urllib2
import datetime

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

def scrape_legislation(chamber,year):
    print "chamber: %s, year: %s" % (chamber, year)
    if chamber == 'upper':
        chamber_abbr='h'

        #we only have data from 2005-2009
        assert int(year) >= 2005, "no upper chamber data from before 2005"
        assert int(year) <= datetime.date.today().year, "no future data"
    
        year2 = "%02d" % (int(year) % 100)
    
        # year is mixed in to the directory.  set a root_url, since
        # we'll use it later
        root_url ='http://www.senate.mo.gov/'+year2+'info/BTS_Web/'
        index_file = root_url + 'BillList.aspx?SessionType=R'
    
        # get the file, parse it with BeautifulSoup
        req = urllib2.Request(index_file)
        response = urllib2.urlopen(req)
        doc = response.read()
        soup = BeautifulSoup(doc)#this gives us an index page
    
    
        # each bill is in it's own table (nested in a larger table)
        bill_tables = soup.findAll(id="Table2")
    
        if bill_tables == None:
            yield 
    
        for bill_table in bill_tables:
    
            bill_id      = ''
            bill_desc    = ''
            bill_url     = ''
            bill_sponsor = ''
    
            bill_id_cell = bill_table.find(id=re.compile("BillNum"))
            if bill_id_cell != None:
                bill_id = bill_id_cell.b.font.string
    
            bill_desc_cell = bill_table.find(id=re.compile("BriefDesc"))
            if bill_desc_cell != None:
                bill_desc = bill_desc_cell.font.string
    
            bill_desc_cell = bill_table.find(id=re.compile("Sponsor"))
            if bill_sponsor != None:
                bill_sponsor = bill_desc_cell.b.font.string
    
            # here we just search the whole table string to get 
            # the BillID that the MO senate site uses
            m = re.search(r"BillID=(\d*)", str(bill_table))
            if m != None:
                bill_web_id = m.group(1)
                bill_url= root_url + 'Bill.aspx?SessionType=R&BillID='+bill_web_id
    
            yield {'state':'M0','chamber':'upper','session':year,
                   'bill_id':bill_id,'remote_url':bill_url,
                   'name':bill_desc,'bill_sponsor':bill_sponsor}

    elif chamber == 'lower':
        chamber_abbr='s'

        #we only have data from 1998-2009
        assert int(year) >= 1998, "no lower chamber data from before 1998"
        assert int(year) <= 2009, "no future data"
    
        year2 = "%02d" % (int(year) % 100)
    
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
            page_root = 'http://www.house.mo.gov'
            bill_page = page_root + '/billtracking/' + session_code + '/billist.htm'
    
            # get the file, parse it with BeautifulSoup
            req = urllib2.Request(bill_page)
            response = urllib2.urlopen(req)
            doc = response.read()
            soup = BeautifulSoup(doc)#this gives us an index page
    
            # find the first center tag, take the text after 'House of Representatives'
            # and before 'Bills' as the session
            header_tag = soup.find('center')
            m = re.search("House of Representatives(.*?)Bills", str(header_tag), re.I | re.DOTALL) 
            session = m.group(1)
            session = re.sub("<.*?>", '', session).strip()
    
            #get bills
            bills = soup.findAll('b')
    
            for bill in bills:
                bill_link = bill.find(href = re.compile("HB\d*?\.HTM", re.I))
                if bill_link != None:
                    bill_url = page_root + bill_link['href']
    
		    # bill id is inside the link
                    bill_id = bill_link.string.strip()
                    
		    # sponsor is in the next link
		    # info is outside of the <b> tag we used to find the bill
                    if int(year) >= 2000:
                        bill_sponsor = bill_link.nextSibling.next.string.strip()
                        bill_info = str(bill.nextSibling.next.next).strip()
                    else:
                        bill_sponsor = bill_link.nextSibling.next.next.string.strip()
                        bill_info = str(bill.nextSibling.next.next.next).strip()
    
		    bill_info = re.sub(r"(\r|\n|\s)+", " ", bill_info)
    
		    # parse out the description and the LR number
		    m = re.match("(.*?)\(LR# (\d.*?)\)", bill_info, re.DOTALL)
		    bill_desc = m.group(1)
		    bill_lr = m.group(2)
    
                    yield {'state':'M0','chamber':'lower','session':session,
                           'bill_id':bill_id,'remote_url':bill_url,
                           'name':bill_desc,'bill_sponsor':bill_sponsor,
                           'lr':bill_lr }

    else:
        print >> sys.stder, "Need to pick a chamber"


if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
