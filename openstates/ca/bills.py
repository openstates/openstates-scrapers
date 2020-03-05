import os
import re
import pytz
import operator
import itertools
import datetime
from lxml import etree, html
from openstates.utils import LXMLMixin

# # import lxml.html
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from pupa.scrape import Scraper, Bill, VoteEvent

# from pupa.scrape.base import ScrapeError

from .models import CABill
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


# Committee codes used in action chamber text.
committee_data_upper = [
    (
        "Standing Committee on Governance and Finance",
        "CS73",
        ["GOV. & F.", "Gov. & F."],
    ),
    (
        "Standing Committee on Energy, Utilities and Communications",
        "CS71",
        ["E., U., & C."],
    ),
    ("Standing Committee on Education", "CS44", ["ED."]),
    ("Standing Committee on Appropriations", "CS61", ["APPR."]),
    ("Standing Committee on Labor and Industrial Relations", "CS51", ["L. & I.R."]),
    (
        "Standing Committee on Elections and Constitutional Amendments",
        "CS45",
        ["E. & C.A."],
    ),
    ("Standing Committee on Environmental Quality", "CS64", ["E.Q."]),
    ("Standing Committee on Natural Resources And Water", "CS55", ["N.R. & W."]),
    ("Standing Committee on Public Employment and Retirement", "CS56", ["P.E. & R."]),
    ("Standing Committee on Governmental Organization", "CS48", ["G.O."]),
    ("Standing Committee on Insurance", "CS70", ["INS."]),
    ("Standing Committee on Public Safety", "CS72", ["PUB. S."]),
    ("Standing Committee on Judiciary", "CS53", ["JUD."]),
    ("Standing Committee on Health", "CS60", ["HEALTH"]),
    ("Standing Committee on Transportation and Housing", "CS59", ["T. & H."]),
    (
        "Standing Committee on Business, Professions and Economic Development",
        "CS42",
        ["B., P. & E.D."],
    ),
    ("Standing Committee on Agriculture", "CS40", ["AGRI."]),
    (
        "Standing Committee on Banking and Financial Institutions",
        "CS69",
        ["B. & F.I."],
    ),
    ("Standing Committee on Veterans Affairs", "CS66", ["V.A."]),
    ("Standing Committee on Budget and Fiscal Review", "CS62", ["B. & F.R."]),
    ("Standing Committee on Human Services", "CS74", ["HUM. S.", "HUMAN S."]),
    ("Standing Committee on Rules", "CS58", ["RLS."]),
    (
        "Extraordinary Committee on Transportation and Infrastructure Development",
        "CS67",
        ["T. & I.D."],
    ),
]

committee_data_lower = [
    ("Standing Committee on Rules", "CX20", ["RLS."]),
    ("Standing Committee on Revenue and Taxation", "CX19", ["REV. & TAX"]),
    ("Standing Committee on Natural Resources", "CX16", ["NAT. RES."]),
    ("Standing Committee on Appropriations", "CX25", ["APPR."]),
    ("Standing Committee on Insurance", "CX28", ["INS."]),
    ("Standing Committee on Utilities and Commerce", "CX23", ["U. & C."]),
    ("Standing Committee on Education", "CX03", ["ED."]),
    ("Standing Committee on Public Safety", "CX18", ["PUB. S."]),
    ("Standing Committee on Elections and Redistricting", "CX04", ["E. & R."]),
    ("Standing Committee on Judiciary", "CX13", ["JUD."]),
    ("Standing Committee on Higher Education", "CX09", ["HIGHER ED."]),
    ("Standing Committee on Health", "CX08", ["HEALTH"]),
    ("Standing Committee on Human Services", "CX11", ["HUM. S.", "HUMAN S."]),
    (
        "Standing Committee on Arts, Entertainment, Sports, Tourism, and Internet Media",
        "CX37",
        ["A., E., S., T., & I.M."],
    ),
    ("Standing Committee on Transportation", "CX22", ["TRANS."]),
    (
        "Standing Committee on Business, Professions and Consumer Protection",
        "CX33",
        ["B., P., & C.P.", "B. & P."],
    ),
    ("Standing Committee on Water, Parks and Wildlife", "CX24", ["W., P., & W."]),
    ("Standing Committee on Local Government", "CX15", ["L. GOV.", "L. Gov."]),
    ("Standing Committee on Aging and Long Term Care", "CX31", ["AGING & L.T.C."]),
    ("Standing Committee on Labor and Employment", "CX14", ["L. & E."]),
    ("Standing Committee on Governmental Organization", "CX07", ["G.O."]),
    (
        "Standing Committee on Public Employees, Retirement and Social Security",
        "CX17",
        ["P.E., R., & S.S."],
    ),
    ("Standing Committee on Veterans Affairs", "CX38", ["V.A."]),
    ("Standing Committee on Housing and Community Development", "CX10", ["H. & C.D."]),
    (
        "Standing Committee on Environmental Safety and Toxic Materials",
        "CX05",
        ["E.S. & T.M."],
    ),
    ("Standing Committee on Agriculture", "CX01", ["AGRI."]),
    ("Standing Committee on Banking and Finance", "CX27", ["B. & F."]),
    (
        "Standing Committee on Jobs, Economic Development and the Economy",
        "CX34",
        ["J., E.D., & E."],
    ),
    (
        "Standing Committee on Accountability and Administrative Review",
        "CX02",
        ["A. & A.R."],
    ),
    ("Standing Committee on Budget", "CX29", ["BUDGET"]),
    ("Standing Committee on Privacy and Consumer Protection", "CX32", ["P. & C.P."]),
    ("Extraordinary Committee on Finance", "CX35", ["FINANCE"]),
    (
        "Extraordinary Committee on Public Health and Developmental Services",
        "CX30",
        ["P.H. & D.S."],
    ),
]

