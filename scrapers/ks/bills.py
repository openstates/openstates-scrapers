import re
import dateutil.parser
import lxml.html
from openstates.scrape import Scraper, Bill

BASE_URL = "https://www.kslegislature.gov"

ACTION_CLASSIFIERS = [
    (r"Prefiled", "filing"),
    (r"Introduced", "introduction"),
    (r"Received and Introduced", "introduction"),
    (r"Referred to.*Committee", "referral-committee"),
    (r"Rereferred to.*Committee", "referral-committee"),
    (r"Committee Report recommending.*passed as amended", "committee-passage-favorable"),
    (r"Committee Report recommending.*be passed", "committee-passage-favorable"),
    (r"Committee Report recommending.*favorable", "committee-passage-favorable"),
    (r"Committee Report recommending.*without recommendation", "committee-passage-unfavorable"),
    (r"Committee Report recommending.*unfavorable", "committee-passage-unfavorable"),
    (r"Committee Report.*reported out", "committee-passage"),
    (r"Committee of the Whole.*Be passed", "passage"),
    (r"Committee of the Whole.*Adopted", "passage"),
    (r"Emergency Final Action.*Passed", "passage"),
    (r"Emergency Final Action.*Failed", "failure"),
    (r"Final Action.*Passed", "passage"),
    (r"Final Action.*Failed", "failure"),
    (r"Approved by Governor", "executive-signature"),
    (r"Vetoed by Governor", "executive-veto"),
    (r"Governor.*signed", "executive-signature"),
    (r"Line Item Veto", "executive-veto-line-item"),
    (r"Veto Override.*Passed", "veto-override-passage"),
    (r"Veto Override.*Failed", "veto-override-failure"),
    (r"Died", "failure"),
]


def _clean_sponsor_name(name):
    name = name.strip()
    for prefix in ("Sen. ", "Rep. ", "Senator ", "Representative "):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    for prefix in ("Senate Committee", "House Committee"):
        if name.startswith(prefix):
            name = "Committee" + name[len("Senate Committee"):]
            break
    return name.strip()


def _classify_action(action_text):
    for pattern, atype in ACTION_CLASSIFIERS:
        if re.search(pattern, action_text, re.IGNORECASE):
            return atype
    return None


class KSBillScraper(Scraper):

    def scrape(self, session=None):
        yield from self.scrape_bill_list(session)

    def scrape_bill_list(self, session):
        page = 1
        while True:
            url = (
                f"{BASE_URL}/measures/fragment/"
                f"?per_page=10&types=bill&types=resolution"
                f"&chambers=House&chambers=Senate"
                f"&sort=number&dir=asc&page={page}"
            )
            resp = self.get(url)
            doc = lxml.html.fromstring(resp.text)

            bill_rows = doc.xpath('//tr[@data-href]')
            if not bill_rows:
                break

            for row in bill_rows:
                href = row.get("data-href", "")
                # Skip appointments: /senate/appointments/... or /house/appointments/...
                if "appointments" in href:
                    continue
                if href:
                    yield from self.scrape_bill(session, href)

            if not doc.xpath(f'//a[contains(@hx-get, "page={page + 1}") or contains(@href, "page={page + 1}")]'):
                break
            page += 1

    def scrape_bill(self, session, href):
        # href like "/bills/SB1/" or "/resolutions/SCR1601/"
        bill_id = href.strip("/").split("/")[-1]
        bill_url = BASE_URL + href
        resp = self.get(bill_url)
        doc = lxml.html.fromstring(resp.text)

        title_els = doc.xpath('//p[@class="bill-hero-sub"]/text()')
        title = title_els[0].strip() if title_els else bill_id

        badge_els = doc.xpath('//span[@class="bill-chamber-badge"]/text()')
        badge = badge_els[0].strip() if badge_els else ""
        chamber = "upper" if "SENATE" in badge.upper() else "lower"

        badge_lower = badge.lower()
        if "concurrent resolution" in badge_lower:
            btype = "concurrent resolution"
        elif "resolution" in badge_lower:
            btype = "resolution"
        elif "bill" in badge_lower:
            btype = "bill"
        else:
            btype = "bill"

        bill = Bill(bill_id, session, title, chamber=chamber, classification=btype)
        bill.add_source(bill_url)

        for subject_text in doc.xpath('//a[@class="bill-subject-tag"]/text()'):
            bill.add_subject(subject_text.strip())

        self._parse_sponsors(doc, bill)
        self._parse_versions(doc, bill)

        history_url = BASE_URL + href.rstrip("/") + "/history/?per_page=500"
        history_resp = self.get(history_url)
        history_doc = lxml.html.fromstring(history_resp.text)
        self._parse_actions(history_doc, bill)

        yield bill

    def _parse_sponsors(self, doc, bill):
        bill_section = doc.xpath('//div[@class="bill-section"]')
        if not bill_section:
            return
        section = bill_section[0]

        primary_names = set()
        for h3 in section.xpath('.//h3'):
            heading = h3.text_content().strip()
            if heading in ("Original Sponsor", "Original Sponsors"):
                primary = True
                classification = "primary"
            elif heading in ("Current Sponsor", "Current Sponsors"):
                primary = False
                classification = "cosponsor"
            else:
                continue

            # Sponsors are in multiple sibling detail-rows after the h3
            for sibling in h3.itersiblings():
                if sibling.tag == "h3":
                    break
                for link in sibling.xpath('.//a'):
                    name = _clean_sponsor_name(link.text_content())
                    if not name:
                        continue
                    if not primary and name in primary_names:
                        continue
                    entity_type = "organization" if "committee" in name.lower() else "person"
                    bill.add_sponsorship(
                        name=name,
                        entity_type=entity_type,
                        primary=primary,
                        classification=classification,
                    )
                    if primary:
                        primary_names.add(name)

    def _parse_versions(self, doc, bill):
        for version_row in doc.xpath('//details[@class="version-row"]'):
            label_els = version_row.xpath('.//summary/span[@class="label"]/text()')
            if not label_els:
                continue
            label = label_els[0].strip()

            pdf_links = version_row.xpath('.//a[@class="version-pdf-link"]')
            for link in pdf_links:
                href = link.get("href", "")
                if not href:
                    continue
                full_url = BASE_URL + href if href.startswith("/") else href
                aria = link.get("aria-label", "")

                if aria == "Download PDF":
                    bill.add_version_link(label, full_url, media_type="application/pdf")
                else:
                    doc_name = aria.replace(" (PDF)", "").strip()
                    doc_label = f"{label} {doc_name}" if doc_name else label
                    bill.add_document_link(doc_label, full_url, media_type="application/pdf")

    def _parse_actions(self, doc, bill):
        for row in doc.xpath('//tr[contains(@class,"history-row")]'):
            date_tds = row.xpath('.//td[@data-label="Date"]/text()')
            if not date_tds:
                continue
            date_str = date_tds[0].strip()
            try:
                date = dateutil.parser.parse(date_str).strftime("%Y-%m-%d")
            except Exception:
                continue

            chamber_els = row.xpath('.//span[contains(@class,"history-chamber")]/text()')
            chamber_text = chamber_els[0].strip() if chamber_els else ""
            actor = "upper" if chamber_text == "Senate" else "lower"

            msg_els = row.xpath('.//td[@class="col-primary"]')
            if not msg_els:
                continue
            action = re.sub(r"\s+", " ", msg_els[0].text_content().strip())

            atype = _classify_action(action)
            bill.add_action(action, date, chamber=actor, classification=atype)
