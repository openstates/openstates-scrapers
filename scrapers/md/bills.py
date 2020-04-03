import re
import datetime
import pytz

import lxml.html
from openstates.scrape import Scraper, Bill, VoteEvent

from openstates.utils import convert_pdf

# http://mgaleg.maryland.gov/mgawebsite/Legislation/Details/hb0060?ys=2019RS&search=True
# # passed all

# search for tax
# http://mgaleg.maryland.gov/mgawebsite/Search/FullText?category=legislation-documents-legislation-bills-and-resolutions&dropXSL=no&isadvanced=&rpp=500&pr=mgasearch&query=tax&order=r&af1like=2019rs&notq=#full-text-search-results-complete

classifiers = {
    r"Committee Amendment .+? Adopted": "amendment-passage",
    r"Favorable": "committee-passage-favorable",
    r"First Reading": "referral-committee",
    r"Floor (Committee )?Amendment\s?\(.+?\)$": "amendment-introduction",
    r"Floor Amendment .+? Rejected": "amendment-failure",
    r"Floor (Committee )?Amendment.+?Adopted": "amendment-passage",
    r"Floor Amendment.+? Withdrawn": "amendment-withdrawal",
    r"Pre\-filed": "introduction",
    r"Withdrawn": "withdrawal",
    r"Re\-(referred|assigned)": "referral-committee",
    r"Recommit to Committee": "referral-committee",
    r"Referred": "referral-committee",
    r"Third Reading Passed": "passage",
    r"Third Reading Failed": "failure",
    r"Unfavorable": "committee-passage-unfavorable",
    r"Vetoed": "executive-veto",
    r"Gubernatorial Veto Override": "veto-override-passage",
    r"Veto overridden": "veto-override-passage",
    r"Approved by the Governor": "executive-signature",
}

vote_classifiers = {r"third": "passage", r"fla|amend|amd": "amendment"}


def _classify_action(action):
    if not action:
        return None

    ctty = None

    for regex, type in classifiers.items():
        if re.match(regex, action):
            if "referral-committee" in type:
                ctty = re.sub(regex, "", action).strip()
            return (type, ctty)
    return (None, ctty)


