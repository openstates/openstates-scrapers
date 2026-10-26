import re
import datetime
import pytz

import lxml.html
from openstates.scrape import Scraper, Bill

# http://mgaleg.maryland.gov/mgawebsite/Legislation/Details/hb0060?ys=2019RS&search=True
# # passed all

# search for tax
# http://mgaleg.maryland.gov/mgawebsite/Search/FullText?category=legislation-documents-legislation-bills-and-resolutions&dropXSL=no&isadvanced=&rpp=500&pr=mgasearch&query=tax&order=r&af1like=2019rs&notq=#full-text-search-results-complete

classifiers = {
    r"Committee Amendment .+? Adopted": "amendment-passage",
    r"Favorable": "committee-passage-favorable",
    r"First Reading": "referral-committee",
    r"Floor (Committee )?Amendment\s?\(.+?\)$": "amendment-introduction",
    r"Floor Amendment .+? Rejected": "amendment-failure",
    r"Floor (Committee )?Amendment.+?Adopted": "amendment-passage",
    r"Floor Amendment.+? Withdrawn": "amendment-withdrawal",
    r"Pre\-filed": "introduction",
    r"Withdrawn": "withdrawal",
    r"Re\-(referred|assigned)": "referral-committee",
    r"Recommit to Committee": "referral-committee",
    r"Referred": "referral-committee",
    r"Third Reading Passed": "passage",
    r"Third Reading Failed": "failure",
    r"Unfavorable": "committee-passage-unfavorable",
    r"Vetoed": "executive-veto",
    r"Gubernatorial Veto Override": "veto-override-passage",
    r"Veto overridden": "veto-override-passage",
    r"Overridden": "veto-override-passage",
    r"Approved by the Governor": "executive-signature",
    r"Enacted under Article II": "became-law",
    r"Became law": "became-law",
}


def _classify_action(action):
    if not action:
        return None

    ctty = None

    for regex, type in classifiers.items():
        if re.match(regex, action):
            if "referral-committee" in type:
                ctty = re.sub(regex, "", action).strip()
            return (type, ctty)
    return (None, ctty)


