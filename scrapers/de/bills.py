import datetime as dt
from functools import partial
import json
from json.decoder import JSONDecodeError
from requests.exceptions import JSONDecodeError as RequestsJSONDecodeError
import random
import re
import time
from urllib.parse import urljoin

import fitz
from openstates.scrape import Scraper, Bill, VoteEvent
from utils import LXMLMixin
from .actions import BILL_ID, Categorizer


class FailedBillFetch:
    def __init__(self, bill_id, fetch_type):
        self.bill_id = bill_id
        self.fetch_type = fetch_type


class DEBillScraper(Scraper, LXMLMixin):
    verify = False

    base_url = "https://legis.delaware.gov"

    categorizer = Categorizer()
    chamber_codes = {"upper": 1, "lower": 2}
    chamber_codes_rev = {1: "upper", 2: "lower"}
    chamber_map = {"House": "lower", "Senate": "upper"}
    legislators = {}
    legislators_by_short = {}
    legislators_by_district = {}
    # roll call PDF url -> (motion, classification); consent calendars are
    # shared by every bill on them
    vote_motions = {}

    """
    DE has caucus-specific sites that it now
    uses to identify bill sponsors...sometimes.
    This mapping helps us consistently get sponsor IDs
    from those caucus-specific sites
    """
    potential_sponsor_urls = {
        "housegop": "https://housegop.delaware.gov/members/house-district-",
        "senategop": "https://senategop.delaware.gov/members/senate-district-",
        "housedems": "https://housedems.delaware.gov/members/house-district-",
        "senatedems": "https://senatedems.delaware.gov/members/senate-district-",
    }

    def decode_and_retry_request(
        self,
        log_label,
        request_method,
        attempt=1,
        retries=3,
        raise_exception=True,
        empty_ok=False,
    ):
        """
        Decode a JSON response, retrying the request if it isn't JSON.
        HTTP errors (the site answers 403 when requests come too fast) are
        retried by scrapelib. The JSON endpoints answer an empty 200 when there
        is nothing to return (a bill with no votes or no actions); with
        empty_ok that is returned as None without retrying.
        """
        try:
            response = request_method()
            if empty_ok and response.status_code == 200 and not response.content:
                return None
            data = json.loads(response.content.decode("utf-8"))
            return data
        except (JSONDecodeError, RequestsJSONDecodeError) as error:
            if attempt < retries:
                min_seconds = 5
                max_seconds = 10
                delay = random.uniform(min_seconds, max_seconds)
                self.warning(
                    f"Failed to fetch {log_label} on attempt {attempt}, retrying w delay {delay}"
                )
                time.sleep(delay)
                return self.decode_and_retry_request(
                    log_label,
                    request_method,
                    attempt + 1,
                    retries,
                    raise_exception,
                    empty_ok,
                )
            else:
                self.warning(
                    f"Failed to fetch {log_label} on attempt {attempt} of {retries}, giving up"
                )
                if raise_exception:
                    raise error
                else:
                    return None

    def scrape(self, session=None, start_page=1, end_page=None):
        start_page = int(start_page)
        if end_page:
            end_page = int(end_page)
        self.headers = {
            "x-oxylabs-force-headers": "1",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "dnt": "1",
            "priority": "u=0, i",
            "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }

        # legis.delaware.gov answers 403 to more than about 160 requests a
        # minute and lifts the block within seconds, so throttle every
        # request below that and retry 403s quickly (2, 4, 8, ... s)
        self.requests_per_minute = 150
        self.retry_attempts = 8
        self.retry_wait_seconds = 2
        self.timeout = 130
        self.init_asp()
        self.headers["x-requested-with"] = "XMLHttpRequest"
        # Cache the legislators, we'll need them for sponsors and votes
        self.scrape_legislators(session)

        # Cannot scrape a particular chamber, since the search-by-chamber
        # returns bills that are currently _active_ in a chamber,
        # and is not a search by chamber-of-origin
        per_page = 20

        bills_and_votes = []
        page_number = start_page
        while True:
            post_search = partial(
                self.post_search,
                session=session,
                page_number=page_number,
                per_page=per_page,
            )
            page = self.decode_and_retry_request("post_search", post_search, retries=6)
            if not page["Data"]:
                self.info("Found no more bills in pagination")
                break
            for bill in page["Data"]:
                bills_and_votes.extend(list(self.scrape_bill(bill, session)))
            page_number += 1
            if end_page and page_number > end_page:
                self.info(
                    f"Stopping bills fetch at the specified ending page number {end_page}"
                )
                break
        yield from self.filter_bills(bills_and_votes)

    def filter_bills(self, items):
        """
        Read through all bills on a page. If a bill has no substitutes,
        yield it. If a bill does have substitutes, keep the highest-numbered
        substitute and only yield that Bill object.
        Bills may be amended (`BILL_ID w/ AMENDMENT ID` on the website),
        but if that is the case then the original (unamended) version
        should not exist anymore.
        """
        # Map of {bill_id: bill}
        bills = {}
        votes = []

        for bill in items:
            # The generator also yields VoteEvent objects
            if isinstance(bill, VoteEvent):
                votes.append(bill)
                continue

            # The generator also includes FailedBill objects representing failures to fetch
            # we want to log these out at the end, so putting this logic here in filter_bills()
            if isinstance(bill, FailedBillFetch):
                self.logger.warning(
                    f"Failed to fetch bill {bill.bill_id} on fetch {bill.fetch_type}"
                )
                continue

            if (
                bill.identifier in bills
                and (
                    "amendment" in bill.extras
                    or "amendment" in bills[bill.identifier].extras
                )
                and bill.extras.get("substitute")
                == bills[bill.identifier].extras.get("substitute")
            ):
                raise ValueError(
                    f"Bill `{bill.identifier}` showed up _both_ amended and unamended"
                )

            if bill.identifier not in bills:
                # This includes bills that were never substituted
                bills[bill.identifier] = bill
            elif "substitute" in bill.extras and (
                "substitute" not in bills[bill.identifier].extras
                or bill.extras["substitute"]
                > bills[bill.identifier].extras["substitute"]
            ):
                bills[bill.identifier] = bill
            else:
                self.warning(f"Ignoring substituted bill `{bill.identifier}`")

        # a vote on a bill later replaced by its substitute belongs to the
        # bill that is kept, or it would point at a bill that isn't saved
        for vote in votes:
            kept = bills.get(vote.bill_identifier)
            if kept and vote.bill != kept._id:
                vote.set_bill(kept)
            yield vote
        yield from bills.values()

    def scrape_bill(self, row, session):
        bill_id = row["LegislationDisplayCode"]

        amendment = None
        substitute = None

        if bill_id.count(" ") > 1:
            if " w/ " in bill_id:
                self.info(f"Found amended bill `{bill_id}`")
                bill_id, amendment = bill_id.split(" w/ ")
            if " -" in bill_id:
                self.info(f"Found amended bill `{bill_id}`")
                bill_id, amendment = bill_id.split(" -")
            # A bill can _both_ be amended and be substituted
            if " for " in bill_id:
                self.info(f"Found substitute to use instead: `{bill_id}`")
                substitute, bill_id = bill_id.split(" for ")
            if amendment is None and substitute is None:
                raise ValueError(f"unknown bill_id format: {bill_id}")

        bill_type = self.classify_bill(bill_id)
        chamber = "upper" if bill_id.startswith("S") else "lower"

        bill = Bill(
            identifier=bill_id,
            legislative_session=session,
            chamber=chamber,
            title=row["LongTitle"],
            classification=bill_type,
        )
        if row["Synopsis"]:
            bill.add_abstract(row["Synopsis"], "synopsis")
        if row["ShortTitle"]:
            bill.add_title(row["ShortTitle"], "short title")
        if row["SponsorPersonId"]:
            self.add_sponsor_by_legislator_id(bill, row["SponsorPersonId"], "primary")
        if substitute:
            bill.extras["substitute"] = substitute
        if amendment:
            bill.extras["amendment"] = amendment

        # TODO: Is there a way get additional sponsors and cosponsors, and versions/fns via API?
        html_url = f"https://legis.delaware.gov/BillDetail?LegislationId={row['LegislationId']}"
        bill.add_source(html_url, note="text/html")

        try:
            html = self.lxmlize(html_url, verify=False)
        except:  # noqa: E722
            # Collecting bills we had to skip because of failure to fetch
            failure = FailedBillFetch(bill_id, "fetch_bill_page")
            yield failure
            return

        additional_sponsors = html.xpath(
            '//label[text()="Additional Sponsor(s):"]/following-sibling::div/a'
        )

        for sponsor_link in additional_sponsors:
            sponsor_id, sponsor_key = self.parse_sponsor_link(sponsor_link)
            if sponsor_id is not None:
                self.add_sponsor_by_legislator_id(
                    bill, sponsor_id, "primary", sponsor_key
                )

        cosponsors = html.xpath(
            '//label[text()="Co-Sponsor(s):"]/following-sibling::div/a'
        )
        for sponsor_link in cosponsors:
            sponsor_id, sponsor_key = self.parse_sponsor_link(sponsor_link)
            if sponsor_id is not None:
                self.add_sponsor_by_legislator_id(
                    bill, sponsor_id, "cosponsor", sponsor_key
                )

        versions = html.xpath(
            '//label[text()="Original / Not Amended:"]/following-sibling::div/a/@href'
        )
        for version_url in versions:
            version_url = urljoin(self.base_url, version_url)
            media_type = self.mime_from_link(version_url)
            version_name = "Bill Text"
            bill.add_version_link(version_name, version_url, media_type=media_type)

        fiscals = html.xpath('//div[contains(@class,"fiscalNote")]/a/@href')
        for fiscal in fiscals:
            self.scrape_fiscal_note(bill, urljoin(self.base_url, fiscal))

        self.scrape_actions(bill, row["LegislationId"])

        # Fall back to the bill detail HTML when the actions API is empty.
        if not bill.actions:
            self.scrape_fallback_actions_from_html(bill, html)

        if row["HasAmendments"] is True:
            self.scrape_amendments(bill, row["LegislationId"])

        code_cite = html.xpath(
            '//label[contains(text(),"Volume:Chapter")]/following-sibling::div/text()'
        )
        if code_cite and "N/A" not in code_cite[0]:
            code_cite = code_cite[0].strip().split(":")
            eff_date = html.xpath(
                '//label[contains(text(),"Effective Date")]'
                "/following-sibling::div/text()"
            )[0].strip()
            exp_date = html.xpath(
                '//label[contains(text(),"Sunset Date")]/following-sibling::div/text()'
            )[0].strip()

            code_urls = html.xpath("//a[contains(@href,'SessionLaws/Chapter')]/@href")
            code_url = urljoin(self.base_url, code_urls[0]) if code_urls else None

            if "N/A" in eff_date or eff_date == "" or len(eff_date) > 9:
                eff_date = None

            if "N/A" in exp_date or exp_date == "":
                exp_date = None

            bill.add_citation(
                "The Laws of Delaware",
                f"Volume {code_cite[0]} Chapter {code_cite[1]}",
                "chapter",
                url=code_url,
                effective=eff_date,
                expires=exp_date,
            )

        yield from self.scrape_votes(bill, row["LegislationId"], session)

        yield bill

    def scrape_legislators(self, session):
        search_form_url = "https://legis.delaware.gov/json/Search/GetFullLegislatorList"
        form = {
            "value": "",
            # note that's selectedGAs plural, it's selectedGA elsewhere
            "selectedGAs[0]": session,
            "sort": "",
            "group": "",
            "filter": "",
        }

        self.info("Fetching legislators")
        page = self.post(
            url=search_form_url,
            data=form,
            allow_redirects=True,
            verify=False,
            headers=self.headers,
            timeout=self.timeout,
        ).content

        page = json.loads(page)
        assert page["Data"], "Cound not fetch legislators!"
        for row in page["Data"]:
            self.legislators[str(row["PersonId"])] = row
            self.legislators_by_short[str(row["ShortName"])] = row
            # House and Senate both number their districts from 1, and a
            # seat's former holder stays listed beside the current one
            key = (row["ChamberId"], row["DistrictNumber"])
            if key not in self.legislators_by_district or row[
                "LegislatorDetailLink"
            ].startswith("http"):
                self.legislators_by_district[key] = row

    def scrape_fiscal_note(self, bill, link):
        media_type = self.mime_from_link(link)
        bill.add_document_link("Fiscal Note", link, media_type=media_type)

    def scrape_votes(self, bill, legislation_id, session):
        votes_url = (
            "https://legis.delaware.gov/json/BillDetail/GetVotingReportsByLegislationId"
        )
        form = {"legislationId": legislation_id, "sort": "", "group": "", "filter": ""}
        self.info(f"Searching for votes for {bill.identifier}")
        request_method = partial(
            self.post,
            url=votes_url,
            data=form,
            allow_redirects=True,
            verify=False,
            headers=self.headers,
            timeout=self.timeout,
        )
        # an empty answer means the bill has no roll calls
        page = self.decode_and_retry_request(
            "scrape_votes", request_method, empty_ok=True
        )
        if page and page["Total"] > 0:
            for row in page["Data"]:
                yield from self.scrape_vote(bill, row["RollCallId"], session)

    def scrape_vote(self, bill, vote_id, session):
        vote_url = (
            "https://legis.delaware.gov/json/RollCall/GetRollCallVoteByRollCallId"
        )
        form = {"rollCallId": vote_id, "sort": "", "group": "", "filter": ""}

        self.info(f"Fetching vote {vote_id} for {bill.identifier}")
        request_method = partial(
            self.post,
            url=vote_url,
            data=form,
            allow_redirects=True,
            verify=False,
            headers=self.headers,
            timeout=self.timeout,
        )
        page = self.decode_and_retry_request("scrape_vote", request_method)

        if page:
            roll = page["Model"]
            # a rescinded roll call is void and is retaken as a new one
            if roll["RollCallStatus"] == "Rescinded":
                self.info(f"Skipping rescinded roll call {vote_id}")
                return
            vote_chamber = self.chamber_map[roll["ChamberName"]]
            # "7/1/16 01:00 AM"
            vote_date = dt.datetime.strptime(
                roll["TakenAtDateTime"], "%m/%d/%y %I:%M %p"
            ).strftime("%Y-%m-%d")

            vote_passed = "pass" if roll["RollCallStatus"] == "Passed" else "fail"
            # VacantVoteCount is empty seats with no voter row, and
            # NotVotingCount already includes ConflictVoteCount
            other_count = int(roll["NotVotingCount"]) + int(roll["AbsentVoteCount"])
            vote_pdf_url = (
                "https://legis.delaware.gov"
                "/json/RollCallController/GenerateRollCallPdf"
                f"?rollCallId={vote_id}&chamberId={self.chamber_codes[vote_chamber]}"
            )
            if vote_pdf_url not in self.vote_motions:
                self.vote_motions[vote_pdf_url] = self.scrape_vote_motion(vote_pdf_url)
            vote_motion, vote_classification = self.vote_motions[vote_pdf_url]
            vote = VoteEvent(
                chamber=vote_chamber,
                start_date=vote_date,
                motion_text=vote_motion or roll["RollCallVoteType"],
                result=vote_passed,
                bill=bill,
                legislative_session=session,
                classification=vote_classification,
            )
            # the vote requirement: SM (simple majority), 2/3, 3/4, 3/5
            vote.extras["vote_requirement"] = roll["RollCallVoteType"]
            # Vote URL is just a generic search URL with POSTed data,
            # so provide a different link
            vote.add_source(vote_pdf_url)
            vote.dedupe_key = f"{bill}#{vote_id}#{roll['RollCallVoteType']}#{vote_chamber}#{vote_date}"
            vote.set_count("yes", roll["YesVoteCount"])
            vote.set_count("no", roll["NoVoteCount"])
            vote.set_count("other", other_count)

            for row in roll["AssemblyMemberVotes"]:
                # AssemblyMemberId looks like it should work here,
                # but for some sessions it's bugged to only return session
                try:
                    voter = self.legislators_by_short[str(row["ShortName"])]
                    name = voter["DisplayName"]
                except KeyError:
                    self.warning(
                        "could not find legislator short name %s", row["ShortName"]
                    )
                    name = row["ShortName"]
                if row["SelectVoteTypeCode"] == "Y":
                    vote.yes(name)
                elif row["SelectVoteTypeCode"] == "N":
                    vote.no(name)
                else:
                    vote.vote("other", name)

            yield vote

    def should_cache_response(self, response):
        # a missing roll call PDF redirects to an HTML error page that answers 200
        url = (response.history or [response])[0].url
        if "GenerateRollCallPdf" in url and not response.content.startswith(b"%PDF"):
            return False
        return super().should_cache_response(response)

    def scrape_vote_motion(self, pdf_url):
        """
        The roll call JSON has no motion; the PDF header names one when the
        vote isn't on the bill itself ("Motion: Veto Override", "Reason Taken:
        motion to recess ..."), or it is a consent calendar. Returns no motion
        and no classification if the PDF can't be read.
        """
        try:
            for _ in range(3):
                pdf = self.get(pdf_url, verify=False).content
                if pdf.startswith(b"%PDF"):
                    break
                time.sleep(random.uniform(5, 10))
            else:
                raise ValueError("not a PDF")
            blocks = fitz.open("pdf", pdf)[0].get_text("blocks")
        except Exception as e:
            self.warning(f"could not read roll call PDF {pdf_url}: {e}")
            return None, []

        motions = {}
        for block in blocks:
            label = None
            for line in block[4].splitlines():
                line = line.strip()
                if line.startswith(("Long Title:", "Vote requirement:")):
                    return self.classify_vote_motion(motions)
                match = re.match(r"(Motion|Reason Taken):\s*(.*)", line, re.I)
                if match:
                    label = match.group(1).title()
                    motions[label] = match.group(2)
                # a wrapped reason, or a label with its text on the next line;
                # "Motion: Veto Override" shares its block with the bill line
                elif label and (label == "Reason Taken" or not motions[label]):
                    motions[label] = f"{motions[label]} {line}".strip()
                elif re.search(r"Consent (Calendar|Agenda)", line):
                    return line, ["passage"]
        return self.classify_vote_motion(motions)

    def classify_vote_motion(self, motions):
        motion = motions.get("Motion", "")
        # "Motion: Other" is followed by the actual "Reason Taken:"
        if motion in ("", "Other"):
            motion = motions.get("Reason Taken") or motion
        if not motion:
            return "Passage", ["passage"]
        if re.search(r"veto override|repass", motion, re.I):
            return motion, ["veto-override"]
        # "HB 160 Mulrooney Passed", "HCR 83 revote after reconsideration"
        if re.match(BILL_ID, motion):
            return "Passage", ["passage"]
        return motion, []

    def parse_sponsor_link(self, sponsor_link):
        # The caucus district URL stays the same when a seat changes hands
        # (a bill co-sponsored by the former member still links to it), so
        # match on the link text, which is the member's ShortName
        short_name = sponsor_link.text_content().strip()
        if short_name in self.legislators_by_short:
            return short_name, "ShortName"
        return self.parse_sponsor_url(sponsor_link.get("href"))

    def parse_sponsor_url(self, sponsor_url):
        sponsor_url = urljoin(self.base_url, sponsor_url)
        if sponsor_url.startswith(f"{self.base_url}/LegislatorDetail"):
            sponsor_id = sponsor_url.replace(
                f"{self.base_url}/LegislatorDetail?personId=", ""
            )
            return sponsor_id, "PersonId"
        for k, v in self.potential_sponsor_urls.items():
            if sponsor_url.startswith(f"https://{k}"):
                chamber_id = 2 if k.startswith("house") else 1
                return (chamber_id, sponsor_url.replace(v, "")), "DistrictId"
        self.warning(f"Could not parse sponsor url, skipping: {sponsor_url}")
        return None, None

    def add_sponsor_by_legislator_id(
        self, bill, legislator_id, sponsor_type, sponsor_key="PersonId"
    ):
        if sponsor_key == "DistrictId":
            sponsor = self.legislators_by_district[legislator_id]
        elif sponsor_key == "ShortName":
            sponsor = self.legislators_by_short[legislator_id]
        elif sponsor_key == "PersonId":
            sponsor = self.legislators[str(legislator_id)]
        sponsor_name = sponsor["DisplayName"]
        chamber = self.chamber_codes_rev[sponsor["ChamberId"]]
        primary = sponsor_type == "primary"
        # The multiple ways in which sponsors are collected sometimes
        # results in duplicates; prevent these
        existing_sponsor_names = [sponsor["name"] for sponsor in bill.sponsorships]
        if sponsor_name not in existing_sponsor_names:
            bill.add_sponsorship(
                name=sponsor_name,
                classification=sponsor_type,
                entity_type="person",
                chamber=chamber,
                primary=primary,
            )
        else:
            self.warning(
                f"Ignoring already-known sponsor: {sponsor_name} for {bill.identifier}"
            )

    def scrape_actions(self, bill, legislation_id):
        actions_url = (
            "https://legis.delaware.gov/json/BillDetail/GetRecentReportsByLegislationId"
        )
        form = {"legislationId": legislation_id, "sort": "", "group": "", "filter": ""}
        self.info(f"Fetching actions for {bill.identifier}")
        request_method = partial(
            self.post,
            url=actions_url,
            data=form,
            allow_redirects=True,
            verify=False,
            headers=self.headers,
            timeout=self.timeout,
        )
        page = self.decode_and_retry_request(
            "scrape_actions", request_method, empty_ok=True
        )
        if not page:
            self.warning(f"No actions returned for {bill.identifier}")
            return
        for row in page["Data"]:
            action_name = row["ActionDescription"]
            action_date = dt.datetime.strptime(
                row["OccuredAtDateTime"], "%m/%d/%y"
            ).strftime("%Y-%m-%d")
            if row.get("ChamberName") is not None:
                action_chamber = self.chamber_map[row["ChamberName"]]
            elif "Senate" in row["ActionDescription"]:
                action_chamber = "upper"
            elif "House" in row["ActionDescription"]:
                action_chamber = "lower"
            elif "Governor" in row["ActionDescription"]:
                # TODO: <obj>.bill_chamber' is not in the enumeration: [u'upper', u'lower']
                action_chamber = "executive"
            else:
                # Actions like 'Stricken' and 'Defeated Amendemnt'
                # don't have a chamber in the data, so assume the bill's home chamber
                action_chamber = "upper" if bill.identifier.startswith("S") else "lower"

            categorization = self.categorizer.categorize(action_name)

            action = bill.add_action(
                description=action_name,
                date=action_date,
                chamber=action_chamber,
                classification=categorization["classification"],
            )

            for leg in categorization["legislators"]:
                action.add_related_entity(leg, "person")
            for c in categorization["committees"]:
                action.add_related_entity(c, "organization")

    def scrape_fallback_actions_from_html(self, bill, html):
        """Add actions from the bill detail HTML when the actions API is empty.

        Only called when ``scrape_actions()`` did not add anything.
        """
        home_chamber = "upper" if bill.identifier.startswith("S") else "lower"

        # "Introduced on: 6/30/26" -> description="Introduced", date=6/30/26
        introduced_values = html.xpath(
            '//label[@class="info-label" and '
            'starts-with(normalize-space(text()), "Introduced on")]'
            "/following-sibling::div[1]/text()"
        )
        if introduced_values:
            intro_text = introduced_values[0].strip()
            intro_date = self._parse_de_short_date(intro_text)
            if intro_date:
                bill.add_action(
                    description="Introduced",
                    date=intro_date,
                    chamber=home_chamber,
                    classification=["introduction"],
                )

        # "Status: House Natural Resources & Energy 6/30/26"
        # -> description="House Natural Resources & Energy", date=6/30/26
        status_values = html.xpath(
            '//label[@class="info-label" and '
            'normalize-space(text())="Status:"]'
            "/following-sibling::div[1]/text()"
        )
        if status_values:
            status_text = status_values[0].strip()
            # Split off a trailing M/D/YY (or M/D/YYYY) date.
            match = re.search(r"\s+(\d{1,2}/\d{1,2}/\d{2,4})\s*$", status_text)
            if match:
                status_date = self._parse_de_short_date(match.group(1))
                description = status_text[: match.start()].strip()
                if status_date and description:
                    # Status text is "{Chamber} {Committee Name}". Rewrite it to
                    # match the categorizer's referral-committee rule.
                    chamber_word = None
                    if description.startswith("Senate"):
                        action_chamber = "upper"
                        chamber_word = "Senate"
                    elif description.startswith("House"):
                        action_chamber = "lower"
                        chamber_word = "House"
                    elif "Governor" in description:
                        action_chamber = "executive"
                    else:
                        action_chamber = home_chamber

                    if chamber_word:
                        committee_name = description[len(chamber_word) :].strip()
                        if committee_name:
                            description = (
                                f"Assigned to {committee_name} "
                                f"Committee in {chamber_word}"
                            )

                    categorization = self.categorizer.categorize(description)
                    action = bill.add_action(
                        description=description,
                        date=status_date,
                        chamber=action_chamber,
                        classification=categorization["classification"],
                    )
                    for leg in categorization["legislators"]:
                        action.add_related_entity(leg, "person")
                    for c in categorization["committees"]:
                        action.add_related_entity(c, "organization")

    def _parse_de_short_date(self, text):
        """Parse DE's short date strings (e.g. "6/30/26") into YYYY-MM-DD.

        Returns ``None`` if the string can't be parsed, so callers can skip
        adding a malformed action rather than crashing the whole scrape.
        """
        text = (text or "").strip()
        if not text:
            return None
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                return dt.datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        self.warning(f"Could not parse DE fallback action date: {text!r}")
        return None

    def scrape_amendments(self, bill, legislation_id):
        # http://legis.delaware.gov/json/BillDetail/GetRelatedAmendmentsByLegislationId?legislationId=47185
        amds_url = (
            "https://legis.delaware.gov/json/BillDetail/GetRelatedAmendmentsByLegislationId"
            f"?legislationId={legislation_id}"
        )
        form = {"sort": "", "group": "", "filter": ""}
        self.info(f"Fetching amendments for {bill.identifier}")
        request_method = partial(
            self.post,
            url=amds_url,
            data=form,
            allow_redirects=True,
            verify=False,
            headers=self.headers,
            timeout=self.timeout,
        )
        page = self.decode_and_retry_request("scrape_amendments", request_method)

        for row in page["Data"]:
            if row["PublicStatusName"] == "Passed":
                # http://legis.delaware.gov/json/BillDetail/GeneratePdfDocument
                # ?legislationId=47252&legislationTypeId=5&docTypeId=2&legislationName=HA1
                # http://legis.delaware.gov/json/BillDetail/GenerateHtmlDocument
                # ?legislationId=47252&legislationTypeId=5&docTypeId=2&legislationName=HA1

                pdf_url = (
                    "http://legis.delaware.gov/json/BillDetail/GeneratePdfDocument?"
                    f"legislationId={row['AmendmentLegislationId']}&legislationTypeId=5&docTypeId=2"
                )

                bill.add_version_link(
                    row["AmendmentCode"],
                    pdf_url,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

                html_url = (
                    "http://legis.delaware.gov/json/BillDetail/GenerateHtmlDocument?"
                    f"legislationId={row['AmendmentLegislationId']}&legislationTypeId=5&docTypeId=2"
                )

                bill.add_version_link(
                    row["AmendmentCode"],
                    html_url,
                    media_type="text/html",
                    on_duplicate="ignore",
                )

    def classify_bill(self, bill_id):
        legislation_types = (
            ("bill", "HB"),
            ("concurrent resolution", "HCR"),
            ("joint resolution", "HJR"),
            ("resolution", "HR"),
            ("bill", "SB"),
            ("concurrent resolution", "SCR"),
            ("joint resolution", "SJR"),
            ("resolution", "SR"),
        )
        for name, abbr in legislation_types:
            if abbr in bill_id:
                return name
        else:
            raise AssertionError("Could not categorize bill ID")

    def post_search(self, session, page_number, per_page):
        search_form_url = (
            "https://legis.delaware.gov/json/AllLegislation/GetAllLegislation"
        )
        form = {
            "page": page_number,
            "pageSize": per_page,
            "selectedGA[0]": session,
            "coSponsorCheck": "True",
            "selectedLegislationTypeId[0]": "1",
            "selectedLegislationTypeId[1]": "2",
            "selectedLegislationTypeId[2]": "3",
            "selectedLegislationTypeId[3]": "4",
            # Ignore the `Amendment` legislation type, `5`
            "selectedLegislationTypeId[4]": "6",
            "sort": "",
            "group": "",
            "filter": "",
            "sponsorName": "",
            "fromIntroDate": "",
            "toIntroDate": "",
        }

        response = self.post(
            url=search_form_url,
            data=form,
            allow_redirects=True,
            verify=False,
            headers=self.headers,
            timeout=self.timeout,
        )
        return response

    def mime_from_link(self, link):
        if "HtmlDocument" in link:
            return "text/html"
        elif "PdfDocument" in link:
            return "application/pdf"
        elif "WordDocument" in link:
            return "application/msword"
        else:
            return ""

    # set up our asp session and fetch cookies
    def init_asp(self):
        self.get(
            "https://legis.delaware.gov/", verify=False, headers=self.headers
        ).content
        return
