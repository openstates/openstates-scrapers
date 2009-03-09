#!/usr/bin/python
import urllib, urllib2
import re
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('.')
from pyutils.legislation import run_legislation_scraper

def scrape_legislation(chamber, year):
    if chamber == 'upper':
        chamber_abbr = 'H'
    elif chamber == 'lower':
        chamber_abbr = 'S'

    #set up POST data
    values = [('txtsessionyear',year),
              ('txttitle',''),
              ('txtlsrnumber',''),
              ('Submit1','Submit')]
    params = urllib.urlencode(values)
    search_url='http://www.gencourt.state.nh.us/bill_status/Results.aspx'

    #request page with list of all bills in year
    req = urllib2.Request(search_url, params)
    response = urllib2.urlopen(req)
    doc = response.read()
    soup = BeautifulSoup(doc)

    #parse results
    bills = soup.find("table",{"class":"ptable"})
    trs = soup.findAll("tr")
    #go through all of the table rows with relevant data
    tr_start = 8
    tr_hop = 11 
    i = 0
    while (tr_start+(tr_hop*i)) < len(trs):
        tr = trs[tr_start+(tr_hop*i)]
        i = i + 1
        #strip off extra white space from name
        id = tr.find("big").string.strip()
        bill_id = tr.find("big").string.strip()
        exp = re.compile("^(\w*)")
        bill_id = exp.search(id).group(1)
        
        #check to see if its in the proper chamber
        exp = re.compile("^"+chamber_abbr)
        if exp.search(bill_id) == None:
            continue #in wrong house
            
        #check to see it is a bill and not a resolution
        exp = re.compile("B")
        if exp.search(bill_id) == None:
            continue #not a bill

        #get bill_id suffix if exists
        exp = re.compile("(-\w*)$")
        res = exp.search(id)
        if res != None:
            bill_id = bill_id + res.group(1)
        
        #grab url of bill text
        urls = tr.findAll("a")
        exp = re.compile("Bill Text")
        for url in urls:
            if exp.search(str(url.string)) != None:
                regexp = re.compile("href=\"(\S*)\"")
                bill_url = regexp.search(str(url))
                bill_url = bill_url.group(1)
                break
        yield {'state':'NH', 'chamber':chamber, 'session':year,
               'bill_id':bill_id, 'remote_url':bill_url}



if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
