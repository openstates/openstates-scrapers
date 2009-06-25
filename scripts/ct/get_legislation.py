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

class CTVote():
    def __init__():
        url=None
        date=None
        yeas=None
        neys=None
        others=None
        passed=None
        chamber=None
        url=None
        
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
            for line in vote_table:
                line = str(line)
                line = line.strip()
                if (len(line) > 0) and (line.find("CGAWhiteOnBlue") < 0):
                    regexp = re.compile("href=\"(\S*)\"")
                    vote_url = regexp.search(line)
                    vote_url = vote_url.group(1)
                    vote_url = "http://cga.ct.gov"+vote_url
                    self.scrape_votes(vote_url)

        print "-----------------------"
                

    #url is the url where the vote info page is.  Returns Vote object
    def scrape_votes(self,url):
        soup = BeautifulSoup(urllib2.urlopen(urllib2.Request(url)).read())
        date=None
        motion=None
        yays=-1
        neys=-1
        others=-1
        passed=None
        chamber=None
        
        fonts = soup.findAll('font')
        if len(fonts) > 4: #data is vaguely structured
            for line in fonts:
                #this could be sped up.
                line = str(line.contents)
                line = line.strip()
                if line.find("Taken on") > -1:
                    #then the text is in the form of: "Take on <date> <reason>"
                    split = line.split(None,3)
                    date = split[2]
                    motion=split[3]
                    print split
                elif line.find("Those voting Yea") > -1:
                    print line + "- yea"
                elif line.find("Those voting Nay") > -1:
                    print line + "- nay"
                elif line.find("Those absent and not voting") > -1:
                    print line + "- other"
                elif (line.find("Necessary for Adoption") > -1) or (line.find("Necessary for Passage") > -1):
                    print line + "- necessary"
        else:
            #data is mostly unstructured. Have to sift through a string
            data = soup.find('pre')
            #print data.contents
            lines = data.contents[len(data.contents)-1]
            lines = lines.strip()
            exp = re.compile(r'\n+|\r+|\f+')
            lines = exp.split(lines)
            print lines
            line=""
            if line.find("Taken on") > -1:
                #then the text is in the form of: "Take on <date> <reason>"
                split = line.split(None,3)
                date = split[2]
                motion=split[3]
                print split
            elif line.find("Those voting Yea") > -1:
                print line + "- yea"
            elif line.find("Those voting Nay") > -1:
                print line + "- nay"
            elif line.find("Those absent and not voting") > -1:
                print line + "- other"
            elif (line.find("Necessary for Adoption") > -1) or (line.find("Necessary for Passage") > -1):
                print line + "- necessary"



#all CT bill pages have a bug in them (three quotation marks in a row 
#in one of the href tags) that crashes beautiful soup.  This funciton
#returns a version of the html without this bug
def cleanup_html(html):
    return html.replace('"""','"')


if __name__ == '__main__':
    CTLegislationScraper().run()
