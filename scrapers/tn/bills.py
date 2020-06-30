import datetime
import lxml.html
import re
from collections import namedtuple

from openstates.scrape import Bill, Scraper, VoteEvent


class Rule(namedtuple("Rule", "regex types stop attrs")):
    """If ``regex`` matches the action text, the resulting action's
    types should include ``types``.

    If stop is true, no other rules should be tested after this one;
    in other words, this rule conclusively determines the action's
    types and attrs.

    The resulting action should contain ``attrs``, which basically
    enables overwriting certain attributes, like the chamber if
    the action was listed in the wrong column.
    """

    def __new__(_cls, regex, types=None, stop=True, **kwargs):
        "Create new instance of Rule(regex, types, attrs, stop)"

        # Types can be a string or a sequence.
        if isinstance(types, str):
            types = set([types])
        types = set(types or [])

        # If no types are associated, assume that the categorizer
        # should continue looking at other rules.
        if not types:
            stop = False
        return tuple.__new__(_cls, (regex, types, stop, kwargs))


# These are regex patterns that map to action categories.
# TODO: Check that these are up to date
_categorizer_rules = (
    # Some actions are listed in the wrong chamber column.
    # Fix the chamber before moving on to the other rules.
    Rule(r"^H\.\s", stop=False, chamber="lower"),
    Rule(r"^S\.\s", stop=False, chamber="upper"),
    Rule(r"Signed by S(\.|enate) Speaker", chamber="upper"),
    Rule(r"Signed by H(\.|ouse) Speaker", chamber="lower"),
    # Extract the vote counts to help disambiguate chambers later.
    Rule(r"Ayes\s*(?P<yes_votes>\d+),\s*Nays\s*(?P<no_votes>\d+)", stop=False),
    # Committees
    Rule(r"(?i)ref\. to (?P<committees>.+?Comm\.)", "referral-committee"),
    Rule(r"^Failed In S\.(?P<committees>.+?Comm\.)", "committee-failure"),
    Rule(r"^Failed In s/c (?P<committees>.+)", "committee-failure"),
    Rule(
        r"Rcvd\. from H., ref\. to S\. (?P<committees>.+)",
        "referral-committee",
        chamber="upper",
    ),
    Rule(r"Placed on cal\. (?P<committees>.+?) for", stop=False),
    Rule(r"Taken off notice for cal in s/c (?P<committees>.+)"),
    Rule(r"to be heard in (?P<committees>.+?Comm\.)"),
    Rule(r"Action Def. in S. (?P<committees>.+?Comm.)", chamber="upper"),
    Rule(r"(?i)Placed on S. (?P<committees>.+?Comm\.) cal. for", chamber="upper"),
    Rule(r"(?i)Assigned to (?P<committees>.+?comm\.)"),
    Rule(r"(?i)Placed on S. (?P<committees>.+?Comm.) cal.", chamber="upper"),
    Rule(r"(?i)Taken off Notice For cal\. in s/c.+?\sof\s(?P<committees>.+?)"),
    Rule(r"(?i)Taken off Notice For cal\. in s/c.+?\sof\s(?P<committees>.+?)"),
    Rule(r"(?i)Taken off Notice For cal\. in[: ]+(?!s/c)(?P<committees>.+)"),
    Rule(r"(?i)Re-referred To:\s+(?P<committees>.+)", "referral-committee"),
    Rule(r"Recalled from S. (?P<committees>.+?Comm.)"),
    # Amendments
    Rule(r"^Am\..+?tabled", "amendment-deferral"),
    Rule(
        r"^Am\. withdrawn\.\(Amendment \d+ \- (?P<version>\S+)", "amendment-withdrawal"
    ),
    Rule(
        r"^Am\. reconsidered(, withdrawn)?\.\(Amendment \d \- (?P<version>.+?\))",
        "amendment-withdrawal",
    ),
    Rule(
        r"adopted am\.\(Amendment \d+ of \d+ - (?P<version>\S+)\)", "amendment-passage"
    ),
    Rule(r"refused to concur.+?in.+?am", "amendment-failure"),
    # Bill passage
    Rule(r"^Passed H\.", "passage", chamber="lower"),
    Rule(r"^Passed S\.", "passage", chamber="upper"),
    Rule(r"^Passed Senate", "passage", chamber="upper"),
    Rule(r"^R/S Adopted", "passage"),
    Rule(r"R/S Intro., adopted", "passage"),
    Rule(r"R/S Concurred", "passage"),
    # Veto
    Rule(r"(?i)veto", "executive-veto"),
    # The existing rules for TN categorization:
    Rule("Amendment adopted", "amendment-passage"),
    Rule("Amendment failed", "amendment-failure"),
    Rule("Amendment proposed", "amendment-introduction"),
    Rule("adopted am.", "amendment-passage"),
    Rule("Am. withdrawn", "amendment-withdrawal"),
    Rule("Divided committee report", "committee-passage"),
    Rule("Filed for intro.", ["introduction", "reading-1"]),
    # TN has a process where it's 'passed' on each reading,
    # Prior to committee referral/passage and chamber passage
    # see http://www.capitol.tn.gov/about/billtolaw.html
    # these don't fall under committee-passage or passage classifications
    Rule("Intro., P1C", ["introduction"]),
    Rule("Introduced, Passed on First Consideration", ["introduction"]),
    Rule("Reported back amended, do not pass", "committee-passage-unfavorable"),
    Rule("Reported back amended, do pass", "committee-passage-favorable"),
    Rule("Rec. For Pass.", "committee-passage-favorable"),
    Rule("Rec. For pass.", "committee-passage-favorable"),
    Rule("Rec. for pass.", "committee-passage-favorable"),
    Rule("Reported back amended, without recommendation", "committee-passage"),
    Rule("Reported back, do not pass", "committee-passage-unfavorable"),
    Rule("w/ recommend", "committee-passage-favorable"),
    Rule("Ref. to", "referral-committee"),
    Rule("ref. to", "referral-committee"),
    Rule("Assigned to", "referral-committee"),
    Rule("Received from House", "introduction"),
    Rule("Received from Senate", "introduction"),
    Rule("Adopted, ", ["passage"]),
    Rule("Concurred, ", ["passage"]),
    Rule("Passed H., ", ["passage"]),
    Rule("Passed S., ", ["passage"]),
    Rule("Second reading, adopted", ["passage", "reading-2"]),
    Rule("Second reading, failed", ["failure", "reading-2"]),
    Rule("Second reading, passed", ["passage", "reading-2"]),
    Rule("Transmitted to Gov. for action.", "executive-receipt"),
    Rule("Transmitted to Governor for his action.", "executive-receipt"),
    Rule("Signed by Governor, but item veto", "executive-veto-line-item"),
    Rule("Signed by Governor", "executive-signature"),
    Rule("Withdrawn", "withdrawal"),
    Rule("tabled", "amendment-deferral"),
    Rule("widthrawn", "amendment-withdrawal"),
    Rule(r"Intro", "introduction"),
)


