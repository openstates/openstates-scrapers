import datetime

from fiftystates.scrape.nj import metadata
from fiftystates.scrape.nv.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree
from dbfpy import dbf
import scrapelib

class NJBillScraper(BillScraper):
    state = 'nj'

    def scrape(self, chamber, session):

        session = int(session)
        if session < 209:
            raise NoDataForPeriod(year)
        else:
            year_abr = 2010

        self.scrape_bill_pages(session, year_abr)

    def scrape_bill_pages(self, session, year_abr):

        main_bill_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/MAINBILL.DBF' % (year_abr)
        MAINBILL_dbf, resp = self.urlretrieve(main_bill_url)
        main_bill_db = dbf.Dbf(MAINBILL_dbf)
        bill_dict = {}

        #Main information
        #print main_bill_db[2]
        for rec in main_bill_db:
            bill_type = rec["billtype"]
            bill_number = int(rec["billnumber"])
            bill_id = bill_type + str(bill_number)
            title = rec["synopsis"]
            if bill_type[0] == 'A':
                chamber = "General Assembly"
            else:
                chamber = "Senate"
            bill = Bill(session, chamber, bill_id, title)
            bill.add_source(main_bill_url)
            bill_dict[bill_id] = bill

        bill_action_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/BILLHIST.DBF' % (year_abr)
        ACTION_dbf, resp = self.urlretrieve(bill_action_url)
        bill_action_db = dbf.Dbf(ACTION_dbf)

        #Actions
        #print bill_action_db[2]
        for rec in bill_action_db:
            bill_type = rec["billtype"]
            bill_number = int(rec["billnumber"])
            bill_id = bill_type + str(bill_number)
            bill = bill_dict[bill_id]
            action = rec["action"]
            date = rec["dateaction"]
            actor = rec["house"]
            comment = rec["comment"]
            bill.add_action(actor, action, str(date), comment = comment)
            bill.add_source(bill_action_url)


        
