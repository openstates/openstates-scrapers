#!/usr/bin/python

# Notes about this scraper:
# 1. This scripts bills after 2005.

from BeautifulSoup import BeautifulSoup
import re
import urllib,urllib2
import time

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

def scrape_legislation(chamber,year):
    if chamber == 'upper':
        chamber_abbr='h'
    elif chamber == 'lower':
        chamber_abbr='s'
    else:
        #TODO print to stderr
        print "Need to pick a chamber"
        

    #we only have data from 2005-2009
    assert int(year) >=2005
    assert int(year) <= 2009

    year2 = "%02d" % (int(year) % 100)


    if chamber == 'upper':

        root_url ='http://www.senate.mo.gov/'+year2+'info/BTS_Web/'
        index_file = root_url + 'BillList.aspx?SessionType=R'
	print index_file

        req = urllib2.Request(index_file)
        response = urllib2.urlopen(req)
        doc = response.read()
	print "downloaded"
        soup = BeautifulSoup(doc)#this gives us an index page
	
    
        #scraping tables to find 
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
            print 'bill_id: '+bill_id

            bill_desc_cell = bill_table.find(id=re.compile("BriefDesc"))
            if bill_desc_cell != None:
                bill_desc = bill_desc_cell.font.string
            print 'bill_desc: '+bill_desc

            bill_desc_cell = bill_table.find(id=re.compile("Sponsor"))
            if bill_sponsor != None:
                bill_sponsor = bill_desc_cell.b.font.string
            print 'bill_sponsor: '+bill_sponsor

            m = re.search(r"BillID=(\d*)", str(bill_table))
            if m != None:
                bill_web_id = m.group(1)
                bill_url= root_url + 'Bill.aspx?SessionType=R&BillID='+bill_web_id
            print 'bill_url: '+bill_url

            yield {'state':'M0','chamber':chamber,'session':year,
                   'bill_id':bill_id,'remote_url':bill_url}


#calculate the url for the full text
def calculate_bill_url(chamber,bill_no,session):
    url = "http://www.mass.gov/legis/bills/%s" %chamber
    #dir num is the same as the first two digits of the bill number
    dir_num = re.compile("^(\d\d)").search(bill_no).group(1)

    if chamber =="house":
        url = "%s/%d/ht%spdf/ht%s.pdf" %(url,session,dir_num,bill_no)
    elif chamber == "senate": 
        if  session == 184:#not so good at their bill organization
            #these don't come in pdf, but some don't come in html. 
            #but some only come in pdf. lose-lose
            url = "%s/st%s/st%s.htm" %(url,dir_num,bill_no)
        else:
            url = "%s/%d/st%spdf/st%s.pdf" %(url,session,dir_num,bill_no)
    else: 
        return ""
    return url
    
#calcualtes the session number given the year
#def session_number(year):
#    if (year % 2) == 0:
#        year = year - 1
#    return int((year*.5) - 818.5)

if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
