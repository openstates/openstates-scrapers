import os
import re
import pytz
import datetime
from lxml import etree, html
from utils import LXMLMixin
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from openstates.scrape import Scraper, Bill, VoteEvent
from .models import CABill, CALocation
from .actions import CACategorizer

SPONSOR_TYPES = {
    "LEAD_AUTHOR": "author",
    "COAUTHOR": "coauthor",
    "PRINCIPAL_COAUTHOR": "principal coauthor",
}

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")


def clean_title(s):
    # replace smart quote characters
    s = s.replace("\xe2\u20ac\u201c", "-")

    # Cesar Chavez e
    s = s.replace("\xc3\xa9", "\u00E9")
    # Cesar Chavez a
    s = s.replace("\xc3\xa1", "\u00E1")
    s = s.replace("\xe2\u20ac\u201c", "\u2013")

    s = re.sub(r"[\u2018\u2019]", "'", s)
    s = re.sub(r"[\u201C\u201D]", '"', s)
    s = re.sub("\u00e2\u20ac\u2122", "'", s)
    s = re.sub(r"\xe2\u20ac\u02dc", "'", s)
    return s


# Committee abbreviations in action text, e.g. "Com. on APPR.",
# "Coms. on L. GOV. and PUB. S.", "Referred to APPR. suspense file."
_abbr_token = r"[A-Z0-9&.,'/-]+(?![a-z])"
_abbr = rf"{_abbr_token}(?: {_abbr_token})*"
committee_abbr_re = re.compile(
    rf"(?:Coms?\. on|Referred to|re-refer(?:red)? to|in) ({_abbr}(?: and {_abbr})*)"
)


def abbr_matches_name(abbr, name):
    """Each part of the abbreviation spells, in order, letters of the
    corresponding word of the name: "B. & F. R." / "Budget and Fiscal Review",
    "RLS." / "Rules", "L., P.E. & R." / "Labor, Public Employment and Retirement".
    """
    parts = [p for p in re.split(r"[\s.,&/]+", abbr.upper()) if p and p != "AND"]
    words = [
        w
        for w in re.split(r"[\s,&]+", name.upper())
        if w and w not in ("AND", "OF", "THE")
    ]
    if not parts or len(parts) != len(words):
        return False
    for part, word in zip(parts, words):
        letters = iter(word)
        if part[0] != word[0] or not all(c in letters for c in part):
            return False
    return True


