import datetime as dt
import lxml.html

from urlparse import urlparse

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

HI_URL_BASE = "http://capitol.hawaii.gov"


def create_bill_report_url( chamber, year ):
    cname = { "upper" : "s", "lower" : "h" }[chamber]
    return HI_URL_BASE + "/report.aspx?type=intro" + cname + "b&year=" + year

class HIBillScraper(BillScraper):
    
    state = 'hi'

    def parse_bill_metainf_table( self, metainf_table ):
        ret = {}
        for tr in metainf_table:
            row = tr.xpath( "td" )

            key   = row[0].text_content().strip()
            value = row[1].text_content().strip()

            if key[-1:] == ":":
                key = key[:-1]

            ret[key] = value
        return ret

    def parse_bill_actions_table( self, action_table ):
        pass

    def scrape_bill( self, url ):
        ret = {
            url : url    
        }
        with self.urlopen(url) as bill_html: 
            bill_page = lxml.html.fromstring(bill_html)
            scraped_bill_name = bill_page.xpath(
                "//a[@id='LinkButtonMeasure']")[0].text_content()
            ret['bill_name'] = scraped_bill_name # for sanity checking
            tables = bill_page.xpath("//table")
            metainf_table = tables[0]
            action_table  = tables[1]

            metainf = self.parse_bill_metainf_table( metainf_table )
            actions = self.parse_bill_actions_table( action_table )
            print metainf, actions

    def scrape_report_page(self, url):
        with self.urlopen(url) as list_html: 
            list_page = lxml.html.fromstring(list_html)
            bills = [ HI_URL_BASE + bill.attrib['href'] for bill in \
                list_page.xpath("//a[@class='report']") ]
            for bill in bills:
                self.scrape_bill( bill )

    def scrape(self, chamber, session):
        session_urlslug = \
            self.metadata['session_details'][session]['_scraped_name']
        print self.scrape_report_page( \
            create_bill_report_url( chamber, session_urlslug ) )
