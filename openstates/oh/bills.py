import os
import datetime

from billy.scrape import ScrapeError
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

import xlrd
import scrapelib
import lxml.html


class OHBillScraper(BillScraper):
    jurisdiction = 'oh'

    def scrape(self, session, chambers):
        if int(session) < 128:
            raise AssertionError("No data for period {}".format(session))

        status_report_url = "http://www.legislature.ohio.gov/legislation/status-reports"

        #ssl verification off due to requests bug
        doc = self.urlopen(status_report_url,verify=False)
        doc = lxml.html.fromstring(doc)
        doc.make_links_absolute(status_report_url)

        status_table = doc.xpath("//div[contains(text(),'{}')]/following-sibling::table".format(session))[0]
        status_links = status_table.xpath(".//a[contains(text(),'Excel')]/@href")


        for url in status_links:

            try:
                fname, resp = self.urlretrieve(url)
            except scrapelib.HTTPError:
                self.logger.warning("Missing report {}".format(report))
                continue

            sh = xlrd.open_workbook(fname).sheet_by_index(0)

            # once workbook is open, we can remove tempfile
            os.remove(fname)

            if int(session) < 131:
                #Lots has changed with the rollover to 131
                #but seems silly to throw out old code when
                #we can still get historical data this way
                #note that a few links and stuff had to be updated
                self.old_scrape(chamber,session,sh)

            else:
                bill_ids_found = []
                self.new_bulk_scrape(chamber,session,sh,bill_ids_found,url)
                if len(bill_ids_found) == 0:
                    self.logger.warning("No bills found in bulk data, check that it's up?")
                self.new_site_scrape(chamber,session,bill_ids_found)


    def new_bulk_scrape(self,session,sh,bill_ids_found,url):
        #get what we can from the bulk data download
        #they gave it to us, we should use it, even though
        #it doesn't seem to be complete
        for rownum in range(1, sh.nrows):
            bill_id = sh.cell(rownum, 0).value.replace(" ","").replace(".","")
            bill_type,bill_no = bill_id.split("No")
            bill_id = bill_type+bill_no.zfill(4)

            bill_type = "resolution" if "R" in bill_id else "bill"
            chamber = "lower" if "H" in bill_id else "upper"
            bill_title = sh.cell(rownum, 3).value.strip()



            bill = Bill(session, chamber, bill_id, bill_title,
                        type=bill_type,subjects=[])

            sponsor1 = sh.cell(rownum, 1).value.strip()
            bill.add_sponsor("primary",sponsor1)
            sponsor2 = sh.cell(rownum, 2).value.strip()
            if sponsor2:
                bill.add_sponsor("primary",sponsor2)

            subjects = sh.cell(rownum,4).value.split(";")
            for subject in subjects:
                if subject.strip():
                    bill["subjects"].append(subject.strip())

            bill.add_source(url)

            introduced_date = sh.cell(rownum,5).value.strip()
            if introduced_date:
                introduced_date = datetime.datetime.strptime(introduced_date,"%d/%m/%Y")
                bill.add_action(chamber,"Introduced",introduced_date,type="bill:introduced")

            refer_date = sh.cell(rownum,6).value.strip()
            committee = sh.cell(rownum,7).value.strip()
            if refer_date and committee:
                refer_date = datetime.datetime.strptime(refer_date,"%d/%m/%Y")
                bill.add_action(chamber,"Referred to committee",refer_date,type="committee:referred",committees=committee)

            comm_rep_date = sh.cell(rownum,8).value.strip()
            comm_report = sh.cell(rownum,9).value.strip()
            if comm_rep_date and comm_report:
                rep_date = datetime.datetime.strptime(comm_rep_date,"%d/%m/%Y")
                committees = committee
                if "recommends its re-referral" in report:
                    act_type = ["committee:passed","committee:referred"]
                    new_comm = sh.cell(rownum,11).value.strip()
                    committees = [committee,new_comm]
                #TODO: lots of possibilites here, get them all in.
                elif "recommends its passage/adoption" in report:
                    act_type = "committee:passed:favorable"
                bill.add_action(chamber,"Committee Reports: '{}'".format(comm_report),rep_date,type="committee:referred",committees=[committee])


            re_refer_date = 

            self.save_bill(bill)
            bill_ids_found.append(bill_id)


    def new_site_scrape(self,session,bill_ids_found):
        #bulk data was missing some stuff
        #so get remaining data from website
        #also it took a long time to get the bulk data up
        pass



    def old_scrape(self,session,sh,url):
        
        for rownum in range(1, sh.nrows):
            bill_id = sh.cell(rownum, 0).value

            bill_type = "resolution" if "R" in bill_id else "bill"
            chamber = "lower" if "H" in bill_id else "upper"

            bill_title = str(sh.cell(rownum, 3).value)

            bill = Bill(session, chamber, bill_id, bill_title,
                        type=bill_type)
            bill.add_source(url)
            bill.add_sponsor('primary', str(sh.cell(rownum, 1).value))

            # add cosponsor
            if sh.cell(rownum, 2).value:
                bill.add_sponsor('cosponsor',
                                 str(sh.cell(rownum, 2).value))

            actor = ""

            # Actions start column after bill title
            for colnum in range(4, sh.ncols - 1):
                action = str(sh.cell(0, colnum).value)
                cell = sh.cell(rownum, colnum)
                date = cell.value

                if len(action) != 0:
                    if action.split()[0] == 'House':
                        actor = "lower"
                    elif action.split()[0] == 'Senate':
                        actor = "upper"
                    elif action.split()[-1] == 'Governor':
                        actor = "executive"
                    elif action.split()[0] == 'Gov.':
                        actor = "executive"
                    elif action.split()[-1] == 'Gov.':
                        actor = "executive"

                if action in ('House Intro. Date', 'Senate Intro. Date'):
                    atype = ['bill:introduced']
                    action = action.replace('Intro. Date', 'Introduced')
                elif action == '3rd Consideration':
                    atype = ['bill:reading:3', 'bill:passed']
                elif action == 'Sent to Gov.':
                    atype = ['governor:received']
                elif action == 'Signed By Governor':
                    atype = ['governor:signed']
                else:
                    atype = ['other']

                if type(date) == float:
                    date = str(xlrd.xldate_as_tuple(date, 0))
                    date = datetime.datetime.strptime(
                        date, "(%Y, %m, %d, %H, %M, %S)")
                    bill.add_action(actor, action, date, type=atype)

            for idx,char in enumerate(bill_id):
                try:
                    int(char)
                except ValueError:
                    continue

                underscore_bill = bill_id[:idx]+"_"+bill_id[idx:]
                break

            self.scrape_votes_old(bill, underscore_bill, session)
            self.scrape_versions_old(bill, underscore_bill, session)
            self.save_bill(bill)

    def scrape_versions_old(self, bill, billname, session):
        base_url = 'http://archives.legislature.state.oh.us/'

        if 'R' in billname:
            piece = '/res.cfm?ID=%s_%s' % (session, billname)
        else:
            piece = '/bills.cfm?ID=%s_%s' % (session, billname)

        def _get_html_or_pdf_version_old(url):
            doc = lxml.html.fromstring(url)
            name = doc.xpath('//font[@size="2"]/a/text()')[0]
            html_links = doc.xpath('//a[text()="(.html format)"]')
            pdf_links = doc.xpath('//a[text()="(.pdf format)"]')
            if html_links:
                link = html_links[0].get('href')
                bill.add_version(name, base_url + link, on_duplicate='use_old',
                                 mimetype='text/html')
            elif pdf_links:
                link = pdf_links[0].get('href')
                bill.add_version(name, base_url + link,
                                 mimetype='application/pdf')

        html = self.urlopen(base_url + piece)
        # pass over missing bills - (unclear why this happens)
        if 'could not be found.' in html:
            self.warning('missing page: %s' % base_url + piece)
            return

        _get_html_or_pdf_version_old(html)
        doc = lxml.html.fromstring(html)
        for a in doc.xpath('//a[starts-with(@href, "/bills.cfm")]/@href'):
            if a != piece:
                _get_html_or_pdf_version_old(self.urlopen(base_url + a))
        for a in doc.xpath('//a[starts-with(@href, "/res.cfm")]/@href'):
            if a != piece:
                _get_html_or_pdf_version_old(self.urlopen(base_url + a))

    def scrape_votes_old(self, bill, billname, session):
        vote_url = ('http://archives.legislature.state.oh.us/bills.cfm?ID=' +
                    session + '_' + billname)

        page = self.urlopen(vote_url)
        page = lxml.html.fromstring(page)

        for jlink in page.xpath("//a[contains(@href, 'JournalText')]"):
            date = datetime.datetime.strptime(jlink.text,
                                              "%m/%d/%Y").date()

            details = jlink.xpath("string(../../../td[2])")

            chamber = details.split(" - ")[0]
            if chamber == 'House':
                chamber = 'lower'
            elif chamber == 'Senate':
                chamber = 'upper'
            else:
                raise ScrapeError("Bad chamber: %s" % chamber)

            motion = details.split(" - ")[1].split("\n")[0].strip()

            vote_row = jlink.xpath("../../..")[0].getnext()

            yea_div = vote_row.xpath(
                "td/font/div[contains(@id, 'Yea')]")[0]
            yeas = []
            for td in yea_div.xpath("table/tr/td"):
                name = td.xpath("string()")
                if name:
                    yeas.append(name)

            no_div = vote_row.xpath(
                "td/font/div[contains(@id, 'Nay')]")[0]
            nays = []
            for td in no_div.xpath("table/tr/td"):
                name = td.xpath("string()")
                if name:
                    nays.append(name)

            yes_count = len(yeas)
            no_count = len(nays)

            vote = Vote(chamber, date, motion, yes_count > no_count,
                        yes_count, no_count, 0)

            for yes in yeas:
                vote.yes(yes)
            for no in nays:
                vote.no(no)

            vote.add_source(vote_url)

            bill.add_vote(vote)