def categorize_action(action):
    types = set()
    attrs = {}

    for rule in _categorizer_rules:

        # Try to match the regex.
        m = re.search(rule.regex, action)
        if m or (rule.regex in action):
            # If so, apply its associated types to this action.
            types |= rule.types

            # Also add its specified attrs.
            attrs.update(m.groupdict())
            attrs.update(rule.attrs)

            # Break if the rule says so, otherwise continue testing against
            # other rules.
            if rule.stop is True:
                break

    # Returns types, attrs
    return list(types), attrs


def actions_from_table(bill, actions_table):
    """
    """
    action_rows = actions_table.xpath("tr")

    # first row will say "Actions Taken on S|H(B|R|CR)..."
    if "Actions For S" in action_rows[0].text_content():
        chamber = "upper"
    else:
        chamber = "lower"

    for ar in action_rows[1:]:
        tds = ar.xpath("td")
        action_taken = tds[0].text
        strptime = datetime.datetime.strptime
        action_date = strptime(tds[1].text.strip(), "%m/%d/%Y").date()
        action_types, attrs = categorize_action(action_taken)
        # Overwrite any presumtive fields that are inaccurate, usually chamber.
        action = dict(
            action=action_taken,
            date=action_date,
            classification=action_types,
            chamber=chamber,
        )
        action.update(**attrs)

        # Finally, if a vote tally is given, switch the chamber.
        if set(["yes_votes", "no_votes"]) & set(attrs):
            total_votes = int(attrs["yes_votes"]) + int(attrs["no_votes"])
            # TODO: Should this be 33, or does it include other entities in the vote?
            if total_votes > 35:
                action["chamber"] = "lower"
            if total_votes <= 35:
                action["chamber"] = "upper"

        # TODO: Add `committees` scraped from the action using related_entities
        # Can we also make use of `version`?
        bill.add_action(
            action["action"],
            action["date"],
            chamber=action["chamber"],
            classification=action["classification"],
        )


