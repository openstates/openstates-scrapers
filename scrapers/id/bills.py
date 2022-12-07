from openstates.scrape import Scraper
from openstates.scrape import Bill, VoteEvent
import re
import datetime
from collections import defaultdict
import lxml.html
from .actions import Categorizer


BILLS_URL = "https://legislature.idaho.gov/sessioninfo/%s/legislation/minidata/"
BILL_URL = "https://legislature.idaho.gov/sessioninfo/%s/legislation/%s/"

_CHAMBERS = {"upper": "Senate", "lower": "House"}
_OTHER_CHAMBERS = {"upper": "lower", "lower": "upper"}

_BILL_TYPES = {
    "CR": "concurrent resolution",
    "JM": "joint memorial",
    "JR": "joint resolution",
    "P": "proclamation",
    "R": "resolution",
}
_COMMITTEES = {
    "lower": {
        "Loc Gov": "Local Government",
        "Jud": "Judiciary, Rules and Administration",
        "Res/Con": "Resources and Conservation",
        "Com/HuRes": "Commerce and Human Resources",
        "Transp": "Transportation and Defense",
        "St Aff": "State Affairs",
        "Rev/Tax": "Revenues and Taxation",
        "Health/Wel": "Health and Welfare",
        "Env": "Environment, Energy and Technology",
        "Bus": "Business",
        "Educ": "Education",
        "Agric Aff": "Agricultural Affairs",
        "Approp": "Appropriations",
        "W/M": "Ways and Means",
    },
    "upper": {
        "Agric Aff": "Agricultural Affairs",
        "Com/HuRes": "Commerce and Human Resources",
        "Educ": "Education",
        "Fin": "Finance",
        "Health/Wel": "Health and Welfare",
        "Jud": "Judiciary and Rules",
        "Loc Gov": "Local Government and Taxation",
        "Res/Env": "Resources and Environment",
        "St Aff": "State Affairs",
        "Transp": "Transportation",
    },
}


def get_bill_type(bill_id):
    suffix = bill_id.split(" ")[0]
    if len(suffix) == 1:
        return "bill"
    else:
        return _BILL_TYPES[suffix[1:]]


