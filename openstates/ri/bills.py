import datetime as dt
import lxml.html
import re

from pupa.scrape import Scraper, Bill

from openstates.utils import url_xpath

subjects = None
bill_subjects = None


MAXQUERY = 250  # What a silly low number. This is just putting more load on the
# server, not even helping with that. Sheesh.


def bill_start_numbers(session):
    # differs by first/second session in term
    if int(session) % 2 == 0:
        return {
            "lower": 7000,
            "upper": 2000
        }
    else:
        return {
            "lower": 5000,
            "upper": 1
        }


def get_postable_subjects():
    global subjects
    if subjects is None:
        subs = url_xpath(
            "http://status.rilin.state.ri.us/",
            "//select[@id='rilinContent_cbCategory']"
        )[0].xpath("./*")
        subjects = {o.text: o.attrib['value'] for o in subs}
        subjects.pop(None)
    return subjects


def get_default_headers(page):
    headers = {}
    for el in url_xpath(page, "//*[@name]"):
        name = el.attrib['name']
        value = ""
        try:
            value = el.attrib['value']
        except KeyError:
            value = el.text

        if value:
            value = value.strip()

        headers[name] = value or ""
    headers['__EVENTTARGET'] = ""
    headers['__EVENTARGUMENT'] = ""
    headers['__LASTFOCUS'] = ""
    return headers


SEARCH_URL = "http://status.rilin.state.ri.us/"

BILL_NAME_TRANSLATIONS = {
    "House Bill No.": "HB",
    "Senate Bill No.": "SB",
    "Senate Resolution No.": "SR",
    "House Resolution No.": "HR"
}

BILL_STRING_FLAGS = {
    "bill_id": r"^[House|Senate].*",
    "sponsors": r"^BY.*",
    "title": r"ENTITLED,.*",
    "version": r"\{.*\}",
    "resolution": r"Resolution.*",
    "chapter": r"^Chapter.*",
    "by_request": r"^\(.*\)$",
    "act": r"^Act\ \d*$"
}


class RIBillScraper(Scraper):
    def parse_results_page(self, page):
        blocks = []
        current = []

        p = lxml.html.fromstring(page)
        if "We're Sorry! You seem to be lost." in p.text_content():
            raise ValueError('POSTing has gone wrong')

        nodes = p.xpath("//span[@id='lblBills']/*")
        for node in nodes:
            if node.tag == "br":
                if len(current) > 0:
                    blocks.append(current)
                    current = []
            else:
                current.append(node)
        if current:
            blocks.append(current)
        return blocks

    def digest_results_page(self, nodes):
        blocks = {}
        for node in nodes:
            nblock = {'actions': []}
            lines = [(n.text_content().strip(), n) for n in node]
            if 'No Bills Met this Criteria' in [x[0] for x in lines]:
                self.info("No results. Skipping block")
                return []

            for line in lines:
                line, node = line
                if ('Total Bills:' in line and
                        'State House, Providence, Rhode Island' in line):
                    continue

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

            self.info("Working on %s" % (nblock.get("bill_id")))
            if "bill_id" in nblock:
                blocks[nblock['bill_id']] = nblock
            else:
                self.warning(lines)
                self.warning("ERROR! Can not find bill_id for current entry!")
                self.warning("This should never happen!!! Oh noes!!!")
        return blocks

    def get_subject_bill_dict(self, session):
        global bill_subjects
        if bill_subjects is not None:
            return bill_subjects
        ret = {}
        subjects = get_postable_subjects()
        self.info('getting subjects (total=%s)', len(subjects))
        for subject in subjects:

            default_headers = get_default_headers(SEARCH_URL)

            default_headers['ctl00$rilinContent$cbCategory'] = \
                subjects[subject]
            default_headers['ctl00$rilinContent$cbYear'] = session

            blocks = self.parse_results_page(self.post(SEARCH_URL,
                                             data=default_headers).text)
            blocks = blocks[1:-1]
            blocks = self.digest_results_page(blocks)
            for block in blocks:
                try:
                    ret[block].append(subject)
                except KeyError:
                    ret[block] = [subject]
        bill_subjects = ret
        return bill_subjects

    def process_actions(self, actions, bill):
        for action in actions:
            actor = "legislature"

            if "house" in action.lower():
                actor = "lower"

            if "senate" in action.lower():
                if actor == "joint":
                    actor = "upper"
                else:
                    actor = "legislature"
            if "governor" in action.lower():
                actor = "executive"
            date = action.split(" ")[0]
            date = dt.datetime.strptime(date, "%m/%d/%Y")
            bill.add_action(
                action, date.strftime('%Y-%m-%d'), chamber=actor,
                classification=self.get_type_by_action(action))

    def get_type_by_name(self, name):
        name = name.lower()
        self.info(name)

        things = [
            "resolution",
            "joint resolution"
            "memorial",
            "memorandum",
            "bill"
        ]

        for t in things:
            if t in name:
                self.info("Returning %s" % t)
                return t

        self.warning("XXX: Bill type fallthrough. This ain't great.")
        return "bill"

    def get_type_by_action(self, name):
        types = {
            "introduced": "introduction",
            "referred": "referral-committee",
            "passed": "passage",
            "recommends passage": "committee-passage-favorable",
            # XXX: need to find the unfavorable string
            # XXX: What's "recommended measure be held for further study"?
            "withdrawn": "withdrawal",
            "signed by governor": "executive-signature",
            "transmitted to governor": "executive-receipt"
        }
        ret = []
        name = name.lower()
        for flag in types:
            if flag in name:
                ret.append(types[flag])

        if len(ret) > 0:
            return ret
        return None

    def scrape_bills(self, chamber, session, subjects):
        idex = bill_start_numbers(session)[chamber]
        FROM = "ctl00$rilinContent$txtBillFrom"
        TO = "ctl00$rilinContent$txtBillTo"
        YEAR = "ctl00$rilinContent$cbYear"
        blocks = "FOO"  # Ugh.
        while len(blocks) > 0:
            default_headers = get_default_headers(SEARCH_URL)
            default_headers[FROM] = idex
            default_headers[TO] = idex + MAXQUERY
            default_headers[YEAR] = session
            idex += MAXQUERY
            blocks = self.parse_results_page(self.post(SEARCH_URL,
                                             data=default_headers).text)
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
                    subs = subjects[bill['bill_id']]
                except KeyError:
                    subs = []

                for b in BILL_NAME_TRANSLATIONS:
                    if billid[:len(b)] == b:
                        billid = BILL_NAME_TRANSLATIONS[b] + billid[len(b) + 1:].split()[0]

                b = Bill(
                    billid,
                    title=title,
                    chamber=chamber,
                    legislative_session=session,
                    classification=self.get_type_by_name(bill['bill_id']),
                )
                b.subject = subs

                self.process_actions(bill['actions'], b)
                sponsors = bill['sponsors'][len("BY"):].strip()
                sponsors = sponsors.split(",")
                sponsors = [s.strip() for s in sponsors]

                for href in bill['bill_id_hrefs']:
                    b.add_version_link(
                        href.text, href.attrib['href'],
                        media_type="application/pdf")

                for sponsor in sponsors:
                    b.add_sponsorship(
                        sponsor, entity_type='person', classification='primary', primary=True)

                b.add_source(SEARCH_URL)
                yield b

    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber is not None else ['upper', 'lower']

        subjects = self.get_subject_bill_dict(session)

        for chamber in chambers:
            yield from self.scrape_bills(chamber, session, subjects)
