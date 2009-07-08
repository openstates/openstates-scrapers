#!/usr/bin/python

#Bill numbering:
#SB 1-5000. (errors around 1072?)
#HB 5001-9999


from BeautifulSoup import BeautifulSoup
import re
import urllib,urllib2
import time
import string

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
                
                self.add_bill_votes(bill,chamber,soup)

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
    def add_bill_votes(self,bill,chamber,soup):
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
                    self.scrape_votes(vote_url,chamber)

                

    #url is the url where the vote info page is.  Returns Vote object
    def scrape_votes(self,url,chamb):
        soup = BeautifulSoup(urllib2.urlopen(urllib2.Request(url)).read())
        date=None
        motion=None
        yeas=None
        neas=None
        others=None
        passed=None
        chamber=chamb
        necessary=None
        vote=None        

        fonts = soup.findAll('font')
        span = soup.findAll('span')
        if (len(fonts) + (len(span))) > 4: #data is vaguely structured
            if (len(fonts) < 4):
                fonts = span
            for line in fonts:
                #this could be sped up.
                line = str(line.contents[0])
                line = line.strip()
                if line.find("Taken on") > -1:
                    #then the text is in the form of: "Take on <date> <reason>"
                    split = line.split(None,3)
                    date = split[2]
                    if (len(split) > 3):
                        motion=split[3]
                elif line.find("Those voting Yea") > -1:
                    yeas = self.get_num_from_line(line)
                elif line.find("Those voting Nay") > -1:
                    neas = self.get_num_from_line(line)
                elif line.find("Those absent and not voting") > -1:
                    others = self.get_num_from_line(line)
                elif (line.find("Necessary for Adoption") > -1) or (line.find("Necessary for Passage") > -1):
                    necessary = self.get_num_from_line(line)
            if yeas >= necessary:
                passed = True
            else:
                passed = False
            vote = Vote(chamber,date,motion,passed,yeas,neas,others)
            
            #figure out who voted for what
            table = soup.findAll('table')
            tds = table[len(table)-1].findAll('td')#get the last table
            
            vote_value = None
            digits = re.compile('^[\d ]+$')
            for cell in tds:
                string = cell.find('font')
                if (string == None):
                    string = cell.find('span') #either we are looking at fonts or spans
                if (string != None):
                    string = string.contents[0]
                    string = string.strip()
                else:
                    string = ''
                if (len(string) > 0) and (digits.search(string) == None):
                    if vote_value == None:
                        if (string == 'Y') or (string == 'N'):
                            vote_value = string
                        elif (string == 'X') or (string == 'A'):
                            vote_value = 'X'
                    else:
                        if vote_value == 'Y':
                            vote.yes(string)
                        elif vote_value == 'N':
                            vote.no(string)
                        else:
                            vote.other(string)
                        vote_value = None
            
        else:
            #data is mostly unstructured. Have to sift through a string
            data = soup.find('pre')
            lines = data.contents[len(data.contents)-1]
            lines = lines.strip()
            exp = re.compile(r'\n+|\r+|\f+')
            lines = exp.split(lines)
            names = []
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.find("Taken on") > -1:
                #then the text is in the form of: "Take on <date> <reason>"
                    split = line.split(None,3)
                    date = split[2]
                    if (len(split) > 3):
                        motion=split[3]
                elif line.find("Those voting Yea") > -1:
                    yeas = self.get_num_from_line(line)
                elif line.find("Those voting Nay") > -1:
                    neas = self.get_num_from_line(line)
                elif line.find("Those absent and not voting") > -1:
                    others = self.get_num_from_line(line)
                elif (line.find("Necessary for Adoption") > -1) or (line.find("Necessary for Passage") > -1):
                    if (line.find("Adoption") > -1):
                        motion="Adoption"
                    else:
                        motion="Passage"
                    necessary = self.get_num_from_line(line)
                elif (line.find("The following is the roll call vote:") > -1):
                    break #the next lines contain actual votes
            #process the vote values
            if yeas >= necessary:
                passed = True
            else:
                passed = False
            vote = Vote(chamber,date,motion,passed,yeas,neas,others)
            lines = lines[i+1:]
            lines = string.join(lines,'  ')
            lines = lines.split('  ')
            absent_vote_value = re.compile('^(X|A)$')
            yea_vote_value = re.compile('^Y$')
            nea_vote_value = re.compile('^N$')
            #there aren't two spaces between vote and name so it doesn't get parsed
            annoying_vote = re.compile('^(Y|X|A|N) ([\S ]+)$')
            digits = re.compile('^[\d ]+$')
            vote_value = None
            for word in lines:
                word = word.strip()
                if (len(word) > 0) and (digits.search(word) == None):
                    word = strip_digits(word)
                    if vote_value != None:
                        if vote_value == 'Y':
                            vote.yes(word)
                        elif vote_value == 'N':
                            vote.no(word)
                        else:
                            vote.other(word)
                        vote_value = None
                    elif absent_vote_value.match(word) != None:
                        vote_value = 'X'
                    elif yea_vote_value.match(word) != None:
                        vote_value = 'Y'
                    elif nea_vote_value.match(word) != None:
                        vote_value = 'N'
                    elif annoying_vote.match(word) != None:
                        split = annoying_vote.match(word)
                        vote_value = split.group(2)
                        name = split.group(1)
                        if vote_value == 'Y':
                            vote.yes(name)
                        elif vote_value == 'N':
                            vote.no(name)
                        else:
                            vote.other(name)
                        vote_value = None


        
    def get_num_from_line(self,line):
        num = re.match('[\D]*(\d+)\w*$',line)
        num = num.group(1)
        return int(num)



#all CT bill pages have a bug in them (three quotation marks in a row 
#in one of the href tags) that crashes beautiful soup.  This funciton
#returns a version of the html without this bug
def cleanup_html(html):
    return html.replace('"""','"')

#stripts digits at beginning of string
def strip_digits(string):
    old = string
    exp = re.compile("^\d* *([\w.,'\s]+)$")
    string = exp.search(string)
    if string == None:
        return old
    return string.group(1).strip()

#gets the inner most child from the soup
def get_baby(soup):
    pass

if __name__ == '__main__':
    CTLegislationScraper().run()
