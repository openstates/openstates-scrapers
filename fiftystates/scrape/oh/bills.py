from __future__ import with_statement
import urlparse
import datetime as dt

from fiftystates.scrape.oh import metadata
from fiftystates.scrape.oh.utils import chamber_name, parse_ftp_listing
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import xlrd
import urllib
import lxml.etree


class OHBillScraper(BillScraper):
    state = 'oh'


    def scrape(self, chamber, year):
        if int(year) < 2009 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_house_bills()
        elif chamber == 'lower':
            self.scrape_senate_bills()


    def scrape_house_bills(self):

        house_bills_url = 'http://www.lsc.state.oh.us/status128/hb.xls'
        house_jointres_url = 'http://www.lsc.state.oh.us/status128/hjr.xls'
        house_concurres_url = 'http://www.lsc.state.oh.us/status128/hcr.xls'
        files = (house_bills_url, house_jointres_url, house_concurres_url)

        for house_file in files:

            house_bills_file = urllib.urlopen(house_file).read()
            f = open('oh_bills.xls','w')
            f.write(house_bills_file)
            f.close()
        
        
            wb = xlrd.open_workbook('oh_bills.xls')
            sh = wb.sheet_by_index(0)
        
            house_file = str(house_file)
            if len(str(house_file)) == 44:
                file_type = house_file[len(house_file) - 7:len(house_file)-4]
            else:
                file_type = house_file[len(house_file) - 6:len(house_file)-4]

            for rownum in range(1, sh.nrows):
            
                bill_id = file_type + str(int(rownum))
                bill_title = str(sh.cell(rownum, 3).value) 
                bill = Bill( '128', 'upper', bill_id, bill_title)
                bill.add_sponsor( 'primary', str(sh.cell(rownum, 1).value) )

                if sh.cell(rownum, 2).value is not '':
                    bill.add_sponsor( 'cosponsor', str(sh.cell(rownum, 2).value) )

                actor = ""

                #Actions - starts column after bill title
                for colnum in range( 4, sh.ncols - 1):
            
    
                    coltitle = str(sh.cell(0, colnum).value)
                    cell = sh.cell(rownum, colnum)              

                    if len(coltitle) != 0:

                        if coltitle.split()[0] == 'House':
                            actor = "upper"
                        elif coltitle.split()[0] == 'Senate':
                            actor = "lower"
                        elif coltitle.split()[-1] == 'Governor':
                            actor = "Governor"
                        else:
                            actor = actor
 
                    action = str(sh.cell( 0, colnum).value)
                    date = cell.value

                    if type(cell.value) == float:
                        bill.add_action(actor, action, date)    

                    if (len(coltitle) != 0 ) and coltitle.split()[-1] == 'Committee':
                        committee = str(cell.value)
                        bill.add_action(committee, action, date = '')

                bill.add_source(house_file)
                self.scrape_votes(bill, file_type, rownum)

                self.save_bill(bill)



    def scrape_senate_bills(self):

        senate_bills_url = 'http://www.lsc.state.oh.us/status128/sb.xls'
        senate_jointres_url = 'http://www.lsc.state.oh.us/status128/sjr.xls'
        senate_concurres_url = 'http://www.lsc.state.oh.us/status128/scr.xls'
        files = [senate_bills_url, senate_jointres_url, senate_concurres_url]

        for senate_file in files:

            senate_bills_file = urllib.urlopen(senate_file).read()
            f = open('oh_bills.xls','w')
            f.write(senate_bills_file)
            f.close()


            wb = xlrd.open_workbook('oh_bills.xls')
            sh = wb.sheet_by_index(0)

            senate_file = str(senate_file)
            if len(str(senate_file)) == 44:
                file_type = senate_file[len(senate_file) - 7:len(senate_file)-4]
            else:
                file_type = senate_file[len(senate_file) - 6:len(senate_file)-4]



            for rownum in range(1, sh.nrows):

                bill_id = file_type + str(int(rownum))
                bill_title = str(sh.cell(rownum, 3).value)
                bill = Bill( '128', 'lower', bill_id, bill_title)
                bill.add_sponsor( 'primary', str(sh.cell(rownum, 1).value) )

                if sh.cell(rownum, 2).value is not '':
                    bill.add_sponsor( 'cosponsor', str(sh.cell(rownum, 2).value) )

                actor = ""

                #Actions - starts column after bill title
                for colnum in range( 4, sh.ncols - 1):


                    coltitle = str(sh.cell(0, colnum).value)
                    cell = sh.cell(rownum, colnum)

                    if len(coltitle) != 0:

                        if coltitle.split()[0] == 'House':
                            actor = "upper"
                        elif coltitle.split()[0] == 'Senate':
                            actor = "lower"
                        elif coltitle.split()[0] == 'Gov.':
                            actor = "Governor"
                        elif coltitle.split()[-1] == 'Gov.':
                            actor = "Governor"
                        elif coltitle.split()[-1] == 'Governor':
                            actor = "Governor"
                        else:
                            actor = actor

                    action = str(sh.cell( 0, colnum).value)
                    date = cell.value


                    if type(cell.value) == float:
                        bill.add_action(actor, action, date)

                    if (len(coltitle) != 0 ) and coltitle.split()[-1] == 'Committee':
                        committee = str(cell.value)
                        bill.add_action(committee, action, date = '')

                bill.add_source(senate_file)
                self.scrape_votes(bill, file_type, rownum)

                self.save_bill(bill)


    def scrape_votes(self, bill, file_type, number):


        vote_url = 'http://www.legislature.state.oh.us/votes.cfm?ID=128_' + file_type + '_' + str(number)
        
        with self.urlopen(vote_url) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            
            save_date = ''
            for el in root.xpath('/html/body/table/tr[3]/td/table/tr[1]/td[2][@class="bigPanel"]/blockquote/font/table'):
                for mr in root.xpath('/html/body/table/tr[3]/td/table/tr[1]/td[2][@class="bigPanel"]/blockquote/font/table/tr[position() > 1]'):
                    
                    yes_count = 0
                    yes_placement = 0
                    no_count = 0
                    no_placement = 0 

                    date = mr.xpath('string(td/font/a)')
                    date = date.lstrip()
                    date = date.rstrip()
                    info = mr.xpath('string(td[2]/font)')  

                    
                    #makes sure that date is saved 
                    if len(date.split()) > 0:
                        save_date = date

                    #figures out the number of votes for each way
                    #also figures out placement of yes and no voters starts for later iteration
                    if info.split()[0] == 'Yeas':
                                                
                        #yes votes
                        yes_count = info.split()[2]

                        #no votes
                        for voter in range(3, len(info.split())):
                           if info.split()[voter] == '-':
                            no_count = info.split()[voter + 1]
                            no_placement = voter + 2
                            yes_placement = voter - 2
                                 

                    #motion and chamber
                    if info.split()[-1] == 'details':
                        motion = info[0:len(info)-10]
                        motion = motion.lstrip()
                        motion = motion.rstrip()
                        chamber = motion.split()[0]

                    
                    #pass or not (only by which has more. need to see look up how they are passed)
                    if yes_count > no_count:
                        passed = True
                    else:
                        passed = False

                    vote = Vote(chamber, save_date, motion, passed, yes_count, no_count, "other_count")

                    #adding in yas voters
                    for voters in range(3, yes_placement):
                        legis = ""
                        initials = 0                        

                        #checks to see if the next name is actually an initial
                        if len(info.split()[voters+1]) < 2:
                            legis = legis + info.split()[voters] + " " + info.split()[voters + 1]
                        elif len(info.split()[voters]) < 2:
                            initials = 1
                        else:
                            legis = legis + info.split()[voters]
                        
                        if initials < 1:
                            vote.yes(legis)
                    
                    #adding in no voters
                    for voters in range(no_placement, len(info.split())):
                        legis = ""                                         
                        initials = 0

                        #checks to see if the next name is actually an initial
                        if (info.split()[voters] != info.split()[-1]) and (len(info.split()[voters+1]) < 2):
                            legis = legis + info.split()[voters] + " " + info.split()[voters + 1]
                        elif len(info.split()[voters]) < 2:
                            initals = 1
                        else:
                            legis = legis + info.split()[voters]

                        if initials < 1:
                            vote.no(legis)
                    
                    #gets rid of blank votes
                    if yes_count > 0 or no_count > 0:
                        vote.add_source(vote_url)
                        bill.add_vote(vote)   