committee_data_both = committee_data_upper + committee_data_lower


def slugify(s):
    return re.sub(r"[ ,.]", "", s)


def get_committee_code_data():
    return dict((t[1], t[0]) for t in committee_data_both)


def get_committee_abbr_data():
    _committee_abbr_to_name_upper = {}
    _committee_abbr_to_name_lower = {}
    for name, code, abbrs in committee_data_upper:
        for abbr in abbrs:
            _committee_abbr_to_name_upper[slugify(abbr).lower()] = name

    for name, code, abbrs in committee_data_lower:
        for abbr in abbrs:
            _committee_abbr_to_name_lower[slugify(abbr).lower()] = name

    committee_data = {
        "upper": _committee_abbr_to_name_upper,
        "lower": _committee_abbr_to_name_lower,
    }

    return committee_data


def get_committee_name_regex():
    # Builds a list of all committee abbreviations.
    _committee_abbrs = map(operator.itemgetter(2), committee_data_both)
    _committee_abbrs = itertools.chain.from_iterable(_committee_abbrs)
    _committee_abbrs = sorted(_committee_abbrs, reverse=True, key=len)

    _committee_abbr_regex = [
        "%s" % r"[\s,]*".join(abbr.replace(",", "").split(" "))
        for abbr in _committee_abbrs
    ]
    _committee_abbr_regex = re.compile("(%s)" % "|".join(_committee_abbr_regex))

    return _committee_abbr_regex


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

    def committee_code_to_name(
        self, code, committee_code_to_name=get_committee_code_data()
    ):
        """Need to map committee codes to names.
        """
        return committee_code_to_name[code]

    def committee_abbr_to_name(
        self,
        chamber,
        abbr,
        committee_abbr_to_name=get_committee_abbr_data(),
        slugify=slugify,
    ):
        abbr = slugify(abbr).lower()
        try:
            return committee_abbr_to_name[chamber][slugify(abbr)]
        except KeyError:
            try:
                other_chamber = {"upper": "lower", "lower": "upper"}[chamber]
            except KeyError:
                raise KeyError
            return committee_abbr_to_name[other_chamber][slugify(abbr)]

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
            },
        }

        for chamber in chambers:
            for abbr, type_ in bill_types[chamber].items():
                yield from self.scrape_bill_type(chamber, session, type_, abbr)

    def scrape_bill_type(
        self,
        chamber,
        session,
        bill_type,
        type_abbr,
        committee_abbr_regex=get_committee_name_regex(),
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

            fsbill = Bill(bill_id, session, title="", chamber=chamber)
            if (bill_id.startswith("S") and chamber == "lower") or (
                bill_id.startswith("A") and chamber == "upper"
            ):
                print("!!!! BAD ID/CHAMBER PAIR !!!!", bill)
                continue

            # # Construct session for web query, going from '20092010' to '0910'
            # source_session = session[2:4] + session[6:8]

            # # Turn 'AB 10' into 'ab_10'
            # source_num = "%s_%s" % (bill.measure_type.lower(),
            #                         bill.measure_num)

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
                    subject = clean_title(version.subject)

            if not title:
                self.warning("Couldn't find title for %s, skipping" % bill_id)
                continue

            fsbill.title = title
            if summary:
                fsbill.add_abstract(summary, note="summary")
            fsbill.classification = type_
            fsbill.subject = [subject] if subject else []
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
            for action in bill.actions:
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

                # Add in the committee strings of the related committees, if any.
                kwargs = attrs
                matched_abbrs = committee_abbr_regex.findall(action.action)

                if re.search(r"Com[s]?. on", action.action) and not matched_abbrs:
                    msg = "Failed to extract committee abbr from %r."
                    self.logger.warning(msg % action.action)

                if matched_abbrs:
                    committees = []
                    for abbr in matched_abbrs:
                        try:
                            name = self.committee_abbr_to_name(chamber, abbr)
                            committees.append(name)
                        except KeyError:
                            msg = (
                                "Mapping contains no committee name for "
                                "abbreviation %r. Action text was %r."
                            )
                            args = (abbr, action.action)
                            self.warning(msg % args)

                    committees = filter(None, committees)
                    kwargs["committees"] = committees

                    code = re.search(r"C[SXZ]\d+", actor)
                    if code is not None:
                        code = code.group()
                        kwargs["actor_info"] = {"committee_code": code}
                    if not_archive_year:
                        assert len(list(committees)) == len(matched_abbrs)
                    for committee, abbr in zip(committees, matched_abbrs):
                        act_str = act_str.replace("Coms. on ", "")
                        act_str = act_str.replace("Com. on " + abbr, committee)
                        act_str = act_str.replace(abbr, committee)
                        if not act_str.endswith("."):
                            act_str = act_str + "."

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

                kwargs.update(self.categorizer.categorize(act_str))

                action = fsbill.add_action(
                    act_str,
                    date.strftime("%Y-%m-%d"),
                    chamber=actor,
                    classification=kwargs["classification"],
                )
                for committee in kwargs.get("committees", []):
                    action.add_related_entity(committee, entity_type="organization")
                seen_actions.add((actor, act_str, date))

            source_url = (
                "http://leginfo.legislature.ca.gov/faces/billVotesClient.xhtml?"
            )
            source_url += f"bill_id={session}0{fsbill.identifier}"
            # print(source_url)

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
                        vtype = "other"

                    motion = motion.strip()

                    # Why did it take until 2.7 to get a flags argument on re.sub?
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

                    source_url = (
                        "http://leginfo.legislature.ca.gov/faces"
                        "/billVotesClient.xhtml?bill_id={}"
                    ).format(fsbill.identifier)
                    fsvote.add_source(source_url)
                    fsvote.pupa_id = source_url + "#" + str(vote_num)

                    rc = {"yes": [], "no": [], "other": []}
                    for record in vote.votes:
                        if record.vote_code == "AYE":
                            rc["yes"].append(record.legislator_name)
                        elif record.vote_code.startswith("NO"):
                            rc["no"].append(record.legislator_name)
                        else:
                            rc["other"].append(record.legislator_name)

                    # Handle duplicate votes
                    for key in rc.keys():
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
                vote_page_url += f"bill_id={session}0{fsbill.identifier}"
                # print(vote_page_url)
                # print("Total Votes: " + str(len(bill.votes)))

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
                    yeas, noes, nvr = [], [], []
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
                                yeas = line[1:]
                            elif line[0] == "Noes" and line[1] != "Count":
                                noes = line[1:]
                            elif line[0] == "NVR" and line[1] != "Count":
                                nvr = line[1:]
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
                        fsvote.pupa_id = vote_page_url + "#" + str(vote_section)

                        for voter in yeas:
                            fsvote.vote("yes", voter)
                        for voter in noes:
                            fsvote.vote("no", voter)
                        for voter in nvr:
                            fsvote.vote("not voting", voter)
                        yield fsvote
                # print("num_of_votes:" + str(num_of_votes))

            yield fsbill
            self.session.expire_all()


def etree_text_content(el):
    return html.fromstring(etree.tostring(el)).text_content()
