import re
import datetime

import lxml.html

from openstates.scrape import Scraper, Bill, VoteEvent
from . import actions


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
            "https://www.akleg.gov/basis/Committee/List/{session}#tabCom5"
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
        spons_str = (
            doc.xpath('//span[contains(text(), "Sponsor(S)")]')[0].getparent()[1].text
        ).strip()
        # Checks if there is a Sponsor string before matching
        if spons_str:
            sponsors_match = re.match(r"(SENATOR|REPRESENTATIVE)S?", spons_str)
            if sponsors_match:
                sponsors = spons_str.split(",")
                sponsor = sponsors[0].strip()

                if sponsor:
                    bill.add_sponsorship(
                        sponsors[0].split()[1],
                        entity_type="person",
                        classification="primary",
                        primary=True,
                    )

                for sponsor in sponsors[1:]:
                    sponsor = sponsor.strip()
                    # occasional AK site error prints some code here
                    if "Model.Sponsors." in sponsor:
                        continue

                    if sponsor:
                        bill.add_sponsorship(
                            sponsor,
                            entity_type="person",
                            classification="cosponsor",
                            primary=False,
                        )

            else:
                # Committee sponsorship
                spons_str = spons_str.strip()

                if re.match(r" BY REQUEST OF THE GOVERNOR$", spons_str):
                    spons_str = re.sub(
                        r" BY REQUEST OF THE GOVERNOR$", "", spons_str
                    ).title()
                    spons_str = spons_str + " Committee (by request of the governor)"

                if spons_str:
                    bill.add_sponsorship(
                        spons_str,
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

        # print(action)

        # Dan attempt at pulling out the vote information
        # Xpath to grab journal entry information
        # xpath_search = "//b[text()[contains(.,'%s')]]" % journal_entry_number
        # xpath_search = "//body//pre[1]"
        # vote_counts = doc.xpath(xpath_search)
        # print(vote_counts[0].text_content().split("\n"))
        # vote_counts = doc.xpath('//body//b[contains(text(), "YEAS")]')
        # for votes in vote_counts:
        #     print(votes.text_content())

        # yield vote

        # old code
        # re_vote_text = re.compile(r'The question (?:being|to be '
        #   'reconsidered):\s*"(.*?\?)"', re.S)
        # re_header = re.compile(r'\d{2}-\d{2}-\d{4}\s{10,}\w{,20} Journal\s{10,}\d{,6}\s{,4}')

        # if len(doc.xpath('//pre')) < 2:
        #     return

        # Find all chunks of text representing voting reports.
        # votes_text = doc.xpath('//pre')[1].text_content()
        # votes_text = re_vote_text.split(votes_text)
        # votes_data = zip(votes_text[1::2], votes_text[2::2])
        # votes_data = []

        # iVoteOnPage = 0

        # # Process each.
        # votes_data = []
        # for motion, text in votes_data:

        #     iVoteOnPage += 1
        #     yes = no = other = 0

        #     tally = re.findall(r'\b([YNEA])[A-Z]+:\s{,3}(\d{,3})', text)
        #     for vtype, vcount in tally:
        #         vcount = int(vcount) if vcount != '-' else 0
        #         if vtype == 'Y':
        #             yes = vcount
        #         elif vtype == 'N':
        #             no = vcount
        #         else:
        #             other += vcount

        #     vote = VoteEvent(
        #         bill=bill,
        #         start_date=act_date.strftime('%Y-%m-%d'),
        #         chamber=act_chamber,
        #         motion_text=motion,
        #         result='pass' if yes > no else 'fail',
        #         classification='passage',
        #     )
        #     vote.set_count('yes', yes)
        #     vote.set_count('no', no)
        #     vote.set_count('other', other)
        #     print("Yes votes:", yes, "No votes", no, "Other", other)

        #     vote.dedupe_key = (url + ' ' + str(iVoteOnPage)) if iVoteOnPage > 1 else url

        #     # In lengthy documents, the "header" can be repeated in the middle
        #     # of content. This regex gets rid of it.
        #     vote_lines = re_header.sub('', text)
        #     vote_lines = vote_lines.split('\r\n')

        #     vote_type = None
        #     for vote_list in vote_lines:
        #         if vote_list.startswith('Yeas: '):
        #             vote_list, vote_type = vote_list[6:], 'yes'
        #         elif vote_list.startswith('Nays: '):
        #             vote_list, vote_type = vote_list[6:], 'no'
        #         elif vote_list.startswith('Excused: '):
        #             vote_list, vote_type = vote_list[9:], 'other'
        #         elif vote_list.startswith('Absent: '):
        #             vote_list, vote_type = vote_list[9:], 'other'
        #         elif vote_list.strip() == '':
        #             vote_type = None
        #         if vote_type:
        #             for name in vote_list.split(','):
        #                 name = name.strip()
        #                 if name:
        #                     vote.vote(vote_type, name)

        #     vote.add_source(url)
        # yield vote
