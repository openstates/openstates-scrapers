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
sys.path.append('./scripts')
from pyutils.legislation import *



class CTLegislationScraper(LegislationScraper):
    #some constants
    state = 'ct'
    min_year = 1991
    upper_bill_no_min = 5001
    upper_bill_no_max = 9999
    lower_bill_no_min = 1
    lower_bill_no_max = 5000

    def scrape_legislators(self,chamber,year):
        pass

    def scrape_bills(self,chamber,year):
        if year < self.min_year:
            raise NoDataForYear(year)
        if chamber == 'upper':
            min = self.upper_bill_no_min
            max = self.upper_bill_no_max
        elif chamber == 'lower':
            min = self.lower_bill_no_min
            max = self.lower_bill_no_max
        
        for i in range(min,max+1):
        #obtain html
            index_file ='http://cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&bill_num=%d&which_year=%s'\
               %(i,year)
            req = urllib2.Request(index_file)
            response = urllib2.urlopen(req)
            doc = response.read()
            soup = BeautifulSoup(cleanup_html(doc))

            #check to see legislation exists
            if soup.find("div",{"class":"CGASubHeader"}) == None:
                continue #bill does not exist
            else: 
                #find bill title
                tables = soup.find("table",{"class":"CGABlackOnWhite"})
                bill_title = tables.findAll("td")[1].contents[2]
                bill_summary =  tables.findAll("td")[1].contents[5]


                bill = Bill(year,chamber,i, bill_title, summary=bill_summary)

                #find urls of bill versions
                self.add_bill_versions(bill,soup)

                #add sponsors
                self.add_bill_sponsors(bill,soup)

                self.add_bill_actions(bill,soup)
                
                self.add_bill_votes(bill,soup)

                self.add_bill(bill)

    def add_bill_sponsors(self,bill,soup):
        
        #add primary sponsors
        sponsors = soup.find("table",{"class":"CGABlackOnWhite"}).findAll("td")[2]
        num_sponsors = len(sponsors)/2
                
        for i in range(num_sponsors):
            name = sponsors.contents[(i+1)*2]
            if i == 0:
                name = name.replace("Introduced by:","")
            name = name.strip()
            if (len(name) > 0):
                bill.add_sponsor("primary",sponsors.contents[(i+1)*2])

        #find cosponsors, if exists
        for td in soup.findAll('td'): #ug, this is slow, can I be more efficient here?
            if (td.string != None) and (td.string.find("Co-sponsors of") > -1):
                contents = td.findAllNext('tr')[0].find('td').contents
                for item in contents:
                    item = item.string
                    if item != None:
                        if item.find("<br") < 0:
                            item = item.strip()
                            if len(item) > 0:
                                bill.add_sponsor("cosponsor",item)

    def add_bill_versions(self,bill,soup):        
        ahrefs = soup.find("table",{"id":"CGABillText"}).findAll("a")
        for href in ahrefs:
            if(href.string != "[pdf]"):
                regexp = re.compile("href=\"(\S*)\"")
                bill_url = regexp.search(str(href))
                bill_url = bill_url.group(1)
                bill_url = "http://cga.ct.gov"+bill_url
                bill.add_version(href.string,bill_url)
    
    def add_bill_actions(self,bill,soup):
        for td in soup.findAll('td'): #ug, this is slow, can I be more efficient here?
            if (td.string != None) and (td.string.find("Bill History") > -1):
                action_table = td.findAllNext('table')[0].findAll('table')[1]
                for action in action_table.findAll("tr"):
                    date = action.contents[2].string
                    action = action.contents[len(action.contents)-1].string
                    bill.add_action('',action,date)
    def add_bill_votes(self,bill,soup):
        #not all bills have votes
        vote_table = soup.find("table",{"id":"CGAVotes"})
        if vote_table != None:
            print vote_table


#all CT bill pages have a bug in them (three quotation marks in a row 
#in one of the href tags) that crashes beautiful soup.  This funciton
#returns a version of the html without this bug
def cleanup_html(html):
    return html.replace('"""','"')
if __name__ == '__main__':
    CTLegislationScraper().run()
