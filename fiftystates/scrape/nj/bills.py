from datetime import datetime
from fiftystates.scrape.nj import metadata
from fiftystates.scrape.nj.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree
from dbfpy import dbf
import scrapelib
import zipfile
import csv

class NJBillScraper(BillScraper):
    state = 'nj'

    def scrape(self, chamber, session):

        session = int(session)
        if session < 209:
            raise NoDataForPeriod(session)
        else:
            year_abr = ((session - 209) * 2) + 2000

        self.scrape_bill_pages(session, year_abr)

    def scrape_bill_pages(self, session, year_abr):

        #Main Bill information
        main_bill_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/MAINBILL.DBF' % (year_abr)
        MAINBILL_dbf, resp = self.urlretrieve(main_bill_url)
        main_bill_db = dbf.Dbf(MAINBILL_dbf)
        bill_dict = {}

        for rec in main_bill_db:
            bill_type = rec["billtype"]
            bill_number = int(rec["billnumber"])
            bill_id = bill_type + str(bill_number)
            title = rec["synopsis"]
            if bill_type[0] == 'A':
                chamber = "lower"
            else:
                chamber = "upper"
            bill = Bill(str(session), chamber, bill_id, title)
            bill.add_source(main_bill_url)
            bill_dict[bill_id] = bill

        #Sponsors
        bill_sponsors_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/BILLSPON.DBF' % (year_abr)
        SPONSORS_dbf, resp = self.urlretrieve(bill_sponsors_url)
        bill_sponsors_db = dbf.Dbf(SPONSORS_dbf)

        for rec in bill_sponsors_db:
            bill_type = rec["billtype"]
            bill_number = int(rec["billnumber"])
            bill_id = bill_type + str(bill_number)
            bill = bill_dict[bill_id]
            name = rec["sponsor"]
            sponsor_type = rec["type"]
            if sponsor_type == 'P':
                sponsor_type = "Primary"
            else:
                sponsor_type = "Co-sponsor"
            bill.add_sponsor(sponsor_type, name)


        #Documents
        bill_document_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/BILLWP.DBF' % (year_abr)
        DOC_dbf, resp = self.urlretrieve(bill_document_url)
        bill_document_db = dbf.Dbf(DOC_dbf)
        
        #print bill_document_db[2]
        for rec in bill_document_db:
            bill_type = rec["billtype"]
            bill_number = int(rec["billnumber"])
            bill_id = bill_type + str(bill_number)
            bill = bill_dict[bill_id]
            document = rec["document"]
            document = document.split('\\')
            doc_name = document[-1]
            document = document[-2] + "/" + document[-1]
            year = str(year_abr) + str((year_abr + 1))
            doc_url = "ftp://www.njleg.state.nj.us/%s" % year
            doc_url = doc_url + "/" + document
            bill.add_document(doc_name, doc_url)

        #Senate Votes
        file1 = 'A' + str(year_abr)
        file2 = 'A' + str(year_abr + 1)
        file3 = 'S' + str(year_abr)
        file4 = 'S' + str(year_abr + 1)
        if str(year_abr) != '2010':
            vote_info_list = [file1, file2, file3, file4]
        else:
            vote_info_list = [file1, file3]
        for bill_vote_file in vote_info_list:
            s_vote_url = 'ftp://www.njleg.state.nj.us/votes/%s.zip' % bill_vote_file
            s_vote_zip, resp = self.urlretrieve(s_vote_url)
            zipedfile = zipfile.ZipFile(s_vote_zip)
            vfile = "%s.txt" % bill_vote_file
            vote_file = zipedfile.open(vfile, 'U')
            vdict_file = csv.DictReader(vote_file)

            votes = {}
            if bill_vote_file[0] == "A":
                chamber = "lower"
            else:
                chamber = "upper"

            for rec in vdict_file:
                bill_id = rec["Bill"]
                bill_id = bill_id.strip()
                leg = rec["Full_Name"]

                date = rec["Session_Date"]
                date = datetime.strptime(date, "%m/%d/%Y")
                action = rec["Action"]
                leg_vote = rec["Legislator_Vote"]
                vote_id = bill_id + "_" + action
                vote_id = vote_id.replace(" ", "_")
                passed = None
                
                if vote_id not in votes:
                    votes[vote_id] = Vote(chamber, date, action, passed, None, None, None, bill_id = bill_id)
                if leg_vote == "Y":
                    votes[vote_id].yes(leg)
                elif leg_vote == "N":
                    votes[vote_id].no(leg)
                else:
                    votes[vote_id].other(leg)

            #Counts yes/no/other votes and saves overall vote
            for vote in votes.itervalues():
                vote_yes_count = len(vote["yes_votes"])
                vote_no_count = len(vote["no_votes"])
                vote_other_count = len(vote["other_votes"])
                vote["yes_count"] = vote_yes_count
                vote["no_count"] = vote_no_count
                vote["other_count"] = vote_other_count
                if vote_yes_count > vote_no_count:
                    vote["passed"] = True
                else:
                    vote["passed"] = False
                vote_bill_id = vote["bill_id"]
                bill = bill_dict[vote_bill_id]
                bill.add_vote(vote)

        #Actions
        bill_action_url = 'ftp://www.njleg.state.nj.us/ag/%sdata/BILLHIST.DBF' % (year_abr)
        ACTION_dbf, resp = self.urlretrieve(bill_action_url)
        bill_action_db = dbf.Dbf(ACTION_dbf)
        bill.add_source(bill_sponsors_url)
        bill.add_source(bill_document_url)
        bill.add_source(bill_action_url)

        for rec in bill_action_db:
            bill_type = rec["billtype"]
            bill_number = int(rec["billnumber"])
            bill_id = bill_type + str(bill_number)
            bill = bill_dict[bill_id]
            action = rec["action"]
            date = rec["dateaction"]
            actor = rec["house"]
            comment = rec["comment"]
            bill.add_action(actor, action, date, comment = comment)
            self.save_bill(bill)
