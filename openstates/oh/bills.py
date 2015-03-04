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

        elif int(session) < 131:
            self.old_scrape(session)
            







    def old_scrape(self,session):
        status_report_url = "http://www.legislature.ohio.gov/legislation/status-reports"

        #ssl verification off due Ohio not correctly implementing SSL
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
