#!/usr/bin/env python
import urllib
import re
from BeautifulSoup import BeautifulSoup

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.bills import Bill, BillScraper

class NHBillScraper(BillScraper):

    state = 'nh'

    def get_bill_text(self, url):
        regexp = re.compile("href=\"(\S*)\"")
        bill_url = regexp.search(str(url))
        return bill_url.group(1)

    def add_bill_sponsors(self, url):
        regexp = re.compile("href=\"(\S*)\"")
        sponsor_url = regexp.search(str(url))
        sponsor_url = sponsor_url.group(1)

    def scrape(self, chamber, year):
        if year == '2009':
            self.scrape_year(chamber, '2009', '2009-2010')
            self.scrape_year(chamber, '2010', '2009-2010')
        else:
            raise NoDataForPeriod(year)

    def scrape_year(self, chamber, year, session):
        if chamber == 'upper':
            chamber_abbr = 'H'
        elif chamber == 'lower':
            chamber_abbr = 'S'

        #set up POST data
        values = [('txtsessionyear', year),
                  ('txttitle', ''),
                  ('txtlsrnumber', ''),
                  ('Submit1', 'Submit')]
        params = urllib.urlencode(values)
        search_url = 'http://www.gencourt.state.nh.us/bill_status/Results.aspx'

        #request page with list of all bills in year
        with self.urlopen(search_url + '?' + params) as doc:
            soup = BeautifulSoup(doc)

            #parse results
            bills = soup.find("table", {"class": "ptable"})
            trs = soup.findAll("tr")
            #go through all of the table rows with relevant data
            tr_start = 8
            tr_hop = 11
            i = 0

            while (tr_start + (tr_hop * i)) < len(trs):
                tr = trs[tr_start + (tr_hop * i)]
                i = i + 1
                # strip off extra white space from name
                id = tr.find("big").string.strip()
                bill_id = tr.find("big").string.strip()
                exp = re.compile("^(\w*)")
                bill_id = exp.search(id).group(1)

                # check to see if its in the proper chamber
                exp = re.compile("^" + chamber_abbr)
                if exp.search(bill_id) == None:
                    continue  # in wrong house

                # check to see it is a bill and not a resolution
                exp = re.compile("B")
                if exp.search(bill_id) == None:
                    continue  # not a bill

                # get bill_id suffix if exists
                exp = re.compile("(-\w*)$")
                res = exp.search(id)
                if res != None:
                    bill_id = bill_id + res.group(1)

                # get bill title
                title = tr.findAll("b")[0]
                bill_title = title.nextSibling.string
                bill_title = bill_title.strip()
                bill_title = bill_title.encode('ascii', 'xmlcharrefreplace')

                # grab url of bill text
                urls = tr.findAll("a")
                textexp = re.compile("Bill Text")
                textdoc = re.compile("Bill Docket")
                textstat = re.compile("Bill Status")
                textcall = re.compile("Roll Calls")
                textaudio = re.compile("Audio Files")
                for url in urls:
                    if textexp.search(str(url.string)) != None:
                        bill_url = self.get_bill_text(url)
                    if textdoc.search(str(url.string)) != None:
                        pass
                    if textstat.search(str(url.string)) != None:
                        add_bill_sponsors()
                    if textcall.search(str(url.string)) != None:
                        pass
                    if textaudio.search(str(url.string)) != None:
                        pass

                bill = Bill(session, chamber, bill_id, bill_title)
                bill.add_version("Bill text", bill_url)
                bill.add_source(search_url)
                self.save_bill(bill)

                #grabs sponsorship

                #todo: add sponsorship, audio, actions

