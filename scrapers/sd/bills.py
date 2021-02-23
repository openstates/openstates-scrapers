import re
import datetime

from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.scrape.base import ScrapeError

from utils import LXMLMixin

SESSION_IDS = {"2021": "44", "2020": "43"}


class SDBillScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None, session=None):
        self.seen_votes = set()
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # removing Light here adds more info, maybe useful
        url = (
            f"https://sdlegislature.gov/api/Bills/Session/Light/{SESSION_IDS[session]}"
        )
        chambers = [chamber] if chamber else ["upper", "lower"]

        for chamber in chambers:
            if chamber == "upper":
                bill_abbr = "S"
            else:
                bill_abbr = "H"

            data = self.get(url).json()
            for item in data:
                bill_id = f'{item["BillType"]} {item["BillNumberOnly"]}'
                title = item["Title"]
                link = f"https://sdlegislature.gov/Session/Bill/{item['BillId']}"
                api_link = f"https://sdlegislature.gov/api/Bills/{item['BillId']}"

                # skip bills from opposite chamber
                if not bill_id.startswith(bill_abbr):
                    continue

                # TODO: remove this and replace it with something that hits the appropriate
                # API endpoints for item['BillId']
                self.info(f"{bill_id} {link}")
                yield from self.scrape_bill(chamber, session, bill_id, title, api_link)

    def scrape_bill(self, chamber, session, bill_id, title, url):
        page = self.get(url).json()
        api_id = page["BillId"]

        if re.match(r"^(S|H)B ", bill_id):
            btype = ["bill"]
        elif re.match(r"(S|H)C ", bill_id):
            btype = ["commemoration"]
        elif re.match(r"(S|H)JR ", bill_id):
            btype = ["joint resolution"]
        elif re.match(r"(S|H)CR ", bill_id):
            btype = ["concurrent resolution"]
        else:
            btype = ["bill"]

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=btype,
        )
        bill.add_source(url)

        version_rows = page["Documents"]
        assert len(version_rows) > 0
        for version in version_rows:
            date = version["DocumentDate"]
            if date:
                match = re.match(r"\d{4}-\d{2}-\d{2}", date)
                date = datetime.datetime.strptime(match.group(0), "%Y-%m-%d").date()

                html_link = f"https://sdlegislature.gov/Session/Bill/{api_id}/{version['DocumentId']}"
                pdf_link = f"https://mylrc.sdlegislature.gov/api/Documents/{version['DocumentId']}.pdf"

                note = version["BillVersion"]
                bill.add_version_link(
                    note,
                    html_link,
                    date=date,
                    media_type="text/html",
                    on_duplicate="ignore",
                )
                bill.add_version_link(
                    note,
                    pdf_link,
                    date=date,
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )
            else:
                self.warning("Version listed but no date or documents")

        sponsors = page["BillSponsor"]
        if sponsors:
            for sponsor in sponsors:
                sponsor_type = "person"
                member = sponsor["Member"]
                # first and last name are available, but UniqueName is the old link text
                # could change later?

                bill.add_sponsorship(
                    member["UniqueName"],
                    classification="primary",
                    primary=True,
                    entity_type=sponsor_type,
                )
        else:
            sponsor_type = "organization"
            committee_sponsor = re.search(r">(.*)</a>", page["BillCommitteeSponsor"])[1]
            bill.add_sponsorship(
                committee_sponsor,
                classification="primary",
                primary=True,
                entity_type=sponsor_type,
            )

        for keyword in page["Keywords"]:
            bill.add_subject(keyword["Keyword"]["Keyword"])

        actions_url = f"https://sdlegislature.gov/api/Bills/ActionLog/{api_id}"
        yield from self.scrape_action(bill, actions_url, chamber)

        yield bill

    def scrape_action(self, bill, actions_url, chamber):
        actions = self.get(actions_url).json()
        actor = chamber

        for action in actions:
            if (
                action["StatusText"] is None and action["Description"] is None
            ):  # properties can be null
                action_text = ""
            elif (
                action["StatusText"] is None
            ):  # fallback to Description if available, and no StatusText
                action_text = action["Description"]
            else:
                action_text = action["StatusText"]
            # This value is for synthesize full action text like site, will be added to
            # tried to replicate site logic found in Bill.html on source site
            full_action = [action_text]
            atypes = []
            if action_text.startswith("First read"):
                atypes.append("introduction")
                atypes.append("reading-1")

            if action_text == "Do Pass":
                if re.match(
                    r"(Senate|House of Representatives)",
                    action["ActionCommittee"]["Name"],
                ):
                    first = ""
                else:
                    first = "committee-"
                if action["Result"] == "P":
                    second = "passage"
                # D is "deferred"
                elif (
                    action["Result"] == "F"
                    or action["Result"] == "D"
                    or action["Result"] == "N"
                ):
                    second = "failure"
                else:
                    self.error("Unknown vote code: {}".format(action["Result"]))
                atypes.append("%s%s" % (first, second))

            if (
                action_text == "Do Pass"
                or action_text == "Tabled"
                or action["ShowCommitteeName"]
            ):
                full_action.insert(0, f'{action["ActionCommittee"]["Name"]}')

            if action["ShowPassed"] or action["ShowFailed"]:
                if action["ShowPassed"]:
                    binary = ", Passed,"
                else:
                    binary = ", Failed,"
                full_action.append(binary)

            if "referred to" in action_text.lower():
                atypes.append("referral-committee")
                if 'AssignedCommittee' in full_action:
                    full_action.append(action["AssignedCommittee"]["FullName"])

            if "Veto override" in action_text:
                if action["Result"] == "P":
                    second = "passage"
                else:
                    second = "failure"
                atypes.append("%s%s" % ("veto-override-", second))

            match = re.match("First read in (Senate|House)", action_text)
            if match:
                if match.group(1) == "Senate":
                    actor = "upper"
                else:
                    actor = "lower"

            date_string = action["ActionDate"]
            date_match = re.match(r"\d{4}-\d{2}-\d{2}", date_string)
            if not date_match:
                self.warning("Bad date: %s" % date_string)
                continue
            date = datetime.datetime.strptime(date_match.group(0), "%Y-%m-%d").date()

            if re.match(r"Signed by (?:the\s)*Governor", action_text, re.IGNORECASE):
                atypes.append("executive-signature")
                actor = "executive"
                full_action.append(f"on {date}")

            if "Delivered to the Governor" in action_text:
                atypes.append("executive-receipt")
                full_action.append(f"on {date}")

            if action["Vote"]:
                vote_link = (
                    f"https://sdlegislature.gov/api/Votes/{action['Vote']['VoteId']}"
                )
                if vote_link not in self.seen_votes:
                    yield from self.scrape_vote(bill, date, vote_link)
                    self.seen_votes.add(vote_link)
                if action_text != "Certified uncontested, placed on consent":
                    vote_action = (
                        f"YEAS {action['Vote']['Yeas']}, NAYS {action['Vote']['Nays']}"
                    )
                    full_action.append(vote_action)

            if action["ActionCommittee"] and action["JournalPage"]:
                full_action.append(
                    f"{action['ActionCommittee']['Body']}.J. {action['JournalPage']}"
                )

            if action_text == "Motion to amend" and action["Result"] == "P":
                atypes.append("amendment-introduction")
                atypes.append("amendment-passage")
                if (
                    action["Amendment"]
                    and type(action["Amendment"]) is dict
                    and "DocumentId" in action["Amendment"]
                ):
                    amd = action["Amendment"]["DocumentId"]
                    version_name = action["Amendment"]["Filename"]
                    version_url = (
                        f"https://mylrc.sdlegislature.gov/api/Documents/{amd}.pdf"
                    )
                    bill.add_version_link(
                        version_name,
                        version_url,
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )
                    full_action.append(f"Amendment {version_name}")

            description = " ".join(full_action)
            bill.add_action(description, date, chamber=actor, classification=atypes)

    def scrape_vote(self, bill, date, url):
        page = self.get(url).json()

        location = page["actionLog"]["FullName"]
        if "House" in location:
            chamber = "lower"
        elif "Senate" in location:
            chamber = "upper"
        else:
            raise ScrapeError("Bad chamber: %s" % location)

        motion = page["actionLog"]["StatusText"]
        if motion:
            # If we can't detect a motion, skip this vote
            yes_count = page["Yeas"]
            no_count = page["Nays"]
            excused_count = page["Excused"]
            absent_count = page["Absent"]

            passed = yes_count > no_count

            if motion.startswith("Do Pass"):
                vtype = "passage"
            elif motion == "Concurred in amendments":
                vtype = "amendment"
            elif motion == "Veto override":
                vtype = "veto_override"
            else:
                vtype = []

            vote = VoteEvent(
                chamber=chamber,
                start_date=date,
                motion_text=motion,
                result="pass" if passed else "fail",
                classification=vtype,
                bill=bill,
            )
            # differentiate nearly identical votes
            vote.pupa_id = url

            vote.add_source(url)
            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("excused", excused_count)
            vote.set_count("absent", absent_count)

            for person in page["RollCalls"]:
                option = person["Vote1"]
                if option in ("Aye", "Yea"):
                    vote.yes(person["UniqueName"])
                elif option == "Nay":
                    vote.no(person["UniqueName"])
                elif option == "Excused":
                    vote.vote("excused", person["UniqueName"])
                elif option == "Absent":
                    vote.vote("absent", person["UniqueName"])

            yield vote
