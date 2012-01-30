import datetime as dt
import lxml.html
import urllib

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.utils import url_xpath

subjects      = None
bill_subjects = None

HB_START_BILLNO=7000
SB_START_BILLNO=2000

START_IDEX = {
    "lower" : HB_START_BILLNO,
    "upper" : SB_START_BILLNO
}

MAXQUERY=250 # What a silly low number. This is just putting more load on the
# server, not even helping with that. Sheesh.

def get_postable_subjects():
    global subjects
    if subjects == None:
        subs = url_xpath( "http://status.rilin.state.ri.us/",
            "//select[@id='rilinContent_cbCategory']" )[0].xpath("./*")
        subjects = { o.text : o.attrib['value'] for o in subs }
        subjects.pop(None)
    return subjects

def get_default_headers( page ):
    headers = {}
    for el in url_xpath( page, "//*[@name]" ):
        name = el.attrib['name']
        value = ""
        try:
            value = el.attrib['value']
        except KeyError:
            value = el.text
        headers[name] = value or ""
    return headers

SEARCH_URL = "http://status.rilin.state.ri.us/"

class RIBillScraper(BillScraper):
    state = 'ri'

    def parse_results_page( self, page ):
        blocks  = []
        current = []

        p = lxml.html.fromstring(page)
        nodes = p.xpath("//span[@id='lblBills']/*")
        for node in nodes:
            if node.tag == "br":
                if len(current) > 0:
                    current = []
                    blocks.append(current)
            else:
                current.append(node)
        return blocks

    def digest_results_page( self, nodes ):

        headers = [
            "bill_id",
            "sponsors",
            "title",
            "docid"
        ]

        ret = {}

        for node in nodes:
            idex = -1
            actions = []
            nret = {
                "actions" : actions    
            }

            for div in node:
                idex += 1
                try:
                    nret[headers[idex]] = div.text_content()
                    hrefs = div.xpath("./a")
                    if len(hrefs) > 0:
                        nret[headers[idex] + "_href"] = hrefs
                except IndexError:
                    actions.append(div.text_content())
            ret[nret["bill_id"]] = nret
        return ret

    def get_subject_bill_dict(self):
        global bill_subjects
        if bill_subjects != None:
            return bill_subjects
        ret = {}
        subjects = get_postable_subjects()
        for subject in subjects:
            default_headers = get_default_headers( SEARCH_URL )

            default_headers['ctl00$rilinContent$cbCategory'] = \
                subjects[subject]

            default_headers['ctl00$rilinContent$cbYear'] = \
                "2012" # XXX: Fixme

            headers = urllib.urlencode( default_headers )
            blocks = self.parse_results_page(self.urlopen( SEARCH_URL,
                method="POST", body=headers))
            blocks = blocks[1:-1]
            ret[subject] = self.digest_results_page(blocks)
        bill_subjects = ret
        return bill_subjects

    def scrape_bills(self, chamber, session, subjects):
        idex = START_IDEX[chamber]
        FROM="ctl00$rilinContent$txtBillFrom"
        TO="ctl00$rilinContent$txtBillTo"
        YEAR="ctl00$rilinContent$cbYear"


        blocks = "FOO" # Ugh.

        while len(blocks) > 0:
            default_headers = get_default_headers( SEARCH_URL )
            default_headers[FROM] = idex
            default_headers[TO]   = idex + MAXQUERY
            default_headers[YEAR] = session

            idex += MAXQUERY

            headers = urllib.urlencode( default_headers )
            blocks = self.parse_results_page(self.urlopen( SEARCH_URL,
                method="POST", body=headers))
            blocks = blocks[1:-1]
            print self.digest_results_page(blocks)

    def scrape(self, chamber, session):
        # subjects = self.get_subject_bill_dict()
        self.scrape_bills( chamber, session, subjects )