class MDBillScraper(Scraper):
    _TZ = pytz.timezone("US/Eastern")
    BASE_URL = "http://mgaleg.maryland.gov/mgawebsite/"
    CHAMBERS = {"upper": "senate", "lower": "house"}

    SESSION_IDS = {"2020": "2020rs"}

    def parse_bill_votes(self, doc, bill):
        elems = doc.xpath("//a")

        # MD has a habit of listing votes twice
        seen_votes = set()

        for elem in elems:
            href = elem.get("href")
            if (
                href
                and "votes" in href
                and href.endswith("htm")
                and href not in seen_votes
            ):
                seen_votes.add(href)
                vote = self.parse_vote_page(href, bill)
                vote.add_source(href)
                yield vote

    def parse_bill_votes_new(self, doc, bill):
        elems = doc.xpath("//table[@class='billdocs']//a")
        # MD has a habit of listing votes twice
        seen_votes = set()

        for elem in elems:
            href = elem.get("href")
            if (
                href
                and "votes" in href
                and href.endswith("pdf")
                and ("Senate" in href or "House" in href)
                and href not in seen_votes
            ):
                seen_votes.add(href)
                vote = self.parse_vote_pdf(href, bill)
                vote.add_source(href)
                yield vote

    def parse_vote_pdf(self, vote_url, bill):

        filename, response = self.urlretrieve(vote_url)

        text = convert_pdf(filename, type="text").decode()
        lines = text.splitlines()

        if "Senate" in vote_url:
            chamber = "upper"
        else:
            chamber = "lower"

        date_string = lines[0].split("Calendar Date:")[1].strip()
        date = datetime.datetime.strptime(date_string, "%b %d, %Y %I:%M (%p)")

        page_index = None
        for index, line in enumerate(lines):
            if "Yeas" in line and "Nays" in line:
                page_index = index
                break

        vote_counts = 5 * [0]
        vote_types = ["yes", "no", "not voting", "excused", "absent"]

        if page_index:

            counts = re.split(r"\s{2,}", lines[page_index].strip())

            for index, count in enumerate(counts):
                number, string = count.split(" ", 1)
                number = int(number)
                vote_counts[index] = number
        else:
            raise ValueError("Vote Counts Not found at %s" % vote_url)

        passed = vote_counts[0] > vote_counts[1]

        # Consent calendar votes address multiple bills in one VoteEvent
        # eg, http://mgaleg.maryland.gov/2018RS/votes/Senate/0478.pdf
        is_consent_calendar = any(
            ["Consent Calendar" in line for line in lines[:page_index]]
        )
        consent_calendar_bills = None
        motion = ""
        if is_consent_calendar:
            motion = re.split(r"\s{2,}", lines[page_index - 4].strip())[0]
            consent_calendar_bills = re.split(r"\s{2,}", lines[page_index - 1].strip())
            assert (
                consent_calendar_bills
            ), "Could not find bills for consent calendar vote"

        motion_keywords = [
            "favorable",
            "reading",
            "amendment",
            "motion",
            "introduced",
            "bill pass",
            "committee",
        ]
        motion_lines = [
            3,
            2,
            4,
            5,
        ]  # Relative LineNumbers to be checked for existence of motion

        for i in motion_lines:
            if any(
                motion_keyword in motion.lower() for motion_keyword in motion_keywords
            ):
                break
            motion = re.split(r"\s{2,}", lines[page_index - i].strip())[0]
        else:
            if not any(
                motion_keyword in motion.lower() for motion_keyword in motion_keywords
            ):
                # This condition covers for the bad formating in SB 1260
                motion = lines[page_index - 3]
            if not any(
                motion_keyword in motion.lower() for motion_keyword in motion_keywords
            ):
                # Check this one for SB 747
                motion = "No motion given"
                self.warning("No motion given")

        vote = VoteEvent(
            bill=bill,
            chamber=chamber,
            start_date=date.strftime("%Y-%m-%d"),
            motion_text=motion,
            classification="passage",
            result="pass" if passed else "fail",
        )

        # Include bill ID to avoid duplication for consent calendars
        vote.pupa_id = "{}#{}".format(vote_url, bill.identifier)

        for index, vote_type in enumerate(vote_types):
            vote.set_count(vote_type, vote_counts[index])
        page_index = page_index + 2

        # Keywords for identifying where names are located in the pdf
        show_stoppers = [
            "Voting Nay",
            "Not Voting",
            "COPY",
            "Excused",
            "indicates vote change",
            "Indicates Vote Change",
        ]
        vote_index = 0

        # For matching number of names extracted with vote counts(extracted independently)
        vote_name_counts = 5 * [0]

        while page_index < len(lines):

            current_line = lines[page_index].strip()

            if not current_line or "Voting Yea" in current_line:
                page_index += 1
                continue

            if any(show_stopper in current_line for show_stopper in show_stoppers):
                page_index += 1
                vote_index = vote_index + 1
                continue

            names = re.split(r"\s{2,}", current_line)

            vote_name_counts[vote_index] += len(names)

            for name in names:
                vote.vote(vote_types[vote_index], name)
            page_index += 1

        if vote_counts != vote_name_counts:
            raise ValueError("Votes Count and Number of Names don't match")

        return vote

    def parse_vote_page(self, vote_url, bill):
        vote_html = self.get(vote_url).text
        doc = lxml.html.fromstring(vote_html)
        # chamber
        if "senate" in vote_url:
            chamber = "upper"
        else:
            chamber = "lower"

        # date in the following format: Mar 23, 2009
        date = doc.xpath('//td[starts-with(text(), "Legislative")]')[0].text
        date = date.replace(u"\xa0", " ")
        date = datetime.datetime.strptime(date[18:], "%b %d, %Y")

        # motion
        motion = "".join(x.text_content() for x in doc.xpath('//td[@colspan="23"]'))
        if motion == "":
            motion = "No motion given"  # XXX: Double check this. See SJ 3.
        motion = motion.replace(u"\xa0", " ")

        # totals
        tot_class = doc.xpath('//td[contains(text(), "Yeas")]')[0].get("class")
        totals = doc.xpath('//td[@class="%s"]/text()' % tot_class)[1:]
        yes_count = int(totals[0].split()[-1])
        no_count = int(totals[1].split()[-1])
        other_count = int(totals[2].split()[-1])
        other_count += int(totals[3].split()[-1])
        other_count += int(totals[4].split()[-1])
        passed = yes_count > no_count

        vote = VoteEvent(
            bill=bill,
            chamber=chamber,
            start_date=date.strftime("%Y-%m-%d"),
            motion_text=motion,
            classification="passage",
            result="pass" if passed else "fail",
        )
        vote.pupa_id = vote_url  # contains sequence number
        vote.set_count("yes", yes_count)
        vote.set_count("no", no_count)
        vote.set_count("other", other_count)

        # go through, find Voting Yea/Voting Nay/etc. and next tds are voters
        func = None
        for td in doc.xpath("//td/text()"):
            td = td.replace(u"\xa0", " ")
            if td.startswith("Voting Yea"):
                func = vote.yes
            elif td.startswith("Voting Nay"):
                func = vote.no
            elif td.startswith("Not Voting"):
                func = vote.other
            elif td.startswith("Excused"):
                func = vote.other
            elif func:
                td = td.rstrip("*")
                func(td)

        return vote

    def scrape_bill_actions(self, bill, page):
        chamber_map = {"Senate": "upper", "House": "lower", "Post Passage": "executive"}
        for row in page.xpath('//table[@id="detailsHistory"]/tbody/tr'):
            # actions have something in the first column
            potential_chamber = row.xpath("td[1]/text()")
            if len(potential_chamber) > 0:
                chamber = chamber_map[potential_chamber[0].strip()]
                action_date = row.xpath("td[2]/text()")[0].strip()
                # self._TZ.localize(
                action_date = datetime.datetime.strptime(action_date, "%m/%d/%Y")
                action_text = row.xpath("td[4]/text()")[0].strip()
                atype, committee = _classify_action(action_text)
                related = (
                    [{"type": "committee", "name": committee}]
                    if committee is not None
                    else []
                )
                bill.add_action(
                    action_text,
                    action_date.strftime("%Y-%m-%d"),
                    chamber=chamber,
                    classification=atype,
                    related_entities=related,
                )
            elif row.xpath("td[4]/a"):
                link = row.xpath("td[4]/a")[0]
                link_text = link.text_content().strip()
                if link_text.startswith("Text"):
                    link_text = link_text.replace("Text - ", "")
                    bill.add_version_link(
                        link_text,
                        link.get("href"),
                        media_type="application/pdf",
                        on_duplicate="ignore",
                    )

    def scrape_bill_subjects(self, bill, page):
        # TODO: this xpath gets both 'subjects' and 'file codes'
        # they both link to subjects on the site and seem to fit the definition of subject
        for row in page.xpath(
            '//a[contains(@href, "/Legislation/SubjectIndex/annotac")]/text()'
        ):
            bill.add_subject(row[0])

    def scrape_bill_sponsors(self, bill, page):
        # TODO: Committees
        sponsors = page.xpath(
            '//dt[contains(text(), "Sponsored by")]/following-sibling::dd[1]/text()'
        )[0].strip()

        sponsors = sponsors.replace("Delegates ", "")
        sponsors = sponsors.replace("Delegate ", "")
        sponsors = sponsors.replace("Senator ", "")
        sponsors = sponsors.replace("Senators ", "")
        sponsor_type = "primary"

        for sponsor in re.split(", (?:and )?", sponsors):
            sponsor = sponsor.strip()
            if not sponsor:
                continue
            bill.add_sponsorship(
                sponsor,
                sponsor_type,
                primary=sponsor_type == "primary",
                entity_type="person",
            )

    def scrape_bill(self, chamber, session, url):
        html = self.get(url).content
        page = lxml.html.fromstring(html)
        page.make_links_absolute(self.BASE_URL)

        if page.xpath('//h2[@style="font-size:1.3rem;"]/a[1]/text()'):
            bill_id = page.xpath('//h2[@style="font-size:1.3rem;"]/a[1]/text()')[
                0
            ].strip()
        elif page.xpath('//h2[@style="font-size:1.3rem;"]/text()'):
            bill_id = page.xpath('//h2[@style="font-size:1.3rem;"]/text()')[0].strip()
        else:
            self.warning("No bill id for {}".format(url))
            return
        title = page.xpath(
            '//dt[contains(text(), "Title")]/following-sibling::dd[1]/text()'
        )[0].strip()

        if "B" in bill_id:
            _type = ["bill"]
        elif "J" in bill_id:
            _type = ["joint resolution"]
        else:
            raise ValueError("unknown bill type " + bill_id)

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=chamber,
            title=title,
            classification=_type,
        )
        bill.add_source(url)

        self.scrape_bill_subjects(bill, page)
        self.scrape_bill_sponsors(bill, page)
        self.scrape_bill_actions(bill, page)

        # fiscal note
        if page.xpath('//dt[contains(text(), "Analysis")]/following-sibling::dd[1]/a'):
            fiscal_note = page.xpath(
                '//dt[contains(text(), "Analysis")]/following-sibling::dd[1]/a'
            )[0]
            fiscal_url = fiscal_note.get("href")
            fiscal_title = fiscal_note.text_content()
            bill.add_document_link(
                fiscal_title, fiscal_url, media_type="application/pdf",
            )

        # yield from self.parse_bill_votes_new(doc, bill)
        yield bill

    def remove_leading_dash(self, string):
        string = string[3:] if string.startswith(" - ") else string
        return string.strip()

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        session_slug = session if "s" in session else session + "RS"

        list_url = "http://mgaleg.maryland.gov/mgawebsite/Legislation/Index/{}?ys={}".format(
            self.CHAMBERS[chamber], session_slug
        )

        list_html = self.get(list_url).content
        page = lxml.html.fromstring(list_html)
        page.make_links_absolute(self.BASE_URL)

        # despite only showing one page to the browser,
        # all the bills are conveniently in the markup
        for row in page.xpath('//table[@id="billIndex"]/tbody/tr'):
            url = row.xpath("td[1]/a[1]/@href")[0]
            yield from self.scrape_bill(chamber, session, url)
