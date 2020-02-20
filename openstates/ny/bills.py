import re
import datetime
import lxml.html
import pytz
from collections import defaultdict

from pupa.scrape import Scraper, Bill, VoteEvent

from .apiclient import OpenLegislationAPIClient
from .actions import Categorizer

eastern = pytz.timezone("US/Eastern")


class NYBillScraper(Scraper):
    categorizer = Categorizer()

    def _parse_bill_number(self, bill_id):
        bill_id_regex = r"(^[ABCEJKLRS])(\d{,6})"
        bill_id_match = re.search(bill_id_regex, bill_id)
        bill_prefix, bill_number = bill_id_match.groups()

        return (bill_prefix, bill_number)

    def _parse_bill_prefix(self, bill_prefix):
        bill_chamber, bill_type = {
            "S": ("upper", "bill"),
            "R": ("upper", "resolution"),
            "J": ("upper", "resolution"),
            "B": ("upper", "concurrent resolution"),
            "C": ("lower", "concurrent resolution"),
            "A": ("lower", "bill"),
            "E": ("lower", "resolution"),
            "K": ("lower", "resolution"),
            "L": ("lower", "joint resolution"),
        }[bill_prefix]

        return (bill_chamber, bill_type)

    def _parse_bill_details(self, bill):
        bill_id = bill["basePrintNo"]
        assert bill_id

        # Parse the bill ID into its prefix and number.
        prefix, number = self._parse_bill_number(bill_id)

        bill_type = self._parse_bill_prefix(prefix)[1]

        active_version = bill["activeVersion"]

        title = bill["title"].strip()

        if not title:
            self.logger.warn("Bill missing title.")
            return

        # Determine the chamber the bill originated from.
        if bill["billType"]["chamber"] == "SENATE":
            bill_chamber = "upper"
        elif bill["billType"]["chamber"] == "ASSEMBLY":
            bill_chamber = "lower"
        else:
            warning = "Could not identify chamber for {}."
            self.logger.warn(warning).format(bill_id)

        senate_url = (
            "http://www.nysenate.gov/legislation/bills/{bill_session}/" "{bill_id}"
        ).format(bill_session=bill["session"], bill_id=bill_id)

        # assembly_url = (
        #     "http://assembly.state.ny.us/leg/?default_fld=&bn={bill_id}"
        #     "&Summary=Y&Actions=Y&Text=Y"
        # ).format(bill_id=bill_id)
        assembly_bill_id = bill_id
        if (bill_id[-1] == "A") or (bill_id[-1] == "B"):
            assembly_bill_id = bill_id[:-1]
        if len(assembly_bill_id) == 3:
            assembly_bill_id = assembly_bill_id[0] + "000" + assembly_bill_id[-2:]
        elif len(assembly_bill_id) == 4:
            assembly_bill_id = assembly_bill_id[0] + "00" + assembly_bill_id[-3:]
        elif len(assembly_bill_id) == 5:
            assembly_bill_id = assembly_bill_id[0] + "0" + assembly_bill_id[-4:]
        else:
            assembly_bill_id = bill_id
        assembly_url = (
            "https://nyassembly.gov/leg/?default_fld=&leg_video=&bn={bill_id}&term={term}"
        ).format(bill_id=assembly_bill_id, term=bill["session"])

        return (
            senate_url,
            assembly_url,
            bill_chamber,
            bill_type,
            bill_id,
            title,
            (prefix, number, active_version),
        )

    def _parse_senate_votes(self, vote_data, bill, url):
        vote_datetime = datetime.datetime.strptime(vote_data["voteDate"], "%Y-%m-%d")
        if vote_data["voteType"] == "FLOOR":
            motion = "Floor Vote"
        elif vote_data["voteType"] == "COMMITTEE":
            motion = "{} Vote".format(vote_data["committee"]["name"])
        else:
            raise ValueError("Unknown vote type encountered.")

        if vote_data["version"]:
            motion += " - Version: " + vote_data["version"]

        vote = VoteEvent(
            chamber="upper",
            start_date=vote_datetime.strftime("%Y-%m-%d"),
            motion_text=motion,
            classification="passage",
            result="fail",
            bill=bill,
        )

        vote.add_source(url)

        vote_rolls = vote_data["memberVotes"]["items"]

        yes_count, no_count, other_count = 0, 0, 0

        # Count all yea votes.
        if "items" in vote_rolls.get("AYE", {}):
            for legislator in vote_rolls["AYE"]["items"]:
                vote.yes(legislator["fullName"])
                yes_count += 1

        if "items" in vote_rolls.get("AYEWR", {}):
            for legislator in vote_rolls["AYEWR"]["items"]:
                vote.yes(legislator["fullName"])
                yes_count += 1

        # Count all nay votes.
        if "items" in vote_rolls.get("NAY", {}):
            for legislator in vote_rolls["NAY"]["items"]:
                vote.no(legislator["fullName"])
                no_count += 1

        # Count all other types of votes.
        other_vote_types = ("EXC", "ABS", "ABD")
        for vote_type in other_vote_types:
            if vote_rolls.get(vote_type, []):
                for legislator in vote_rolls[vote_type]["items"]:
                    vote.vote("other", legislator["fullName"])
                    other_count += 1

        vote.result = "pass" if yes_count > no_count else "fail"
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", other_count)

        return vote

    def _generate_bills(self, session, window=None):
        self.logger.info("Generating bills.")
        bills = defaultdict(list)

        delimiter = "-"
        (start_year, delimiter, end_year) = session.partition(delimiter)
        page = 0
        # 1000 is the current maximum returned record limit for all Open
        # Legislature API calls that use the parameter.
        limit = 1000
        # Flag whether to retrieve full bill data.
        full = True
        while True:
            # Updating the offset before the page matters here.
            offset = limit * page + 1
            page += 1

            # Response should be a dict of the JSON data returned from
            # the Open Legislation API.
            if window:
                to_datetime = datetime.datetime.now()
                from_datetime = datetime.datetime.now() - self.parse_relative_time(
                    window
                )

                # note for debugging:
                # set detail=True to see what changed on the bill
                response = self.api_client.get(
                    "updated_bills",
                    from_datetime=from_datetime.replace(microsecond=0).isoformat(),
                    to_datetime=to_datetime.replace(microsecond=0).isoformat(),
                    detail=False,
                    summary=True,
                    limit=limit,
                    offset=offset,
                    type="updated",
                )

                self.info(
                    "{} bills updated since {}".format(
                        response["total"],
                        from_datetime.replace(microsecond=0).isoformat(),
                    )
                )
            else:
                response = self.api_client.get(
                    "bills",
                    session_year=start_year,
                    limit=limit,
                    offset=offset,
                    full=full,
                )

            if (
                response["responseType"] == "empty list"
                or response["offsetStart"] > response["offsetEnd"]
            ):
                break
            else:
                bills = response["result"]["items"]

            for bill in bills:
                if window:
                    # https://legislation.nysenate.gov/api/3/bills/2017/S8570
                    # unfortunately the updated bills since N api doesn't offer
                    # the full bill info, so get them individually
                    resp = self.api_client.get(
                        "bill",
                        session_year=bill["item"]["session"],
                        bill_id=bill["item"]["printNo"],
                        summary=False,
                        detail=True,
                    )
                    bill = resp["result"]
                yield bill

    def _scrape_bill(self, session, bill_data):
        details = self._parse_bill_details(bill_data)

        (
            senate_url,
            assembly_url,
            bill_chamber,
            bill_type,
            bill_id,
            title,
            (prefix, number, active_version),
        ) = details

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=bill_chamber,
            title=title or bill_data["summary"],
            classification=bill_type,
        )

        if bill_data["summary"]:
            bill.add_abstract(bill_data["summary"], note="")

        bill_active_version = bill_data["amendments"]["items"][active_version]

        # Parse sponsors.
        if bill_data["sponsor"] is not None:
            if bill_data["sponsor"]["rules"] is True:
                bill.add_sponsorship(
                    "Rules Committee",
                    entity_type="organization",
                    classification="primary",
                    primary=True,
                )
            elif not bill_data["sponsor"]["budget"]:
                primary_sponsor = bill_data["sponsor"]["member"]
                bill.add_sponsorship(
                    primary_sponsor["shortName"],
                    entity_type="person",
                    classification="primary",
                    primary=True,
                )

                # There *shouldn't* be cosponsors if there is no sponsor.
                cosponsors = bill_active_version["coSponsors"]["items"]
                for cosponsor in cosponsors:
                    bill.add_sponsorship(
                        cosponsor["shortName"],
                        entity_type="person",
                        classification="cosponsor",
                        primary=False,
                    )

        # List companion bill.
        same_as = bill_active_version.get("sameAs", {})
        # Check whether "sameAs" property is populated with at least one bill.
        if same_as["items"]:
            # Get companion bill ID.
            companion_bill_id = same_as["items"][0]["basePrintNo"]

            # Build companion bill session.
            start_year = same_as["items"][0]["session"]
            end_year = start_year + 1
            companion_bill_session = "-".join([str(start_year), str(end_year)])

            # Attach companion bill data.
            bill.add_related_bill(
                companion_bill_id, companion_bill_session, relation_type="companion"
            )

        # Parse actions.
        chamber_map = {"senate": "upper", "assembly": "lower"}

        for action in bill_data["actions"]["items"]:
            chamber = chamber_map[action["chamber"].lower()]
            action_datetime = datetime.datetime.strptime(action["date"], "%Y-%m-%d")
            action_date = action_datetime.date()
            types, _ = NYBillScraper.categorizer.categorize(action["text"])

            bill.add_action(
                action["text"],
                action_date.strftime("%Y-%m-%d"),
                chamber=chamber,
                classification=types,
            )

        # Handling of sources follows. Sources serving either chamber
        # maintain duplicate data, so we can see certain bill data
        # through either chamber's resources. However, we have to refer
        # to a specific chamber's resources if we want to grab certain
        # specific information such as vote data.
        #
        # As such, I'm placing all potential sources in the interest of
        # thoroughness. - Andy Lo

        # List Open Legislation API endpoint as a source.
        api_url = self.api_client.root + self.api_client.resources["bill"].format(
            session_year=session, bill_id=bill_id, summary="", detail=""
        )
        bill.add_source(api_url)
        bill.add_source(senate_url)
        bill.add_source(assembly_url)

        # Chamber-specific processing.
        for vote_data in bill_data["votes"]["items"]:
            yield self._parse_senate_votes(vote_data, bill, api_url)
        yield from self.scrape_assembly_votes(session, bill, assembly_url, bill_id)

        # A little strange the way it works out, but the Assembly
        # provides the HTML version documents and the Senate provides
        # the PDF version documents.
        amendments = bill_data["amendments"]["items"]
        for key, amendment in amendments.items():
            version = amendment["printNo"]

            html_version = version + " HTML"
            html_url = (
                "http://assembly.state.ny.us/leg/?sh=printbill&bn="
                "{}&term={}&Text=Y".format(bill_id, self.term_start_year)
            )
            bill.add_version_link(
                html_version, html_url, on_duplicate="ignore", media_type="text/html"
            )

            pdf_version = version + " PDF"
            pdf_url = "http://legislation.nysenate.gov/pdf/bills/{}/{}".format(
                self.term_start_year, version
            )
            bill.add_version_link(
                pdf_version,
                pdf_url,
                on_duplicate="ignore",
                media_type="application/pdf",
            )

        yield bill

    def scrape_assembly_votes(self, session, bill, assembly_url, bill_id):

        # parse the bill data page, finding the latest html text
        url = assembly_url + "&Floor%26nbspVotes=Y"

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)

        if "Votes:" in doc.text_content():
            vote_motions = []
            additional_votes_on_motion = 2
            for table in doc.xpath("//table"):

                date = table.xpath('caption/span[contains(., "DATE:")]')
                date = next(date[0].itersiblings()).text
                date = datetime.datetime.strptime(date, "%m/%d/%Y")
                date = eastern.localize(date)
                date = date.isoformat()

                spanText = table.xpath("caption/span/text()")
                motion = spanText[2].strip() + spanText[3].strip()
                if motion in vote_motions:
                    motion = motion + f" - Vote {additional_votes_on_motion}"
                    additional_votes_on_motion += 1
                else:
                    vote_motions.append(motion)

                votes = (
                    table.xpath("caption/span/span")[0].text.split(":")[1].split("/")
                )
                yes_count, no_count = map(int, votes)
                passed = yes_count > no_count
                vote = VoteEvent(
                    chamber="lower",
                    start_date=date,
                    motion_text=motion,
                    bill=bill,
                    result="pass" if passed else "fail",
                    classification="passage",
                )

                vote.set_count("yes", yes_count)
                vote.set_count("no", no_count)
                absent_count = 0
                excused_count = 0
                tds = table.xpath("tr/td/text()")
                votes = [tds[i : i + 2] for i in range(0, len(tds), 2)]

                vote_dictionary = {
                    "Y": "yes",
                    "NO": "no",
                    "ER": "excused",
                    "AB": "absent",
                    "NV": "not voting",
                }

                for vote_pair in votes:
                    name, vote_val = vote_pair
                    vote.vote(vote_dictionary[vote_val], name)
                    if vote_val == "AB":
                        absent_count += 1
                    elif vote_val == "ER":
                        excused_count += 1

                vote.set_count("absent", absent_count)
                vote.set_count("excused", excused_count)
                vote.add_source(url)
                vote.pupa_id = url + motion + spanText[1]

                yield vote

    def parse_relative_time(self, time_str):
        regex = re.compile(
            r"((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?"
        )
        parts = regex.match(time_str)
        if not parts:
            return
        parts = parts.groupdict()
        time_params = {}
        for (name, param) in parts.items():
            if param:
                time_params[name] = int(param)
        return datetime.timedelta(**time_params)

    # This scrape supports both windowed scraping for
    # bills updated since a datetime, and individual bill scraping
    # NEW_YORK_API_KEY=key pupa update ny bills --scrape bill_no=S155
    # or
    # NEW_YORK_API_KEY=key pupa update ny bills --scrape window=5d1h
    def scrape(self, session=None, bill_no=None, window=None):
        self.api_client = OpenLegislationAPIClient(self)

        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        self.term_start_year = session.split("-")[0]

        for bill in self._generate_bills(session, window):
            if bill_no:
                yield from self._scrape_bill(session, bill)
                return
            else:
                yield from self._scrape_bill(session, bill)
