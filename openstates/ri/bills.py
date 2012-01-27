import datetime as dt
import lxml.html

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.utils import url_xpath

def get_postable_subjects():
    return url_xpath( "http://status.rilin.state.ri.us/",
        "//select[@id='rilinContent_cbCategory']" )[0].xpath("./*")

subjects = { o.text : o.attrib['value'] for o in get_postable_subjects() }
subjects.pop(None)

class RIBillScraper(BillScraper):
    state = 'ri'

    def scrape(self, chamber, session):
        print subjects
