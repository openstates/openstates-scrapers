#!/usr/bin/python

#Bill numbering:
#SB 1-5000. (errors 1072..)
#HB 5001-9999

#http://cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&bill_num=100&which_year=2009

from BeautifulSoup import BeautifulSoup
import re
import urllib,urllib2
import time

# ugly hack
import sys
sys.path.append('.')
from legislation import LegislationScraper

class ConnecticutScraper(LegislationScraper):
    def scrape_legislation(self,chamber,year,download):
        if chamber == 'upper':
            chamber_abbr = 'H'
            min = 5001
            max = 9999
        elif chamber == 'lower':
            chamber_abbr = 'S'
            min = 1
            max = 5000
        local_filename = ''

        for i in range(min,max+1):
            index_file ='http://cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&bill_num=%d&which_year=%s'\
                %(i,year)
            req = urllib2.Request(index_file)
            response = urllib2.urlopen(req)
            doc = response.read()
            soup = BeautifulSoup(doc)
            if soup.find("div",{"class":"CGASubHeader"}) == None:
                continue #bill does not exist
            else: 
                ahref = soup.find("table",{"id":"CGABillText"}).find("a")
                regexp = re.compile("href=\"(\S*)\"")
                bill_url = regexp.search(str(ahref))
                bill_url = bill_url.group(1)
                bill_url = "http://cga.ct.gov"+bill_url
                if download:
                    local_filename = 'data/ct/legislation/%s%s%04d.htm' %(chamber,year,i)
                    urllib.urlretrieve(bill_url,local_filename)
                    time.sleep(0.5)
                else:
                    local_filename = ''
                
                self.add_bill('CT',chamber,year,i,bill_url,local_filename)
                print 'CT'+" "+chamber+" "+str(year)+" "+str(i)+" "+bill_url+" "+local_filename
                
    
if __name__ == '__main__':
    ConnecticutScraper('test.csv').run()
