import datetime as dt
import lxml.html
import urllib
import re

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

BILL_NAME_TRANSLATIONS = {
    "House Bill No."  : "HB",
    "Senate Bill No." : "SB",
    "Senate Resolution No." : "SR",
    "House Resolution No."  : "HR"
}

BILL_STRING_FLAGS = {
    "bill_id"    : r"^[House|Senate].*",
    "sponsors"   : r"^BY.*",
    "title"      : r"ENTITLED,.*",
    "version"    : r"\{.*\}",
    "resolution" : r"Resolution.*",
    "chapter"    : r"^Chapter.*",
    "by_request" : r"^\(.*\)$",
    "act"        : r"^Act\ \d*$"
}

class RIBillScraper(BillScraper):
    jurisdiction = 'ri'

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
        blocks = {}
        for node in nodes:
            nblock = { 'actions' : [] }
            lines = [ ( n.text_content(), n ) for n in node ]
            for line in lines:
                line, node = line
                found = False
                for regexp in BILL_STRING_FLAGS:
                    if re.match(BILL_STRING_FLAGS[regexp], line):
                        hrefs = node.xpath("./a")
                        if len(hrefs) > 0:
                             nblock[regexp + "_hrefs"] = hrefs
                        nblock[regexp] = line
                        found = True
                if not found:
                    nblock['actions'].append(line)
            if "bill_id" in nblock:
                blocks[nblock['bill_id']] = nblock
            else:
                self.warning("ERROR! Can not find bill_id for current entry!")
                self.warning("This should never happen!!! Oh noes!!!")
        return blocks

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

            #headers = urllib.urlencode( default_headers )
            blocks = self.parse_results_page(self.urlopen( SEARCH_URL,
                method="POST", body=default_headers))
            blocks = blocks[1:-1]
            blocks = self.digest_results_page(blocks)
            for block in blocks:
                try:
                    ret[block].append(subject)
                except KeyError:
                    ret[block] = [ subject ]
        bill_subjects = ret
        return bill_subjects

    def process_actions( self, actions, bill ):
        for action in actions:
            actor = "joint"

            if "house"  in action.lower():
                actor = "lower"

            if "senate" in action.lower():
                if actor == "joint":
                    actor = "upper"
                else:
                    actor = "joint"
            if "governor" in action.lower():
                actor = "governor"
            date = action.split(" ")[0]
            date = dt.datetime.strptime(date, "%m/%d/%Y")
            bill.add_action( actor, action, date,
                type=self.get_type_by_action(action))

    def get_type_by_name(self, name):
        name = name.lower()
        self.log(name)

        things = [
            "resolution",
            "joint resolution"
            "memorial",
            "memorandum",
            "bill"
        ]

        for t in things:
            if t in name:
                self.log( "Returning %s" % t )
                return t

        self.warning("XXX: Bill type fallthrough. This ain't great.")
        return "bill"

    def get_type_by_action(self, name):
        types = {
            "introduced" : "bill:introduced",
            "referred"   : "committee:referred",
            "passed"     : "bill:passed",
            "recommends passage" : "committee:passed:favorable",
            # XXX: need to find the unfavorable string
            # XXX: What's "recommended measure be held for further study"?
            "withdrawn"               : "bill:withdrawn",
            "signed by governor"      : "governor:signed",
            "transmitted to governor" : "governor:received"
        }
        ret = []
        name = name.lower()
        for flag in types:
            if flag in name:
                ret.append(types[flag])

        if len(ret) > 0:
            return ret
        return "other"

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
            #headers = urllib.urlencode( default_headers )
            blocks = self.parse_results_page(self.urlopen( SEARCH_URL,
                method="POST", body=default_headers))
            blocks = blocks[1:-1]
            blocks = self.digest_results_page(blocks)

            for block in blocks:
                bill = blocks[block]
                subs = []
                try:
                    subs = subjects[bill['bill_id']]
                except KeyError:
                    pass

                title = bill['title'][len("ENTITLED, "):]
                billid = bill['bill_id']
                try:
                    subs   = subjects[bill['bill_id']]
                except KeyError:
                    subs   = []

                for b in BILL_NAME_TRANSLATIONS:
                    if billid[:len(b)] == b:
                        billid = BILL_NAME_TRANSLATIONS[b] + \
                            billid[len(b)+1:].split()[0]
                b = Bill(session, chamber, billid, title,
                    type=self.get_type_by_name(bill['bill_id']),
                    subjects=subs
                )

                self.process_actions( bill['actions'], b )
                sponsors = bill['sponsors'][len("BY"):].strip()
                sponsors = sponsors.split(",")
                sponsors = [ s.strip() for s in sponsors ]

                for href in bill['bill_id_hrefs']:
                    b.add_version( href.text, href.attrib['href'],
                        mimetype="application/pdf" )

                for sponsor in sponsors:
                    b.add_sponsor("primary", sponsor)

                b.add_source( SEARCH_URL )
                self.save_bill(b)
                # print bill['bill_id'], subs

    def scrape(self, chamber, session):
        subjects = self.get_subject_bill_dict()
        self.scrape_bills( chamber, session, subjects )
