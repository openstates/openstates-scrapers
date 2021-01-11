import re
import datetime
import lxml.html

from openstates.scrape import Scraper, Bill, VoteEvent
from openstates.scrape.base import ScrapeError

from utils import LXMLMixin

SESSION_IDS = {"2021": "44"}


class SDBillScraper(Scraper, LXMLMixin):
    def scrape(self, chambers=None, session=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        # removing Light here adds more info, maybe useful
        url = (
            f"https://sdlegislature.gov/api/Bills/Session/Light/{SESSION_IDS[session]}"
        )
        chambers = [chambers] if chambers else ["upper", "lower"]

        for chamber in chambers:
            if chamber == "upper":
                bill_abbr = "S"
            else:
                bill_abbr = "H"

            data = self.get(url).json()
            for item in data:
                bill_id = item["BillType"] + item["BillNumber"]
                title = item["Title"]
                link = f"https://sdlegislature.gov/Session/Bill/{item['BillId']}"

                # skip bills from opposite chamber
                if not bill_id.startswith(bill_abbr):
                    continue

                # TODO: remove this and replace it with something that hits the appropriate
                # API endpoints for item['BillId']
                print(bill_id, link)
                yield from self.scrape_bill(chamber, session, bill_id, title, link)

    def scrape_bill(self, chamber, session, bill_id, title, url):
        page = self.lxmlize(url)

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

        version_rows = page.xpath("//div[2]/div/div/table/tbody/tr")
        assert len(version_rows) > 0
        for row in version_rows:
            # dates are in first cell
            (date,) = row.xpath("./td[1]/span/text()")
            date = date.strip()
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            # html in second cell
            (html_note,) = row.xpath("./td[2]/a/text()")
            (html_link,) = row.xpath("./td[2]/a/@href")
            # pdf in third cell
            (pdf_note,) = row.xpath("./td[3]/a/text()")
            (pdf_link,) = row.xpath("./td[3]/a/@href")

            assert html_note == pdf_note
            note = html_note

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

        sponsor_links = page.xpath("//div[2]/div[4]/div[2]/div/a")
        for link in sponsor_links:
            if link.attrib["href"].startswith("https://sdlegislature.gov/Legislators/"):
                sponsor_type = "person"
            elif link.attrib["href"].startswith(
                "https://sdlegislature.gov/Legislative_Session/Committees"
            ):
                sponsor_type = "organization"
            else:
                raise ScrapeError(
                    "Found unexpected sponsor, URL: " + link.attrib["href"]
                )
            bill.add_sponsorship(
                link.text,
                classification="primary",
                primary=True,
                entity_type=sponsor_type,
            )

        actor = chamber

        for row in page.xpath("//div[1]/div/div/div/table/tbody/tr"):

            action_row = row.xpath("./td[2]")
            # Fix me!
            # action is now spans inside of the row, sometimes with spans inside
            # pull text and append to string
            action = ""
            for span in action_row:
                action += span.strip

            atypes = []
            if action.startswith("First read"):
                atypes.append("introduction")
                atypes.append("reading-1")

            if re.match(r"Signed by (?:the\s)*Governor", action, re.IGNORECASE):
                atypes.append("executive-signature")
                actor = "executive"

            match = re.match(r"(.*) Do Pass( Amended)?, (Passed|Failed)", action)
            if match:
                if match.group(1) in ["Senate", "House of Representatives"]:
                    first = ""
                else:
                    first = "committee-"
                if match.group(3).lower() == "passed":
                    second = "passage"
                elif match.group(3).lower() == "failed":
                    second = "failure"
                atypes.append("%s%s" % (first, second))

            if "referred to" in action.lower():
                atypes.append("referral-committee")

            if "Motion to amend, Passed Amendment" in action:
                atypes.append("amendment-introduction")
                atypes.append("amendment-passage")
                # needs updating
                if row.xpath('td[2]/a[contains(@href,"api/Documents")]'):
                    amd = row.xpath('td[2]/a[contains(@href,"api/Documents")]')[0]
                    version_name = amd.xpath("string(.)")
                    version_url = amd.xpath("@href")[0]
                    if "htm" in version_url:
                        mimetype = "text/html"
                    elif "pdf" in version_url:
                        mimetype = "application/pdf"
                    bill.add_version_link(
                        version_name,
                        version_url,
                        media_type=mimetype,
                        on_duplicate="ignore",
                    )

            if "Veto override, Passed" in action:
                atypes.append("veto-override-passage")
            elif "Veto override, Failed" in action:
                atypes.append("veto-override-failure")

            if "Delivered to the Governor" in action:
                atypes.append("executive-receipt")

            match = re.match("First read in (Senate|House)", action)
            if match:
                if match.group(1) == "Senate":
                    actor = "upper"
                else:
                    actor = "lower"

            date = row.xpath("string(td[1]/div[2]/span/a)").strip()
            match = re.match(r"\d{2}/\d{2}/\d{4}", date)
            if not match:
                self.warning("Bad date: %s" % date)
                continue
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

            for link in row.xpath("td[2]/a[contains(@href, 'Vote')]"):
                yield from self.scrape_vote(bill, date, link.attrib["href"])

            if action:
                bill.add_action(action, date, chamber=actor, classification=atypes)

        for link in page.xpath("//a[contains(@href, 'Keyword')]"):
            bill.add_subject(link.text.strip())

        yield bill

    def scrape_vote(self, bill, date, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        header = page.xpath("string(//main/div/div/div[2]/div[1]/div)")

        if "No Bill Action" in header:
            self.warning("bad vote header -- skipping")
            return
        location = header.split(", ")[1]

        if location.startswith("House"):
            chamber = "lower"
        elif location.startswith("Senate"):
            chamber = "upper"
        elif location.startswith("Joint"):
            chamber = "legislature"
        else:
            raise ScrapeError("Bad chamber: %s" % location)

        motion = ", ".join(header.split(", ")[2:]).strip()
        if motion:
            # If we can't detect a motion, skip this vote
            yes_count = int(page.xpath("string(//div[2]/div/span[1]/span)"))
            no_count = int(page.xpath("string(//div[2]/div/span[2]/span)"))
            excused_count = int(page.xpath("string(//div[2]/div/span[3]/span)"))
            absent_count = int(page.xpath("string(//div[2]/div/span[4]/span)"))

            passed = yes_count > no_count

            if motion.startswith("Do Pass"):
                type = "passage"
            elif motion == "Concurred in amendments":
                type = "amendment"
            elif motion == "Veto override":
                type = "veto_override"
            else:
                type = []

            vote = VoteEvent(
                chamber=chamber,
                start_date=date,
                motion_text=motion,
                result="pass" if passed else "fail",
                classification=type,
                bill=bill,
            )
            # The vote page URL has a unique ID
            # However, some votes are "consent calendar" events,
            # and relate to the passage of _multiple_ bills
            # These can't be modeled yet in Pupa, but for now we can
            # append a bill ID to the URL that forms the `pupa_id`
            # https://github.com/opencivicdata/pupa/issues/308
            vote.pupa_id = "{}#{}".format(url, bill.identifier.replace(" ", ""))

            vote.add_source(url)
            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("excused", excused_count)
            vote.set_count("absent", absent_count)

            for td in page.xpath("//div/div/div[2]/div[3]/div/div/div"):
                option_or_person = td.text.strip()
                if option_or_person in ("Aye", "Yea"):
                    vote.yes(td.getprevious().text.strip())
                elif option_or_person == "Nay":
                    vote.no(td.getprevious().text.strip())
                elif option_or_person == "Excused":
                    vote.vote("excused", td.getprevious().text.strip())
                elif option_or_person == "Absent":
                    vote.vote("absent", td.getprevious().text.strip())

            yield vote