class CABillScraper(Scraper, LXMLMixin):
    categorizer = CACategorizer()

    _tz = pytz.timezone("US/Pacific")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        host = kwargs.pop("host", MYSQL_HOST)
        user = kwargs.pop("user", MYSQL_USER)
        pw = kwargs.pop("pw", MYSQL_PASSWORD)

        if (user is not None) and (pw is not None):
            conn_str = "mysql://%s:%s@" % (user, pw)
        else:
            conn_str = "mysql://"
        conn_str = "%s%s/%s?charset=utf8" % (
            conn_str,
            host,
            kwargs.pop("db", "capublic"),
        )
        self.engine = create_engine(conn_str)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self._committee_codes = {}
        self._unmatched_abbrs = set()

    def committee_codes(self, session):
        """Committee names by code from location_code_tbl (codes CS*/CX*)."""
        if session not in self._committee_codes:
            self._committee_codes[session] = {
                loc.location_code: loc.long_description.strip()
                for loc in self.session.query(CALocation).filter_by(
                    session_year=session
                )
                if re.fullmatch(r"C[SX]\d+", loc.location_code or "")
            }
        return self._committee_codes[session]

    def match_committee_list(self, pieces, names):
        """Match ", "-separated pieces to names; commas also occur inside
        abbreviations ("L., P.E. & R."), so try the longest pieces first."""
        if not pieces:
            return []
        for i in range(len(pieces), 0, -1):
            found = {n for n in names if abbr_matches_name(", ".join(pieces[:i]), n)}
            if len(found) == 1:
                rest = self.match_committee_list(pieces[i:], names)
                if rest is not None:
                    return [found.pop()] + rest
        return None

    def action_committees(self, action, session):
        """Return (committee names, unmatched abbreviations) for an action."""
        prefix = {"Senate": "CS", "Assembly": "CX"}.get(action.primary_location, "C")
        names = {
            n for c, n in self.committee_codes(session).items() if c.startswith(prefix)
        }
        matched, unmatched = [], []
        text = re.sub(r"\s+", " ", action.action)
        for m in committee_abbr_re.finditer(text):
            for abbr in m.group(1).split(" and "):
                abbr = abbr.strip(" ,")
                if not re.search(r"[A-Z]{2}|[A-Z]\.", abbr) or re.fullmatch(
                    r"[A-Z]{1,2}\d+|\d.*", abbr
                ):
                    continue
                found = self.match_committee_list(abbr.split(", "), names)
                if found is None:
                    unmatched.append(abbr)
                else:
                    matched.extend(found)
        return matched, unmatched

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.jurisdiction.legislative_sessions[-1]["identifier"]
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        bill_types = {
            "lower": {
                "AB": "bill",
                "ACA": "constitutional amendment",
                "ACR": "concurrent resolution",
                "AJR": "joint resolution",
                "HR": "resolution",
            },
            "upper": {
                "SB": "bill",
                "SCA": "constitutional amendment",
                "SCR": "concurrent resolution",
                "SJR": "joint resolution",
                "SR": "resolution",
                "GRP": "bill",
            },
        }

        for chamber in chambers:
            for abbr, type_ in bill_types[chamber].items():
                try:
                    yield from self.scrape_bill_type(chamber, session, type_, abbr)
                except (StopIteration, RuntimeError):
                    continue

    def scrape_bill_type(
        self,
        chamber,
        session,
        bill_type,
        type_abbr,
    ):
        bills = (
            self.session.query(CABill)
            .filter_by(session_year=session)
            .filter_by(measure_type=type_abbr)
        )

        archive_year = int(session[0:4])
        not_archive_year = archive_year >= 2009

        for bill in bills:
            bill_session = session
            if bill.session_num != "0":
                bill_session += " Special Session %s" % bill.session_num

            bill_id = bill.short_bill_id
            if bill_id.strip() == "SB77" and session == "20052006":
                continue

            fsbill = Bill(bill_id, bill_session, title="", chamber=chamber)
            if (bill_id.startswith("S") and chamber == "lower") or (
                bill_id.startswith("A") and chamber == "upper"
            ):
                print("!!!! BAD ID/CHAMBER PAIR !!!!", bill)
                continue

            # Construct a fake source url
            source_url = (
                "http://leginfo.legislature.ca.gov/faces/"
                "billNavClient.xhtml?bill_id=%s"
            ) % bill.bill_id

            fsbill.add_source(source_url)
            fsbill.add_version_link(bill_id, source_url, media_type="text/html")

            title = ""
            type_ = ["bill"]
            subject = ""
            all_titles = set()
            summary = ""

            # Get digest test (aka "summary") from latest version.
            if bill.versions and not_archive_year:
                version = bill.versions[-1]
                nsmap = version.xml.nsmap
                xpath = "//caml:DigestText/xhtml:p"
                els = version.xml.xpath(xpath, namespaces=nsmap)
                chunks = []
                for el in els:
                    t = etree_text_content(el)
                    t = re.sub(r"\s+", " ", t)
                    t = re.sub(r"\)(\S)", lambda m: ") %s" % m.group(1), t)
                    chunks.append(t)
                summary = "\n\n".join(chunks)

            for version in bill.versions:
                if not version.bill_xml:
                    continue

                version_date = self._tz.localize(version.bill_version_action_date)

                # create a version name to match the state's format
                # 02/06/17 - Enrolled
                version_date_human = version_date.strftime("%m/%d/%y")
                version_name = "{} - {}".format(
                    version_date_human, version.bill_version_action
                )

                version_base = "https://leginfo.legislature.ca.gov/faces"

                version_url_pdf = "{}/billPdf.xhtml?bill_id={}&version={}".format(
                    version_base, version.bill_id, version.bill_version_id
                )

                fsbill.add_version_link(
                    version_name,
                    version_url_pdf,
                    media_type="application/pdf",
                    date=version_date.date(),
                )

                # CA is inconsistent in that some bills have a short title
                # that is longer, more descriptive than title.
                if bill.measure_type in ("AB", "SB"):
                    impact_clause = clean_title(version.title)
                    title = clean_title(version.short_title)
                else:
                    impact_clause = None
                    if len(version.title) < len(
                        version.short_title
                    ) and not version.title.lower().startswith("an act"):
                        title = clean_title(version.short_title)
                    else:
                        title = clean_title(version.title)

                if title:
                    all_titles.add(title)

                type_ = [bill_type]

                if version.appropriation == "Yes":
                    type_.append("appropriation")

                tags = []
                if version.fiscal_committee == "Yes":
                    tags.append("fiscal committee")
                if version.local_program == "Yes":
                    tags.append("local program")
                if version.urgency == "Yes":
                    tags.append("urgency")
                if version.taxlevy == "Yes":
                    tags.append("tax levy")

                if version.subject:
                    cleaned_subjects = clean_title(version.subject)
                    # one has a super long subject, trims last few characters so still makes sense
                    if bill_id.strip() == "SB867" and session == "20232024":
                        subject = [cleaned_subjects[0:-9]]
                    # another has a colon at the end instead of a period & verify flags an empty string list item later
                    elif bill_id.strip() == "SB1211" and session == "20232024":
                        subject = cleaned_subjects[0:-2].split(": ")
                    # break up subject to actually be a list of them instead of one long string
                    else:
                        subject = (
                            cleaned_subjects.replace(".", "")
                            .replace(" ", "")
                            .split(":")
                        )
                        subject = [sub for sub in subject if len(sub) != 0]

            if not title:
                self.warning("Couldn't find title for %s, skipping" % bill_id)
                continue

            fsbill.title = title
            if summary:
                fsbill.add_abstract(summary, note="summary")
            fsbill.classification = type_
            fsbill.subject = [*set(subject)] if subject else []
            fsbill.extras["impact_clause"] = impact_clause
            fsbill.extras["tags"] = tags

            # We don't want the current title in alternate_titles
            all_titles.remove(title)

            for title in all_titles:
                fsbill.add_title(title)

            for author in version.authors:
                fsbill.add_sponsorship(
                    author.name,
                    classification=SPONSOR_TYPES[author.contribution],
                    primary=author.primary_author_flg == "Y",
                    entity_type="person",
                )
                # fsbill.sponsorships[-1]['extras'] = {'official_type': author.contribution}

            seen_actions = set()
            codes = self.committee_codes(session)
            prev_code = code = None
            for action in bill.actions:
                prev_code, code = code, action.ternary_location
                if not action.action:
                    # NULL action text seems to be an error on CA's part,
                    # unless it has some meaning I'm missing
                    continue
                actor = action.actor or chamber
                actor = actor.strip()
                match = re.match(r"(Assembly|Senate)($| \(Floor)", actor)
                if match:
                    actor = {"Assembly": "lower", "Senate": "upper"}[match.group(1)]
                elif actor.startswith("Governor"):
                    actor = "executive"
                else:

                    def replacer(matchobj):
                        if matchobj:
                            return {"Assembly": "lower", "Senate": "upper"}[
                                matchobj.group()
                            ]
                        else:
                            return matchobj.group()

                    actor = re.sub(r"^(Assembly|Senate)", replacer, actor)

                type_ = []

                act_str = action.action
                act_str = re.sub(r"\s+", " ", act_str)

                attrs = self.categorizer.categorize(act_str)

                kwargs = attrs
                committees, unmatched = self.action_committees(action, session)
                for abbr in unmatched:
                    if abbr not in self._unmatched_abbrs:
                        self._unmatched_abbrs.add(abbr)
                        self.warning("no committee matches %r in %r", abbr, act_str)
                if not committees and not unmatched:
                    # The row's location code is the committee the bill is in
                    # after the action; "From committee" rows that send it to
                    # the floor have none, so take the previous row's.
                    if act_str.startswith(("In committee", "Set for hearing")):
                        committees = [codes[code]] if code in codes else []
                    elif act_str.startswith("From committee"):
                        loc = code if code in codes else prev_code
                        committees = [codes[loc]] if loc in codes else []
                if unmatched or not committees:
                    committees += kwargs.get("committees", [])

                # Determine which chamber the action originated from.
                changed = False
                for committee_chamber in ["upper", "lower", "legislature"]:
                    if actor.startswith(committee_chamber):
                        actor = committee_chamber
                        changed = True
                        break
                if not changed:
                    actor = "legislature"

                if actor != action.actor:
                    actor_info = kwargs.get("actor_info", {})
                    actor_info["details"] = action.actor
                    kwargs["actor_info"] = actor_info

                # Add strings for related legislators, if any.
                rgx = r"(?:senator|assembly[mwp][^ .,:;]+)\s+[^ .,:;]+"
                legislators = re.findall(rgx, action.action, re.I)
                if legislators:
                    kwargs["legislators"] = legislators

                date = action.action_date
                date = self._tz.localize(date)
                date = date.date()
                if (actor, act_str, date) in seen_actions:
                    continue

                action = fsbill.add_action(
                    act_str,
                    date.strftime("%Y-%m-%d"),
                    chamber=actor,
                    classification=kwargs["classification"],
                )
                for committee in dict.fromkeys(committees):
                    action.add_related_entity(committee, entity_type="organization")
                seen_actions.add((actor, act_str, date))

            source_url = (
                "http://leginfo.legislature.ca.gov/faces/billVotesClient.xhtml?"
            )
            source_url += f"bill_id={session}{bill.session_num}{fsbill.identifier}"

            # Votes for non archived years
            if archive_year > 2009:
                for vote_num, vote in enumerate(bill.votes):
                    if vote.vote_result == "(PASS)":
                        result = True
                    else:
                        result = False

                    if not vote.location:
                        continue

                    full_loc = vote.location.description
                    first_part = full_loc.split(" ")[0].lower()
                    if first_part in ["asm", "assembly"]:
                        vote_chamber = "lower"
                        # vote_location = ' '.join(full_loc.split(' ')[1:])
                    elif first_part.startswith("sen"):
                        vote_chamber = "upper"
                        # vote_location = ' '.join(full_loc.split(' ')[1:])
                    else:
                        # raise ScrapeError("Bad location: %s" % full_loc) # To uncomment
                        continue

                    if vote.motion:
                        motion = vote.motion.motion_text or ""
                    else:
                        motion = ""

                    if "Third Reading" in motion or "3rd Reading" in motion:
                        vtype = "passage"
                    elif "Do Pass" in motion:
                        vtype = "passage"
                    else:
                        vtype = []

                    motion = motion.strip()
                    motion = re.compile(
                        r"(\w+)( Extraordinary)? Session$", re.IGNORECASE
                    ).sub("", motion)
                    motion = re.compile(r"^(Senate|Assembly) ", re.IGNORECASE).sub(
                        "", motion
                    )
                    motion = re.sub(
                        r"^(SCR|SJR|SB|AB|AJR|ACR)\s?\d+ \w+\.?  ", "", motion
                    )
                    motion = re.sub(r" \(\w+\)$", "", motion)
                    motion = re.sub(r"(SCR|SB|AB|AJR|ACR)\s?\d+ \w+\.?$", "", motion)
                    motion = re.sub(
                        r"(SCR|SJR|SB|AB|AJR|ACR)\s?\d+ \w+\.? " r"Urgency Clause$",
                        "(Urgency Clause)",
                        motion,
                    )
                    motion = re.sub(r"\s+", " ", motion)

                    if not motion:
                        self.warning("Got blank motion on vote for %s" % bill_id)
                        continue

                    # XXX this is responsible for all the CA 'committee' votes, not
                    # sure if that's a feature or bug, so I'm leaving it as is...
                    # vote_classification = chamber if (vote_location == 'Floor') else 'committee'
                    # org = {
                    # 'name': vote_location,
                    # 'classification': vote_classification
                    # }

                    fsvote = VoteEvent(
                        motion_text=motion,
                        start_date=self._tz.localize(vote.vote_date_time),
                        result="pass" if result else "fail",
                        classification=vtype,
                        # organization=org,
                        chamber=vote_chamber,
                        bill=fsbill,
                    )
                    fsvote.extras = {"threshold": vote.threshold}

                    fsvote.add_source(source_url)
                    fsvote.dedupe_key = source_url + "#" + str(vote_num)

                    rc = {"yes": [], "no": [], "other": []}
                    for record in vote.votes:
                        if record.vote_code == "AYE":
                            rc["yes"].append(record.legislator_name)
                        elif record.vote_code.startswith("NO"):
                            rc["no"].append(record.legislator_name)
                        else:
                            rc["other"].append(record.legislator_name)

                    # Handle duplicate votes
                    for key in rc:
                        rc[key] = list(set(rc[key]))

                    for key, voters in rc.items():
                        for voter in voters:
                            fsvote.vote(key, voter)
                        # Set counts by summed votes for accuracy
                        fsvote.set_count(key, len(voters))

                    yield fsvote
            if len(bill.votes) > 0 and archive_year <= 2009:
                vote_page_url = (
                    "http://leginfo.legislature.ca.gov/faces/billVotesClient.xhtml?"
                )
                vote_page_url += (
                    f"bill_id={session}{bill.session_num}{fsbill.identifier}"
                )

                # parse the bill data page, finding the latest html text
                data = self.get(vote_page_url).content
                doc = html.fromstring(data)
                doc.make_links_absolute(vote_page_url)
                num_of_votes = len(doc.xpath("//div[@class='status']"))
                for vote_section in range(1, num_of_votes + 1):
                    lines = doc.xpath(
                        f"//div[@class='status'][{vote_section}]//div[@class='statusRow']"
                    )
                    date, result, motion, vtype, location = "", "", "", "", ""
                    votes = {}
                    for line in lines:
                        line = line.text_content().split()
                        if line[0] == "Date":
                            date = line[1]
                            date = datetime.datetime.strptime(date, "%m/%d/%y")
                            date = self._tz.localize(date)
                        elif line[0] == "Result":
                            result = "pass" if "PASS" in line[1] else "fail"
                        elif line[0] == "Motion":
                            motion = " ".join(line[1:])
                        elif line[0] == "Location":
                            location = " ".join(line[1:])
                        elif len(line) > 1:
                            if line[0] == "Ayes" and line[1] != "Count":
                                votes["yes"] = line[1:]
                            elif line[0] == "Noes" and line[1] != "Count":
                                votes["no"] = line[1:]
                            elif line[0] == "NVR" and line[1] != "Count":
                                votes["not voting"] = line[1:]
                    # Determine chamber based on location
                    first_part = location.split(" ")[0].lower()
                    vote_chamber = ""
                    if first_part in ["asm", "assembly"]:
                        vote_chamber = "lower"
                    elif first_part.startswith("sen"):
                        vote_chamber = "upper"

                    if "Third Reading" in motion or "3rd Reading" in motion:
                        vtype = "passage"
                    elif "Do Pass" in motion:
                        vtype = "passage"
                    else:
                        vtype = "other"
                    if len(motion) > 0:
                        fsvote = VoteEvent(
                            motion_text=motion,
                            start_date=date,
                            result=result,
                            classification=vtype,
                            chamber=vote_chamber,
                            bill=fsbill,
                        )
                        fsvote.add_source(vote_page_url)
                        fsvote.dedupe_key = vote_page_url + "#" + str(vote_section)

                        for how_voted, voters in votes.items():
                            for voter in voters:
                                voter = voter.replace(",", "")
                                fsvote.vote(how_voted, voter)
                        yield fsvote

            for analysis in bill.analyses:
                analysis_date = self._tz.localize(analysis.analysis_date)
                # create an analysis name to match the state's format
                # 05/31/20- Assembly Appropriations
                analysis_date_human = analysis_date.strftime("%m/%d/%y")
                analysis_name = "{}- {}".format(
                    analysis_date_human, analysis.committee_name
                )

                analysis_base = "https://leginfo.legislature.ca.gov/faces"

                # unfortunately this just brings you to the analysis list
                # storing analysisId and analyzingOffice for a future POST request?
                analysis_url_pdf = "{}/billAnalysisClient.xhtml?bill_id={}&analysisId={}&analyzingOffice={}".format(
                    analysis_base,
                    analysis.bill_id,
                    analysis.analysis_id,
                    analysis.committee_name.replace(" ", "+"),
                )

                fsbill.add_document_link(
                    analysis_name,
                    analysis_url_pdf,
                    classification="analysis",
                    date=analysis_date.date(),
                    media_type="application/pdf",
                    on_duplicate="ignore",
                )

            yield fsbill
            self.session.expire_all()


def etree_text_content(el):
    return html.fromstring(etree.tostring(el)).text_content()
