import os
import re
import datetime
import requests.exceptions
from openstates.utils import LXMLMixin
from pupa.utils import convert_pdf
from pupa.scrape import Scraper, VoteEvent as Vote


date_re = (
    r".*(?P<date>(MONDAY|TUESDAY|WEDNESDAY|"
    + r"THURSDAY|FRIDAY|SATURDAY|SUNDAY),\s\w+\s\d{1,2},\s\d{4}).*"
)
chamber_re = r".*JOURNAL OF THE ((HOUSE)|(SENATE)).*\d+.*DAY.*"
page_re = r"Page\s\d+"


class NDVoteScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber_name = "house" if chamber == "lower" else "senate"
        session_slug = {
            "62": "62-2011",
            "63": "63-2013",
            "64": "64-2015",
            "65": "65-2017",
            "66": "66-2019",
        }[session]

        # Open the index page of the session's Registers, and open each
        url = "http://www.legis.nd.gov/assembly/%s/journals/%s-journal.html" % (
            session_slug,
            chamber_name,
        )
        page = self.lxmlize(url)
        pdfs = page.xpath("//a[contains(@href, '.pdf')]")
        for pdf in pdfs:

            # Initialize information about the vote parsing
            results = {}
            in_motion = False
            cur_vote = None
            in_vote = False
            cur_motion = ""
            bills = []

            # Determine which URLs the information was pulled from
            pdf_url = pdf.attrib["href"]

            try:
                (path, response) = self.urlretrieve(pdf_url)
            except requests.exceptions.ConnectionError:
                continue

            # Convert the PDF to text
            data = convert_pdf(path, type="text").decode("utf-8")
            os.unlink(path)

            # Determine the date of the document
            date = re.findall(date_re, data)
            if date:
                date = date[0][0]
                cur_date = datetime.datetime.strptime(date, "%A, %B %d, %Y")
            else:
                # If no date is found anywhere, do not process the document
                self.warning("No date was found for the document; skipping.")
                continue

            # Check each line of the text for motion and vote information
            lines = data.splitlines()
            for line in lines:
                # Ignore lines with no information
                if (
                    re.search(chamber_re, line)
                    or re.search(date_re, line)
                    or re.search(page_re, line)
                    or line.strip() == ""
                ):
                    pass

                # Ensure that motion and vote capturing are not _both_ active
                elif in_motion and in_vote:
                    raise AssertionError(
                        "Scraper should not be simultaneously processing "
                        + "motion name and votes, as it is for this motion: "
                        + cur_motion
                    )

                # Start capturing motion text after a ROLL CALL header
                elif not in_motion and not in_vote:
                    if line.strip() == "ROLL CALL":
                        in_motion = True

                elif in_motion and not in_vote:
                    if cur_motion == "":
                        cur_motion = line.strip()
                    else:
                        cur_motion = cur_motion + " " + line.strip()

                    # ABSENT AND NOT VOTING marks the end of each motion name
                    # In this case, prepare to capture votes
                    if line.strip().endswith("VOTING") or line.strip().endswith(
                        "VOTING."
                    ):
                        in_motion = False
                        in_vote = True

                elif not in_motion and in_vote:
                    # Ignore appointments and confirmations
                    if "The Senate advises and consents to the appointment" in line:
                        in_vote = False
                        cur_vote = None
                        results = {}
                        cur_motion = ""
                        bills = []

                    # If votes are being processed, record the voting members
                    elif ":" in line:
                        cur_vote, who = (x.strip() for x in line.split(":", 1))
                        who = [x.strip() for x in who.split(";") if x.strip() != ""]
                        results[cur_vote] = who

                        name_may_be_continued = False if line.endswith(";") else True

                    # Extracts bill numbers in the closing text
                    # used for when the closing text is multiple lines.
                    elif (
                        cur_vote is not None
                        and re.findall(r"(?i)(H|S|J)(C?)(B|R|M) (\d+)", line)
                        and not any(
                            x in line.lower()
                            for x in [
                                "passed",
                                "adopted",
                                "sustained",
                                "prevailed",
                                "lost",
                                "failed",
                            ]
                        )
                    ):
                        bills.extend(re.findall(r"(?i)(H|S|J)(C?)(B|R|M) (\d+)", line))

                    elif cur_vote is not None and not any(
                        x in line.lower()
                        for x in [
                            "passed",
                            "adopted",
                            "sustained",
                            "prevailed",
                            "lost",
                            "failed",
                        ]
                    ):
                        who = [x.strip() for x in line.split(";") if x.strip() != ""]

                        if name_may_be_continued:
                            results[cur_vote][-1] = (
                                results[cur_vote][-1] + " " + who.pop(0)
                            )

                        name_may_be_continued = False if line.endswith(";") else True

                        results[cur_vote].extend(who)

                    # At the conclusion of a vote, save its data
                    elif any(
                        x in line.lower()
                        for x in [
                            "passed",
                            "adopted",
                            "sustained",
                            "prevailed",
                            "lost",
                            "failed",
                        ]
                    ):

                        in_vote = False
                        cur_vote = None

                        # Identify what is being voted on
                        # Throw a warning if impropper informaiton found
                        bills.extend(re.findall(r"(?i)(H|S|J)(C?)(B|R|M) (\d+)", line))
                        if bills == [] or cur_motion.strip() == "":
                            results = {}
                            cur_motion = ""
                            self.warning(
                                "No motion or bill name found: "
                                + "motion name: "
                                + cur_motion
                                + "; "
                                + "decision text: "
                                + line.strip()
                            )
                            continue

                        # If votes are found in the motion name, throw an error
                        if "YEAS:" in cur_motion or "NAYS:" in cur_motion:
                            raise AssertionError(
                                "Vote data found in motion name: " + cur_motion
                            )

                        # Use the collected results to determine who voted how
                        keys = {
                            "YEAS": "yes",
                            "NAYS": "no",
                            "ABSENT AND NOT VOTING": "other",
                        }
                        res = {}
                        for key in keys:
                            if key in results:
                                res[keys[key]] = results[key]
                            else:
                                res[keys[key]] = []

                        # Count the number of members voting each way
                        yes, no, other = (
                            len(res["yes"]),
                            len(res["no"]),
                            len(res["other"]),
                        )
                        chambers = {"H": "lower", "S": "upper", "J": "legislature"}

                        # Almost all of the time, a vote only applies to one bill and this loop
                        # will only be run once.
                        # Some exceptions exist.

                        for bill in bills:

                            cur_bill_id = "%s%s%s %s" % bill

                            # Identify the source chamber for the bill
                            try:
                                bc = chambers[cur_bill_id[0]]
                            except KeyError:
                                bc = "other"

                            # Determine whether or not the vote passed
                            if "over the governor's veto" in cur_motion.lower():
                                VETO_SUPERMAJORITY = 2 / 3
                                passed = yes / (yes + no) > VETO_SUPERMAJORITY
                            else:
                                passed = yes > no
                            # Create a Vote object based on the scraped information
                            vote = Vote(
                                chamber=chamber,
                                start_date=cur_date.strftime("%Y-%m-%d"),
                                motion_text=cur_motion,
                                result="pass" if passed else "fail",
                                legislative_session=session,
                                classification="passage",
                                bill=cur_bill_id,
                                bill_chamber=bc,
                            )

                            vote.add_source(pdf_url)
                            vote.add_source(url)
                            vote.set_count("yes", yes)
                            vote.set_count("no", no)
                            vote.set_count("other", other)
                            # For each category of voting members,
                            # add the individuals to the Vote object
                            for key in res:
                                for voter in res[key]:
                                    vote.vote(key, voter)

                            # Check the vote counts in the motion text against
                            # the parsed results
                            for category_name in keys.keys():
                                # Need to search for the singular, not plural, in the text
                                # so it can find, for example,  " 1 NAY "
                                vote_re = r"(\d+)\s{}".format(category_name[:-1])
                                motion_count = int(re.findall(vote_re, cur_motion)[0])

                                for item in vote.counts:
                                    if item["option"] == keys[category_name]:
                                        vote_count = item["value"]

                                if motion_count != vote_count:
                                    self.warning(
                                        "Motion text vote counts ({}) ".format(
                                            motion_count
                                        )
                                        + "differed from roll call counts ({}) ".format(
                                            vote_count
                                        )
                                        + "for {0} on {1}".format(
                                            category_name, cur_bill_id
                                        )
                                    )

                                    for item in vote.counts:
                                        if item["option"] == keys[category_name]:
                                            vote_count = motion_count

                            yield vote

                        # With the vote successfully processed,
                        # wipe its data and continue to the next one
                        results = {}
                        cur_motion = ""
                        bills = []