class IDBillScraper(Scraper):
    categorizer = Categorizer()

    # the following are only used for parsing legislation from 2008 and earlier
    vote = None
    in_vote = False
    ayes = False
    nays = False
    other = False
    last_date = None

    def scrape_subjects(self, session):
        self._subjects = defaultdict(list)

        url = (
            "https://legislature.idaho.gov/sessioninfo" "/{}/legislation/topicind/"
        ).format(session)
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # loop through anchors
        anchors = doc.xpath("//td//a")
        for a in anchors:
            # if anchor has a name, that's the subject
            if a.get("name"):
                subject = a.get("name")
            # if anchor is a link to a bill, save that reference
            elif "legislation" in a.get("href"):
                self._subjects[a.text].append(subject)

    def scrape(self, chamber=None, session=None):
        """
        Scrapes all the bills for a given session and chamber
        """
        # specials don't have subjects
        if "spcl" in session:
            self._subjects = defaultdict(list)
        else:
            self.scrape_subjects(session)

        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_bill_url(chamber, session)

    def scrape_bill_url(self, chamber, session):
        """scrapes legislation for 2009 and above"""
        url = BILLS_URL % session
        bill_index = self.get(url).text
        html = lxml.html.fromstring(bill_index)
        # I check for rows with an id that contains 'bill' and startswith
        # 'H' or 'S' to make sure I dont get any links from the menus
        # might not be necessary
        bill_rows = html.xpath(
            '//tr[contains(@id, "bill") and '
            'starts-with(descendant::td/a/text(), "%s")]' % _CHAMBERS[chamber][0]
        )
        for row in bill_rows:
            matches = re.match(r"([A-Z]*)([0-9]+)", row[0].text_content().strip())
            bill_id = " ".join(matches.groups()).strip()
            short_title = row[1].text_content().strip()
            yield from self.scrape_bill(chamber, session, bill_id, short_title)

    def scrape_bill(self, chamber, session, bill_id, short_title=None):
        """
        Scrapes documents, actions, vote counts and votes for
        bills from the 2009 session and above.
        """
        url = BILL_URL % (session, bill_id.replace(" ", ""))
        bill_page = self.get(url).text
        html = lxml.html.fromstring(bill_page)
        html.make_links_absolute(
            "https://legislature.idaho.gov/legislation/%s/" % session
        )
        bill_tables = html.xpath('//table[contains(@class, "bill-table")]')
        title = bill_tables[1].text_content().strip()
        bill_type = get_bill_type(bill_id)
        bill = Bill(
            legislative_session=session,
            chamber=chamber,
            identifier=bill_id,
            title=title,
            classification=bill_type,
        )
        bill.add_source(url)
        for subject in self._subjects[bill_id.replace(" ", "")]:
            bill.add_subject(subject)

        if short_title and title.lower() != short_title.lower():
            bill.add_title(short_title, "short title")

        # documents
        doc_links = html.xpath('//div[contains(@class,"insert-page")]//a')
        for link in doc_links:
            name = link.text_content().strip()
            href = link.get("href")
            if "Engrossment" in name or "Bill Text" in name or "Amendment" in name:
                bill.add_version_link(note=name, url=href, media_type="application/pdf")
            else:
                bill.add_document_link(
                    note=name, url=href, media_type="application/pdf"
                )

        def _split(string):
            return re.split(r"\w+[,|AND]\s+", string)

        # sponsors range from a committee to one legislator to a group of legs
        sponsor_lists = bill_tables[0].text_content().split("by")
        if len(sponsor_lists) > 1:
            for sponsors in sponsor_lists[1:]:
                if "COMMITTEE" in sponsors.upper():
                    bill.add_sponsorship(
                        name=sponsors.strip(),
                        entity_type="organization",
                        primary=True,
                        classification="primary",
                    )
                else:
                    for person in _split(sponsors):
                        person = person.strip()
                        if person != "":
                            bill.add_sponsorship(
                                classification="primary",
                                name=person,
                                entity_type="person",
                                primary=True,
                            )

        actor = chamber
        last_date = None
        # if a bill has passed a chamber or been 'received from'
        # then the next committee passage is in the opposite chamber
        has_moved_chambers = False
        for row in bill_tables[2]:
            # lots of empty rows
            if len(row) == 1:
                continue
            _, date, action, _ = [x.text_content().strip() for x in row]

            if date:
                last_date = date
            else:
                date = last_date
            date = datetime.datetime.strptime(
                date + "/" + session[0:4], "%m/%d/%Y"
            ).strftime("%Y-%m-%d")
            if action.startswith("House"):
                actor = "lower"
            elif action.startswith("Senate"):
                actor = "upper"

            # votes
            if "AYES" in action or "NAYS" in action:
                yield from self.parse_vote(
                    actor, date, row[2], session, bill_id, chamber, url
                )
                # bill.add_vote_event(vote)
            # some td's text is seperated by br elements
            if len(row[2]):
                action = "".join(row[2].itertext())
            action = action.replace("\xa0", " ").strip()
            # atype = get_action(actor, action)
            attrs = self.categorizer.categorize(action)
            atype = attrs["classification"]
            if atype and "passage" in atype:
                has_moved_chambers = True

            if atype and "committee-passage" in atype and has_moved_chambers:
                actor = _OTHER_CHAMBERS[actor]

            bill.add_action(action, date, chamber=actor, classification=atype)
            # after voice vote/roll call and some actions the bill is sent
            # 'to House' or 'to Senate'
            if "to House" in action:
                actor = "lower"
            elif "to Senate" in action:
                actor = "upper"
        yield bill

    def get_names(self, name_text):
        """both of these are unicode non-breaking spaces"""
        if name_text:
            name_text = name_text.replace("\xa0--\xa0", "")
            name_text = name_text.replace("\u00a0", " ")
            name_list = [
                name.replace("\u2013", "").strip()
                for name in name_text.split(",")
                if name
            ]
            name_list = [name.split("(")[0] for name in name_list]
            return name_list
        return []

    def parse_vote(self, actor, date, row, session, bill_id, bill_chamber, source):
        """
        takes the actor, date and row element and returns a Vote object
        """
        spans = row.xpath(".//span")
        motion = row.text.replace("\u00a0", " ").replace("-", "").strip()
        motion = motion if motion else "passage"
        passed, yes_count, no_count, other_count = (
            spans[0].text_content().rsplit("-", 3)
        )
        yes_votes = self.get_names(spans[1].tail)
        no_votes = self.get_names(spans[2].tail)

        other_votes = []
        for span in spans[3:]:
            if span.text.startswith(("Absent", "Excused")):
                other_votes += self.get_names(span.tail)
        for key, val in {"adopted": "pass", "passed": "pass", "failed": "fail"}.items():
            if key in passed.lower():
                passed = val
                break
        vote = VoteEvent(
            chamber=actor,
            start_date=date,
            motion_text=motion,
            bill=bill_id,
            bill_chamber=bill_chamber,
            result=passed,
            classification="passage",
            legislative_session=session,
        )
        vote.add_source(source)
        vote.set_count("yes", int(yes_count))
        vote.set_count("no", int(no_count))
        vote.set_count("absent", int(other_count))
        for name in yes_votes:
            if name and name != "None":
                vote.yes(name)
        for name in no_votes:
            if name and name != "None":
                vote.no(name)
        for name in other_votes:
            if name and name != "None":
                vote.vote("absent", name)
        yield vote