class MDBillScraper(Scraper):
    _TZ = pytz.timezone("US/Eastern")
    BASE_URL = "http://mgaleg.maryland.gov/mgawebsite/"
    CHAMBERS = {"upper": "senate", "lower": "house"}

    def scrape_bill_actions(self, bill, page):
        chamber_map = {"Senate": "upper", "House": "lower", "Post Passage": "executive"}
        for row in page.xpath('//table[@id="detailsHistory"]/tbody/tr'):
            # actions have something in the first column
            potential_chamber = row.xpath("td[1]/text()")
            if len(potential_chamber) > 0:
                chamber = chamber_map[potential_chamber[0].strip()]
                action_date = row.xpath("td[2]/text()")[0].strip()
                # self._TZ.localize(
                action_date = datetime.datetime.strptime(action_date, "%m/%d/%Y")
                action_text = row.xpath("td[4]/text()")[0].strip()
                atype, committee = _classify_action(action_text)
                action = bill.add_action(
                    action_text,
                    action_date.strftime("%Y-%m-%d"),
                    chamber=chamber,
                    classification=atype,
                )
                if committee:
                    action.add_related_entity(committee, "organization")
            elif row.xpath("td[4]/a"):
                link = row.xpath("td[4]/a")[0]
                link_text = link.text_content().strip()
                if link_text.startswith("Text"):
                    link_text = link_text.replace("Text - ", "")
                    bill.add_version_link(
                        link_text,
                        link.get("href"),
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )

    def scrape_bill_subjects(self, bill, page):
        # TODO: this xpath gets both 'subjects' and 'file codes'
        # they both link to subjects on the site and seem to fit the definition of subject
        for row in page.xpath(
            '//a[contains(@href, "/Legislation/SubjectIndex/annotac")]/text()'
        ):
            bill.add_subject(row[0])

    def scrape_bill_sponsors(self, bill, page):
        sponsors_title = "".join(
            page.xpath(
                '//dt[contains(text(), "Sponsored by")]/following-sibling::dd[1]/text()'
            )
        )
        if "Delegate" in sponsors_title:
            chamber = "lower"
        elif "Senator" in sponsors_title:
            chamber = "upper"
        else:
            chamber = None

        sponsors = page.xpath(
            '//dt[contains(text(), "Sponsored by")]/following-sibling::dd[1]/a'
        )
        sponsor_type = "primary"

        for sponsor in sponsors:
            sponsor = sponsor.text.strip()
            entity_type = "organization" if "Committee" in sponsor else "person"
            if not sponsor:
                continue
            if sponsor == "Departmental":
                # there seems to be meta information about the requestor, but that
                # doesn't really fit our definition of sponsor.  once we get to this
                # sponsor the list is done
                # (e.g. http://mgaleg.maryland.gov/mgawebsite/Legislation/Details/sb0125?ys=2021RS)
                break
            if chamber:
                bill.add_sponsorship(
                    sponsor,
                    sponsor_type,
                    primary=sponsor_type == "primary",
                    entity_type=entity_type,
                    chamber=chamber,
                )
            else:
                bill.add_sponsorship(
                    sponsor,
                    sponsor_type,
                    primary=sponsor_type == "primary",
                    entity_type=entity_type,
                )

    def scrape_bill(self, chamber, session, url):
        html = self.get(url).content
        page = lxml.html.fromstring(html)
        page.make_links_absolute(self.BASE_URL)

        if page.xpath('//h2[@style="font-size:1.3rem;"]/a[1]/text()'):
            bill_id = page.xpath('//h2[@style="font-size:1.3rem;"]/a[1]/text()')[
                0
            ].strip()
        elif page.xpath('//h2[@style="font-size:1.3rem;"]/text()'):
            bill_id = page.xpath('//h2[@style="font-size:1.3rem;"]/text()')[0].strip()
        else:
            self.warning("No bill id for {}".format(url))
            return
        title = page.xpath(
            '//dt[contains(text(), "Title")]/following-sibling::dd[1]/text()'
        )[0].strip()

        if "OIS Test" in title:
            self.warning(f"Ignoring test bill {bill_id} - {title}")
            return

        if "B" in bill_id:
            _type = ["bill"]
        elif "J" in bill_id:
            _type = ["joint resolution"]
        elif "HS" in bill_id or "SS" in bill_id:
            _type = ["resolution"]
        else:
            raise ValueError("unknown bill type " + bill_id)

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=_type,
        )
        bill.add_source(url)

        self.scrape_bill_subjects(bill, page)
        self.scrape_bill_sponsors(bill, page)
        self.scrape_bill_actions(bill, page)

        # fiscal note
        if page.xpath('//dt[contains(text(), "Analysis")]/following-sibling::dd[1]/a'):
            fiscal_note = page.xpath(
                '//dt[contains(text(), "Analysis")]/following-sibling::dd[1]/a'
            )[0]
            fiscal_url = fiscal_note.get("href")
            fiscal_title = fiscal_note.text_content()
            bill.add_document_link(
                fiscal_title, fiscal_url, media_type="application/pdf"
            )

        # effective date, where available
        if page.xpath('//div[contains(text(), "Effective Date(s)")]'):
            eff_date = page.xpath(
                '//div[contains(text(), "Effective Date(s)")]/text()'
            )[0].strip()
            eff_date = eff_date.replace("Effective Date(s):", "").strip()
            # this can contain multiple dates, eg "July 1, 2020, July 1, 2022"
            bill.extras["date_effective"] = eff_date

        # companion bills
        companion_link = page.xpath("//div[contains(.,'Cross-filed')]/a")
        if companion_link:
            # get the bill from the text of the link
            bill.add_related_bill(
                companion_link[0].xpath("text()")[0],
                legislative_session=session,
                relation_type="companion",
            )

        # previous session version of the bill
        prev_div = page.xpath("//div[contains(text(),'Introduced in a prior session')]")
        if prev_div:
            # Get the session from the text following "Session:"
            prev_div = prev_div[0]
            prev_div_text = prev_div.xpath("text()")[1]
            prev_session = re.search(r"Session\:\s(.*)", prev_div_text).group(1)
            # Get the bill from the text of the link
            prev_bill = prev_div.xpath("a/text()")[0]
            bill.add_related_bill(
                prev_bill,
                legislative_session=prev_session,
                relation_type="prior-session",
            )

        yield bill

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        session_slug = session if "s" in session else session + "RS"

        list_url = (
            "http://mgaleg.maryland.gov/mgawebsite/Legislation/Index/{}?ys={}".format(
                self.CHAMBERS[chamber], session_slug
            )
        )

        list_html = self.get(list_url).content
        page = lxml.html.fromstring(list_html)
        page.make_links_absolute(self.BASE_URL)

        # despite only showing one page to the browser,
        # all the bills are conveniently in the markup
        for row in page.xpath('//table[@id="billIndex"]/tbody/tr'):
            url = row.xpath("td[1]/a[1]/@href")[0]
            yield from self.scrape_bill(chamber, session, url)
