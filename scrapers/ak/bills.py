import re
import datetime

import lxml.html

from openstates.scrape import Scraper, Bill, VoteEvent
from . import actions

SPONSOR_CHAMBER_MAP = {
    "REPRESENTATIVE": "lower",
    "SENATOR": "upper",
}


class AKBillScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        bill_types = {
            "B": "bill",
            "R": "resolution",
            "JR": "joint resolution",
            "J": "bill",  # joint bill
            "CR": "concurrent resolution",
            "SC": "concurrent resolution",
            "SCR": "concurrent resolution",
        }

        bill_list_url = f"https://www.akleg.gov/basis/Bill/Range/{session}"
        doc = lxml.html.fromstring(self.get(bill_list_url).text)
        doc.make_links_absolute(bill_list_url)

        conference_committee_list_url = (
            f"https://www.akleg.gov/basis/Committee/List/{session}#tabCom5"
        )
        conference_committee_doc = lxml.html.fromstring(
            self.get(conference_committee_list_url).text
        )
        conference_committee_bills_list = []
        for link in conference_committee_doc.xpath(
            '//a[contains(@href, "/basis/Committee/Details/")]'
        ):
            name = link.text_content()
            if "CONFERENCE COMMITTEE" in str(name):
                bill_id = re.sub(
                    r"^.*\((.*?)\)[^\(]*$", r"\g<1>", name
                )  # Search for the content between the last set of brackets
                conference_committee_bills_list.append(bill_id)

        for bill_link in doc.xpath("//tr//td[1]//nobr[1]//a[1]"):
            bill_abbr = bill_link.text
            if " " in bill_abbr:
                bill_abbr = bill_abbr.split(" ")[0]
            elif "HCR" in bill_abbr or "SCR" in bill_abbr:
                bill_abbr = bill_abbr[:3]
            else:
                bill_abbr = bill_abbr[:2]
            bill_id = bill_link.text.replace(" ", "")
            bill_type = bill_types[bill_abbr[1:]]
            bill_url = bill_link.get("href").replace(" ", "")
            if bill_abbr in ["SB", "SR", "SCR", "SJR"]:
                chamber = "upper"
            else:
                chamber = "lower"

            if bill_id in conference_committee_bills_list:
                conference_committee = True
            else:
                conference_committee = False

            yield from self.scrape_bill(
                chamber, session, bill_id, bill_type, bill_url, conference_committee
            )

    def scrape_bill(
        self, chamber, session, bill_id, bill_type, url, conference_committee
    ):
        doc = lxml.html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)

        title = doc.xpath('//span[text()="Title"]')[0].getparent()
        short_title = doc.xpath('//span[text()="Short Title "]')[0].getparent()

        if len(title) > 1 and title[1].text:
            title = title[1].text.strip().strip('"')
        elif len(short_title) > 1 and short_title[1].text:
            self.warning("Falling back to short title on {}".format(url))
            title = short_title[1].text.strip().strip('"')
        else:
            self.warning("skipping bill {}, no Title".format(url))
            return

        bill = Bill(
            bill_id,
            title=title,
            chamber=chamber,
            classification=bill_type,
            legislative_session=session,
        )
        bill.add_source(url)

        # Get sponsors
        spons_str = "".join(
            doc.xpath('//span[contains(text(), "Sponsor(S)")]/../strong//text()')
        ).strip()
        # Checks if there is a Sponsor string before matching
        if spons_str:
            sponsors_matches = re.finditer(
                r"(?P<sponsor_type>REPRESENTATIVE|SENATOR)S?\s+(?P<sponsors>.*)",
                spons_str,
            )

            sponsors_cnt = 0

            for sponsors_match in sponsors_matches:
                sponsors_cnt += 1
                sponsors_data = sponsors_match.groupdict()

                sponsor_type = sponsors_data["sponsor_type"]
                sponsors = sponsors_data["sponsors"].split(",")

                sponsor_chamber = SPONSOR_CHAMBER_MAP.get(sponsor_type, "")

                for sponsor in sponsors:
                    primary = sponsor == sponsor.upper()
                    sponsor = sponsor.upper().split("BY REQUEST")[0].title().strip()
                    # occasional AK site error prints some code here
                    if "Model.Sponsors." in sponsor:
                        continue
                    if sponsor:
                        bill.add_sponsorship(
                            sponsor,
                            chamber=sponsor_chamber,
                            entity_type="person",
                            classification="primary" if primary else "cosponsor",
                            primary=primary,
                        )

            if sponsors_cnt == 0:
                # Committee sponsorship
                spons_str = spons_str.upper().split("BY REQUEST")[0].title().strip()

                if spons_str:
                    sponsor_chamber = ""
                    if "Senate" in spons_str:
                        sponsor_chamber = "upper"
                    elif "House" in spons_str:
                        sponsor_chamber = "lower"

                    bill.add_sponsorship(
                        spons_str,
                        chamber=sponsor_chamber,
                        entity_type="organization",
                        classification="primary",
                        primary=True,
                    )

        # Get actions
        actions._current_comm = None
        act_rows = doc.xpath("//div[@id='tab6_4']//tr")[1:]
        for row in act_rows:
            date, journal, action = row.xpath("td")
            action = action.text_content().strip()
            raw_chamber = action[0:3]
            journal_entry_number = journal.text_content()
            act_date = datetime.datetime.strptime(
                date.text_content().strip(), "%m/%d/%Y"
            )
            if raw_chamber == "(H)":
                act_chamber = "lower"
            elif raw_chamber == "(S)":
                act_chamber = "upper"

            # Votes
            if re.search(r"Y(\d+)", action):
                vote_href = journal.xpath(".//a/@href")
                if vote_href:
                    vote_href = vote_href[0].replace(" ", "")
                    yield from self.parse_vote(
                        bill,
                        journal_entry_number,
                        action,
                        act_chamber,
                        act_date,
                        vote_href,
                    )

            action, atype = actions.clean_action(action)

            match = re.search(r"^Prefile released (\d+/\d+/\d+)$", action)
            if match:
                action = "Prefile released"
                act_date = datetime.datetime.strptime(match.group(1), "%m/%d/%y")

            bill.add_action(
                action,
                chamber=act_chamber,
                date=act_date.strftime("%Y-%m-%d"),
                classification=atype,
            )

        # Get subjects
        for subj in doc.xpath('//a[contains(@href, "subject")]/text()'):
            bill.add_subject(subj.strip())

        for version_row in doc.xpath("//tr[td[@data-label='Version']]"):
            html_url = version_row.xpath("td[@data-label='Version']/span/a/@href")[0]
            version_name = version_row.xpath("td[@data-label='Amended Name']")[
                0
            ].text_content()
            bill.add_version_link(version_name, html_url, media_type="text/html")

            if version_row.xpath("td[@data-label='PDF']/span/a/@href"):
                pdf_url = version_row.xpath("td[@data-label='PDF']/span/a/@href")[0]
                bill.add_version_link(
                    version_name, pdf_url, media_type="application/pdf"
                )

        # Get documents - to do
        doc_list_url = (
            f"https://www.akleg.gov/basis/Bill/Detail/{session}?Root={bill_id}#tab5_4"
        )
        doc_list = lxml.html.fromstring(self.get(doc_list_url).text)
        doc_list.make_links_absolute(doc_list_url)
        bill.add_source(doc_list_url)
        seen = set()
        for href in doc_list.xpath('//a[contains(@href, "get_documents")][@onclick]'):
            h_name = str(href.text_content()).replace(".pdf", "")
            doc_link_url = href.attrib["href"]
            if h_name.strip() and doc_link_url not in seen:
                bill.add_document_link(note=h_name, url=doc_link_url, media_type="pdf")
                seen.add(doc_link_url)

        if conference_committee:
            conferees_house_doc_link_url = "https://www.akleg.gov/basis/Committee/Details/{0}?code=H{1}#tab1_7".format(
                session, bill_id
            )
            bill.add_document_link(
                note="Conference Committee Members (House)",
                url=conferees_house_doc_link_url,
                media_type="text/html",
            )
            conferees_senate_doc_link_url = "https://www.akleg.gov/basis/Committee/Details/{0}?code=S{1}#tab1_7".format(
                session, bill_id
            )
            bill.add_document_link(
                note="Conference Committee Members (Senate)",
                url=conferees_senate_doc_link_url,
                media_type="text/html",
            )

        yield bill

    def parse_vote(
        self, bill, journal_entry_number, action, act_chamber, act_date, url
    ):
        # html = self.get(url).text
        # doc = lxml.html.fromstring(html)
        yes = no = other = 0
        result = ""
        vote_counts = action.split()
        for vote_count in vote_counts:
            if re.match(r"[\D][\d]", vote_count):
                if "Y" in vote_count:
                    yes = int(vote_count[1:])
                elif "N" in vote_count:
                    no = int(vote_count[1:])
                elif "E" in vote_count or "A" in vote_count:
                    other += int(vote_count[1:])

        if "PASSED" in action:
            result = "pass"
        elif "FAILED" in action:
            result = "fail"
        else:
            result = "pass" if yes > no else "fail"

        vote = VoteEvent(
            bill=bill,
            start_date=act_date.strftime("%Y-%m-%d"),
            chamber=act_chamber,
            motion_text=action + " #" + journal_entry_number,
            result=result,
            classification="passage",
        )

        vote.set_count("yes", yes)
        vote.set_count("no", no)
        vote.set_count("other", other)
        vote.add_source(url)

        yield vote