# Map the OpenStates chamber identifier to TN bill prefixes for that chamber
CHAMBER_TO_PREFIXES = {
    # Senate Bill, Senate Joint Resolution, Senate Resolution
    "upper": ["SB", "SJR", "SR"],
    "lower": ["HB", "HJR", "HR"],
}

# Set of all prefixes so we can make sure we're not missing any
PREFIXES = {p for prefixes in CHAMBER_TO_PREFIXES.values() for p in prefixes}

# Bill listing is something like "BillIndex.aspx?StartNum=HB0001&EndNum=HB0100"
# This is meant to always return only one result, the prefix for this bill listing
BILL_LISTING_PREFIX_RE = re.compile(r"StartNum=([A-Z]{2,3})")


def listing_matches_chamber(listing, chamber):
    """ Returns True if the listing url matches the passed chamber

    This parses the URL to pull out the bill prefix (e.g. HB, SB, etc.), and uses some knowledge
    encoded in the constants above to say if it is a valid prefix for the chamber.

    This takes a conservative approach and raises an exception if
    * The match anything other than a single prefix in the URL
    * The matched prefix isn't in our list of known prefixes
    In these cases either the regex is broken or our list of prefixes is incomplete. An exception
    highlights either case for a quick fix.
    """
    (prefix,) = BILL_LISTING_PREFIX_RE.findall(listing)
    if prefix not in CHAMBER_TO_PREFIXES[chamber]:
        if prefix not in PREFIXES:
            raise Exception("Unknown bill prefix: {}".format(prefix))

        return False

    return True


