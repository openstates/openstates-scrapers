#!/usr/bin/python

#Bill numbering:
#SB 1-5000. (errors around 1072?)
#HB 5001-9999


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
        min = 5001
        max = 9999
    elif chamber == 'lower':
        min = 1
        max = 5000
        local_filename = ''
        
    for i in range(min,max+1):
        #obtain html
        index_file ='http://cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&bill_num=%d&which_year=%s'\
            %(i,year)
        req = urllib2.Request(index_file)
        response = urllib2.urlopen(req)
        doc = response.read()
        soup = BeautifulSoup(doc)
        
            #check to see legislation exists
        if soup.find("div",{"class":"CGASubHeader"}) == None:
            continue #bill does not exist
        else: 
            ahref = soup.find("table",{"id":"CGABillText"}).find("a")
            regexp = re.compile("href=\"(\S*)\"")
            bill_url = regexp.search(str(ahref))
            bill_url = bill_url.group(1)
            bill_url = "http://cga.ct.gov"+bill_url
            #if download:
            #    local_filename = 'data/ct/legislation/%s%s%04d.htm' %(chamber,year,i)
            #    urllib.urlretrieve(bill_url,local_filename)
            #    time.sleep(0.5)
            #else:
            #    local_filename = ''
                
            yield {'state':'CT','chamber':chamber,'session':year,
                   'bill_id':i,'remote_url':bill_url}
                
    
if __name__ == '__main__':
    run_legislation_scraper(scrape_legislation)
