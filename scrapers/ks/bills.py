import re
import json
import datetime
import requests

import lxml.html
from openstates.scrape import Scraper, Bill, VoteEvent

from . import ksapi


def _clean_spaces(title):
    return re.sub(r"\s+", " ", title)


class KSBillScraper(Scraper):
    special_slugs = {"2020S1": "li_2020s", "2021S1": "li_2021s"}

    def scrape(self, chamber=None, session=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):

        # Pull the session metadata so we can get the
        # slug for the API Request
        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        if meta["classification"] == "special":
            list_slug = self.special_slugs[session]
        else:
            list_slug = "li"

        list_url = "http://www.kslegislature.org/{}" "/api/v11/rev-1/bill_status"
        list_url = list_url.format(list_slug)

        chamber_name = "Senate" if chamber == "upper" else "House"
        chamber_letter = chamber_name[0]
        # perhaps we should save this data so we can make one request for both?
        bill_request = self.get(list_url).text
        bill_request_json = json.loads(bill_request)
        bills = bill_request_json["content"]

        # there are duplicates
        seen_ids = set()

        for bill_data in bills:

            bill_id = bill_data["BILLNO"]

            # filter other chambers
            if not bill_id.startswith(chamber_letter):
                continue
            # filter duplicates
            if bill_id in seen_ids:
                continue

            seen_ids.add(bill_id)

            if "CR" in bill_id:
                btype = "concurrent resolution"
            elif "R" in bill_id:
                btype = "resolution"
            elif "B" in bill_id:
                btype = "bill"

            title = bill_data["SHORTTITLE"] or bill_data["LONGTITLE"]

            # main
            bill = Bill(bill_id, session, title, chamber=chamber, classification=btype)
            bill.extras = {"status": bill_data["STATUS"]}

            bill.add_source(ksapi.url + "bill_status/" + bill_id.lower())

            if bill_data["LONGTITLE"] and bill_data["LONGTITLE"] != bill.title:
                bill.add_title(bill_data["LONGTITLE"])

            # An "original sponsor" is the API's expression of "primary sponsor"
            for primary_sponsor in bill_data["ORIGINAL_SPONSOR"]:
                primary_sponsor = self.clean_sponsor_name(primary_sponsor)
                bill.add_sponsorship(
                    name=primary_sponsor,
                    entity_type="organization"
                    if "committee" in primary_sponsor.lower()
                    else "person",
                    primary=True,
                    classification="original sponsor",
                )
            for sponsor in bill_data["SPONSOR_NAMES"]:
                if sponsor in bill_data["ORIGINAL_SPONSOR"]:
                    continue
                sponsor = self.clean_sponsor_name(sponsor)
                bill.add_sponsorship(
                    name=sponsor,
                    entity_type="organization"
                    if "committee" in sponsor.lower()
                    else "person",
                    primary=False,
                    classification="cosponsor",
                )

            # history is backwards
            for event in reversed(bill_data["HISTORY"]):
                actor = "upper" if event["chamber"] == "Senate" else "lower"

                date = event["session_date"]
                # append committee names if present
                if "committee_names" in event:
                    action = (
                        event["status"] + " " + " and ".join(event["committee_names"])
                    )
                else:
                    action = event["status"]

                if event["action_code"] not in ksapi.action_codes:
                    self.warning(
                        "unknown action code on %s: %s %s"
                        % (bill_id, event["action_code"], event["status"])
                    )
                    atype = None
                else:
                    atype = ksapi.action_codes[event["action_code"]]
                bill.add_action(action, date, chamber=actor, classification=atype)

            # Versions are exposed in `bill_data['versions'],
            # but lack any descriptive text or identifiers;
            # continue to scrape these from the HTML
            yield from self.scrape_html(bill, session)

            yield bill

    def scrape_html(self, bill, session):
        meta = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["identifier"] == session
        )
        slug = meta["_scraped_name"]

        if meta["classification"] == "special":
            li_slug = self.special_slugs[session]
        else:
            li_slug = "li"

        # we have to go to the HTML for the versions & votes
        base_url = "http://www.kslegislature.org/{}/{}/measures/".format(li_slug, slug)
        if "resolution" in bill.classification:
            base_url = "http://www.kslegislature.org/{}/{}/year1/measures/".format(
                li_slug, slug
            )

        url = base_url + bill.identifier.lower() + "/"
        doc = lxml.html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)

        bill.add_source(url)

        # versions & notes
        version_rows = doc.xpath('//tbody[starts-with(@id, "version-tab")]/tr')
        for row in version_rows:
            # version, docs, sn, fn
            tds = row.getchildren()
            title = _clean_spaces(tds[0].text_content().strip())
            doc_url = get_doc_link(tds[1])
            if doc_url:
                bill.add_version_link(title, doc_url, media_type="application/pdf")
            if len(tds) > 2:
                sn_url = get_doc_link(tds[2])
                if sn_url:
                    bill.add_document_link(
                        title + " - Supplementary Note", sn_url, on_duplicate="ignore"
                    )
            if len(tds) > 3:
                if sn_url:
                    bill.add_document_link(
                        title + " - Fiscal Note", sn_url, on_duplicate="ignore"
                    )

        all_links = doc.xpath(
            "//table[@class='bottom']/tbody[@class='tab-content-sub']/tr/td/a/@href"
        )
        vote_members_urls = []
        for i in all_links:
            if "vote_view" in i:
                vote_members_urls.append(str(i))
        if len(vote_members_urls) > 0:
            for link in vote_members_urls:
                yield from self.parse_vote(bill, link)

        history_rows = doc.xpath('//tbody[starts-with(@id, "history-tab")]/tr')
        for row in history_rows:
            row_text = row.xpath(".//td[3]")[0].text_content()
            # amendments & reports
            amendment = get_doc_link(row.xpath(".//td[4]")[0])
            if amendment:
                if "Motion to Amend" in row_text:
                    _, offered_by = row_text.split("Motion to Amend -")
                    amendment_name = "Amendment " + offered_by.strip()
                elif "Conference committee report now available" in row_text:
                    amendment_name = "Conference Committee Report"
                else:
                    amendment_name = row_text.strip()
                bill.add_document_link(
                    _clean_spaces(amendment_name), amendment, on_duplicate="ignore"
                )

    def clean_sponsor_name(self, sponsor):
        if sponsor.split()[0] in ["Representative", "Senator"]:
            sponsor = "".join(sponsor.split()[1:])
        return sponsor

    def parse_vote(self, bill, link):
        # Server sometimes sends proper error headers,
        # sometimes not
        try:
            self.info("Get {}".format(link))
            text = requests.get(link).text
        except requests.exceptions.HTTPError as err:
            self.warning("{} fetching vote {}, skipping".format(err, link))
            return

        if "Varnish cache server" in text:
            self.warning(
                "Scrape rate is too high, try re-scraping with "
                "The --rpm set to a lower number"
            )
            return

        if "Page Not Found" in text or "Page Unavailable" in text:
            self.warning("missing vote, skipping")
            return
        member_doc = lxml.html.fromstring(text)
        motion = member_doc.xpath("//div[@id='main_content']/h4/text()")
        chamber_date_line = "".join(
            member_doc.xpath("//div[@id='main_content']/h3[1]//text()")
        )
        chamber_date_line_words = chamber_date_line.split()
        vote_chamber = chamber_date_line_words[0]
        vote_date = datetime.datetime.strptime(chamber_date_line_words[-1], "%m/%d/%Y")
        vote_status = " ".join(chamber_date_line_words[2:-2])
        opinions = member_doc.xpath(
            "//div[@id='main_content']/h3[position() > 1]/text()"
        )
        if len(opinions) > 0:
            vote_status = vote_status if vote_status.strip() else motion[0]
            vote_chamber = "upper" if vote_chamber == "Senate" else "lower"

            for i in opinions:
                try:
                    count = int(i[i.find("(") + 1 : i.find(")")])
                except ValueError:
                    # This is likely not a vote-count text chunk
                    # It's probably '`On roll call the vote was:`
                    pass
                else:
                    if "yea" in i.lower():
                        yes_count = count
                    elif "nay" in i.lower():
                        no_count = count
                    elif "present" in i.lower():
                        p_count = count
                    elif "absent" in i.lower():
                        a_count = count

            vote = VoteEvent(
                bill=bill,
                start_date=vote_date.strftime("%Y-%m-%d"),
                chamber=vote_chamber,
                motion_text=vote_status,
                result="pass" if yes_count > no_count else "fail",
                classification="passage",
            )
            vote.dedupe_key = link

            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("abstain", p_count)
            vote.set_count("absent", a_count)

            vote.add_source(link)

            a_links = member_doc.xpath("//div[@id='main_content']/a/text()")
            for i in range(1, len(a_links)):
                if i <= yes_count:
                    vote.vote("yes", re.sub(",", "", a_links[i]).split()[0])
                elif no_count != 0 and i > yes_count and i <= yes_count + no_count:
                    vote.vote("no", re.sub(",", "", a_links[i]).split()[0])
                else:
                    vote.vote("other", re.sub(",", "", a_links[i]).split()[0])
            yield vote
        else:
            self.warning("No Votes for: %s", link)


def get_doc_link(elem):
    # try ODT then PDF
    link = elem.xpath('.//a[contains(@href, ".odt")]/@href')
    if link:
        return link[0]
    link = elem.xpath('.//a[contains(@href, ".pdf")]/@href')
    if link:
        return link[0]