class TNBillScraper(Scraper):
    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        self._seen_votes = set()
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        session_details = self.jurisdiction.sessions_by_id[session]

        # The index page gives us links to the paginated bill pages
        if session_details["classification"] == "special":
            index_page = "http://wapp.capitol.tn.gov/apps/indexes/SPSession1.aspx"
            xpath = '//h4[text()="{}"]/following-sibling::table[1]/tbody/tr/td/a'.format(
                session_details["_scraped_name"]
            )
        else:
            index_page = "http://wapp.capitol.tn.gov/apps/indexes/"
            xpath = '//td[contains(@class,"webindex")]/a'

        index_list_page = self.get(index_page).text

        index_list_page = lxml.html.fromstring(index_list_page)
        index_list_page.make_links_absolute(index_page)

        for bill_listing in index_list_page.xpath(xpath):

            bill_listing = bill_listing.attrib["href"]

            if not listing_matches_chamber(bill_listing, chamber):
                self.logger.info(
                    "Skipping bill listing '{bill_listing}' "
                    "Does not match chamber '{chamber}'".format(
                        bill_listing=bill_listing, chamber=chamber
                    )
                )
                continue

            bill_list_page = self.get(bill_listing).text

            bill_list_page = lxml.html.fromstring(bill_list_page)
            bill_list_page.make_links_absolute(bill_listing)

            for bill_link in set(
                bill_list_page.xpath(
                    '//h1[text()="Legislation"]/following-sibling::div/'
                    "div/div/div//a/@href"
                )
            ):
                bill = self.scrape_bill(session, bill_link)
                if bill:
                    yield bill

    def scrape_bill(self, session, bill_url):
        page = self.get(bill_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(bill_url)

        try:
            bill_id = page.xpath('//span[@id="lblBillNumber"]/a[1]')[0].text
        except IndexError:
            self.logger.warning("Something is wrong with bill page, skipping.")
            return
        secondary_bill_id = page.xpath('//span[@id="lblCompNumber"]/a[1]')

        # checking if there is a matching bill
        if secondary_bill_id:
            secondary_bill_id = secondary_bill_id[0].text
            # swap ids if * is in secondary_bill_id
            if "*" in secondary_bill_id:
                bill_id, secondary_bill_id = secondary_bill_id, bill_id
                secondary_bill_id = secondary_bill_id.strip()
            secondary_bill_id = secondary_bill_id.replace("  ", " ")

        bill_id = bill_id.replace("*", "").replace("  ", " ").strip()

        if "B" in bill_id:
            bill_type = "bill"
        elif "JR" in bill_id:
            bill_type = "joint resolution"
        elif "R" in bill_id:
            bill_type = "resolution"

        primary_chamber = "lower" if "H" in bill_id else "upper"
        # secondary_chamber = 'upper' if primary_chamber == 'lower' else 'lower'

        title = page.xpath("//span[@id='lblAbstract']")[0].text
        if title is None:
            msg = "%s detail page was missing title info."
            self.logger.warning(msg % bill_id)
            return

        # bill subject
        subject_pos = title.find("-")
        subjects = [s.strip() for s in title[: subject_pos - 1].split(",")]
        subjects = filter(None, subjects)

        bill = Bill(
            bill_id,
            legislative_session=session,
            chamber=primary_chamber,
            title=title,
            classification=bill_type,
        )
        for subject in subjects:
            bill.add_subject(subject)

        if secondary_bill_id:
            bill.add_identifier(secondary_bill_id)

        if page.xpath('//span[@id="lblCompNumber"]/a'):
            companion_id = (
                page.xpath('//span[@id="lblCompNumber"]/a')[0].text_content().strip()
            )
            bill.add_related_bill(
                identifier=companion_id,
                legislative_session=session,
                relation_type="companion",
            )

        bill.add_source(bill_url)

        # Primary Sponsor
        sponsor = (
            page.xpath("//span[@id='lblBillPrimeSponsor']")[0]
            .text_content()
            .split("by")[-1]
        )
        sponsor = sponsor.replace("*", "").strip()
        if sponsor:
            bill.add_sponsorship(
                sponsor, classification="primary", entity_type="person", primary=True
            )

        # bill text
        btext = page.xpath("//span[@id='lblBillNumber']/a")[0]
        bill.add_version_link(
            "Current Version", btext.get("href"), media_type="application/pdf"
        )

        # documents
        summary = page.xpath('//a[contains(@href, "BillSummaryArchive")]')
        if summary:
            bill.add_document_link("Summary", summary[0].get("href"))
        fiscal = page.xpath('//span[@id="lblFiscalNote"]//a')
        if fiscal:
            bill.add_document_link("Fiscal Note", fiscal[0].get("href"))
        amendments = page.xpath('//a[contains(@href, "/Amend/")]')
        for amendment in amendments:
            bill.add_version_link("Amendment " + amendment.text, amendment.get("href"), media_type="application/pdf")
        # amendment notes in image with alt text describing doc inside <a>
        amend_fns = page.xpath('//img[contains(@alt, "Fiscal Memo")]')
        for afn in amend_fns:
            bill.add_document_link(
                afn.get("alt"), afn.getparent().get("href"), on_duplicate="ignore"
            )

        # actions
        atable = page.xpath("//table[@id='gvBillActionHistory']")[0]
        actions_from_table(bill, atable)

        # if there is a matching bill
        if secondary_bill_id:
            # secondary sponsor
            secondary_sponsor = (
                page.xpath("//span[@id='lblCompPrimeSponsor']")[0]
                .text_content()
                .split("by")[-1]
            )
            secondary_sponsor = (
                secondary_sponsor.replace("*", "").replace(")", "").strip()
            )
            # Skip black-name sponsors.
            if secondary_sponsor:
                bill.add_sponsorship(
                    secondary_sponsor,
                    classification="primary",
                    entity_type="person",
                    primary=True,
                )

            # secondary actions
            if page.xpath("//table[@id='gvCoActionHistory']"):
                cotable = page.xpath("//table[@id='gvCoActionHistory']")[0]
                actions_from_table(bill, cotable)

        # votes
        yield from self.scrape_vote_events(bill, page, bill_url)

        bill.actions.sort(key=lambda a: a["date"])
        yield bill

    def scrape_vote_events(self, bill, page, link):
        chamber_labels = (("lower", "lblHouseVoteData"), ("upper", "lblSenateVoteData"))
        for chamber, element_id in chamber_labels:
            raw_vote_data = page.xpath("//*[@id='{}']".format(element_id))[
                0
            ].text_content()
            votes = self.scrape_votes_for_chamber(chamber, raw_vote_data, bill, link)
            for vote in votes:
                yield vote

    def scrape_votes_for_chamber(self, chamber, vote_data, bill, link):
        raw_vote_data = re.split(r"\w+? by [\w ]+?\s+-", vote_data.strip())[1:]

        motion_count = 1

        for raw_vote in raw_vote_data:
            raw_vote = raw_vote.split(u"\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0")
            motion = raw_vote[0]

            vote_date = re.search(r"(\d+/\d+/\d+)", motion)
            if vote_date:
                vote_date = datetime.datetime.strptime(vote_date.group(), "%m/%d/%Y")

            passed = (
                "Passed" in motion
                or "Recommended for passage" in motion
                or "Rec. for pass" in motion
                or "Adopted" in raw_vote[1]
            )
            vote_regex = re.compile(r"\d+$")
            aye_regex = re.compile(r"^.+voting aye were: (.+) -")
            no_regex = re.compile(r"^.+voting no were: (.+) -")
            not_voting_regex = re.compile(r"^.+present and not voting were: (.+) -")
            yes_count = 0
            no_count = 0
            not_voting_count = 0
            ayes = []
            nos = []
            not_voting = []

            for v in raw_vote[1:]:
                v = v.strip()
                if v.startswith("Ayes...") and vote_regex.search(v):
                    yes_count = int(vote_regex.search(v).group())
                elif v.startswith("Noes...") and vote_regex.search(v):
                    no_count = int(vote_regex.search(v).group())
                elif v.startswith("Present and not voting...") and vote_regex.search(v):
                    not_voting_count += int(vote_regex.search(v).group())
                elif aye_regex.search(v):
                    ayes = aye_regex.search(v).groups()[0].split(", ")
                elif no_regex.search(v):
                    nos = no_regex.search(v).groups()[0].split(", ")
                elif not_voting_regex.search(v):
                    not_voting += not_voting_regex.search(v).groups()[0].split(", ")

            motion = motion.strip()
            motion = motion.replace("&AMP;", "&")  # un-escape ampersands
            if motion in self._seen_votes:
                motion = "{} ({})".format(motion, motion_count)
                motion_count += 1
            self._seen_votes.add(motion)

            vote = VoteEvent(
                motion_text=motion,
                start_date=vote_date.strftime("%Y-%m-%d") if vote_date else None,
                classification="passage",
                result="pass" if passed else "fail",
                chamber=chamber,
                bill=bill,
            )
            vote.set_count("yes", yes_count)
            vote.set_count("no", no_count)
            vote.set_count("not voting", not_voting_count)
            vote.add_source(link)

            seen = set()
            for a in ayes:
                if a in seen:
                    continue
                vote.yes(a)
                seen.add(a)
            for n in nos:
                if n in seen:
                    continue
                vote.no(n)
                seen.add(n)
            for n in not_voting:
                if n in seen:
                    continue
                vote.vote("not voting", n)
                seen.add(n)

            yield vote
