import re
import datetime

import lxml.html

from openstates.scrape import Scraper, VoteEvent


SESSION_SOURCE_IDS = {
    "2019-2020": "249",
    "2020s1": "252",
    "2020s2": "253",
    "2020s3": "254",
    "2020s4": "255",
    "2020s5": "256",
    "2020s6": "258",
    "2020s7": "259",
    "2021-2022": "257",
    "2023-2024": "300",
    "2025-2026": "302",
    "2025s1": "304",
}


# Please note: this only supports the MN House, not the Senate. Senate votes are scraped in bills.py
class MNVoteScraper(Scraper):

    bill_link_number_re = re.compile(r"([A-Z]+)0*([1-9]+[0-9]*)")

    def scrape(self, session=None):
        session_internal_id = SESSION_SOURCE_IDS.get(session)
        if not session_internal_id:
            self.warning("no session internal ID recorded for %s", session)
            return
        votes_summary_endpoint = "https://www.house.mn.gov/Votes/GetVoteSummary"
        votes = self.post(
            votes_summary_endpoint,
            {
                "SessionKey": session_internal_id,
                "sortOption": "BillNumber",
            },
        ).json()
        # JSON has a Date property that looks like '/Date(-62135575200000)/' - useful?
        for vote in votes:
            bill_id_with_leading = vote["Number"]
            bill_id_match = self.bill_link_number_re.search(bill_id_with_leading)
            bill_id = f"{bill_id_match.group(1)} {bill_id_match.group(2)}"
            yield from self.scrape_votes(session, bill_id, bill_id_with_leading)

    def scrape_votes(self, session, bill_id, bill_id_for_url):
        # URL looks like https://www.house.mn.gov/Votes/Details?SessionKey=302&BillNumber=HF0003
        link_url = f"https://www.house.mn.gov/Votes/Details?SessionKey={SESSION_SOURCE_IDS.get(session)}&BillNumber={bill_id_for_url}"
        html = self.get(link_url).text
        doc = lxml.html.fromstring(html)
        for vote_container in doc.xpath('//div[contains(@class, "collapsible-panel")]'):
            # Parse Vote Event metadata
            header_table_cells = vote_container.xpath(
                './/div[contains(@class, "panel-header")]//tbody//td'
            )
            motion_text_line_breaks = header_table_cells[1].xpath("./br")
            motion_text = motion_text_line_breaks[-1].tail
            yes_votes = int(header_table_cells[3].text_content())
            no_votes = int(header_table_cells[4].text_content())

            is_amendment = False
            amendment_br_elems = header_table_cells[2].xpath("./br")
            if len(amendment_br_elems) > 0:
                if amendment_br_elems[0].tail and amendment_br_elems[0].tail.strip():
                    is_amendment = True

            if is_amendment:
                motion_classification = "amendment"
            else:
                motion_classification = "passage"

            date_text = f"{header_table_cells[6].text_content()}"
            date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()

            if bill_id[0] == "H":
                bill_chamber = "lower"
            elif bill_id[0] == "S":
                bill_chamber = "upper"
            else:
                raise Exception(f"Unexpected bill ID to parse chamber: {bill_id}")

            journal_page_number = header_table_cells[5].xpath("./a")[0].text_content()
            # TODO add source journal URL
            # You can make a POST request to https://www.house.mn.gov/Votes/GetPage
            # to get redirected to the source journal page (HTML) for this vote
            # with values like {PageNumber: "643", SessionKey: 302}

            # several amendment votes can share a date, motion text and even a
            # journal page, so the amendment number (e.g. H0025A5) tells them apart
            amendment_number = (header_table_cells[2].text or "").strip()
            identifier = f"Journal page {journal_page_number}"
            if amendment_number:
                identifier += f", {amendment_number}"

            vote = VoteEvent(
                identifier=identifier,
                chamber="lower",
                start_date=date,
                motion_text=motion_text,
                result="pass" if yes_votes > no_votes else "fail",
                classification=motion_classification,
                legislative_session=session,
                bill=bill_id,
                bill_chamber=bill_chamber,
            )
            vote.set_count("yes", yes_votes)
            vote.set_count("no", no_votes)
            vote.add_source(link_url)
            vote.dedupe_key = (
                f"{session}-{bill_id}-{date_text}-{motion_text}-{journal_page_number}"
            )
            if amendment_number:
                vote.dedupe_key += f"-{amendment_number}"

            # parse individual votes
            # first table is the YES and second table is the NO
            # plenty of "spacer" TDs in here that are just whitespace for no good reason
            content_vote_tables = vote_container.xpath(
                ".//div[contains(@class, 'panel-content')]//table"
            )
            for i, vote_table in enumerate(content_vote_tables):
                content_vote_cells = vote_table.xpath(".//td")
                for content_vote_cell in content_vote_cells:
                    voter = content_vote_cell.text_content()
                    if voter.strip():
                        if i == 0:
                            vote.yes(voter)
                        else:
                            vote.no(voter)

            yield vote
