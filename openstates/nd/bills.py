import datetime
import re
import lxml.html
from billy.scrape import NoDataForPeriod, ScrapeError
from billy.scrape.bills import Bill, BillScraper

class NDBillScraper(BillScraper):
    """
    Scrapes available legislative information from the website of the North
    Dakota legislature and stores it in the fiftystates backend.
    """
    state = 'nd'
    site_root = 'http://www.legis.nd.gov'

    def scrape(self, chamber, session):
        # URL building
        if chamber == 'upper':
            url_chamber_name = 'senate'
            norm_chamber_name = 'Senate'
        else:
            url_chamber_name = 'house'
            norm_chamber_name = 'House'

        assembly_url = '/assembly/%s' % session

        chamber_url = '/bill-text/%s-bill.html' % (url_chamber_name)

        bill_list_url = self.site_root + assembly_url + chamber_url

        with self.urlopen(bill_list_url) as html:
            list_page = lxml.html.fromstring(html)
            # connects bill_id with bill details page
            bills_url_dict = {}
            #connects bill id with bills to be accessed later.
            bills_id_dict = {}
            title = ''
            for bills in list_page.xpath('/html/body/table[3]/tr/th/a'):
                bill_id = bills.text
                bill_url = bill_list_url[0: -26] + '/' + bills.attrib['href'][2:len(bills.attrib['href'])]
                bill = Bill(session, chamber, bill_id, title)
                bills_url_dict[bill_id] = bill_url
                bills_id_dict[bill_id] = bill

            for bill_keys in bills_url_dict.keys():
                url = bills_url_dict[bill_keys]
                curr_bill = bills_id_dict[bill_keys]
                with self.urlopen(url) as bill_html:
                    bill_page = lxml.html.fromstring(bill_html)
                    for bill_info in bill_page.xpath('/html/body/table[4]/tr/td'):
                        info = bill_info.text

                        #Sponsors
                        if "Introduced" in info:
                            if ('Rep' in info) or ('Sen' in info):
                                rep = info[14: 17]
                                info = info[18: len(info)]
                                sponsors = info.split(',')
                            else:
                                sponsors = info[13: len(info)]
                                rep = ''
                            for sponsor in sponsors:
                                if sponsor == sponsors[0]:
                                    sponsor_type = 'primary'
                                else:
                                    sponsor_type = 'cosponsor'
                                curr_bill.add_sponsor(sponsor_type, rep + sponsor)
                        else:
                            #title
                            title = info.strip()
                            curr_bill["title"] = title
                self.save_bill(curr_bill)
