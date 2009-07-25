#!/usr/bin/env python

# Notes about this scraper:
# 1. MA has not posted any bill text of bills in the current session,
#    I am guessing I will have to scrape this information off of openmass.gov
#    once the information is available.
# 2. This scripts bills from 2005-2008.  Some bill numbers do not have full 
#    text, for the time being, we still provide a URL of where they should
#    be located.
# 3. I can get most full bill texts in pdf, however some are only available in
#    html.  It will make our life harder later on, but this is the best I can 
#    do for now.

from BeautifulSoup import BeautifulSoup
import re
import urllib,urllib2
import time

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyutils.legislation import run_legislation_scraper

def scrape_legislation(chamber,year):
    if chamber == 'upper':
        chamber_abbr='h'
        chamber_url='house'
    elif chamber == 'lower':
        chamber_abbr='s'
        chamber_url = 'senate'
    else:
        #TODO print to stderr
        print "Need to pick a chamber"
        

    session = session_number(int(year))

    #we only have data from 2005-2008
    assert int(year) >=2005
    assert int(year) <= 2008


    index_file ='http://www.mass.gov/legis/'+str(session)+'history'
    req = urllib2.Request(index_file)
    response = urllib2.urlopen(req)
    doc = response.read()
    soup = BeautifulSoup(doc)#this gives us an index page
    
    #scraping links to all bills to get list of bills
    re_str = "\w\w*\d\d\d\d\d.htm"
    links = soup.findAll(href=re.compile(re_str))
    if links == None:
        yield 

    for link in links:
        #check to see bill chamber matches what we are trying to scrape
        if re.compile("^"+chamber_abbr).search(link.string) == None: 
            continue
        res = re.compile("(h|s)\w*(\d\d\d\d\d)").search(link.string)
        bill_id = res.group(1)+res.group(2)

        bill_url=calculate_bill_url(chamber_url,res.group(2),session)

        yield {'state':'MA','chamber':chamber,'session':year,
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
def session_number(year):
    if (year % 2) == 0:
        year = year - 1
    return int((year*.5) - 818.5)

if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
