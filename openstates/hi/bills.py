import datetime as dt
import lxml.html
import re
from pupa.scrape import Scraper, Bill, VoteEvent
from .utils import get_short_codes
from urllib import parse as urlparse

HI_URL_BASE = "http://capitol.hawaii.gov"
SHORT_CODES = "%s/committees/committees.aspx?chamber=all" % (HI_URL_BASE)


def create_bill_report_url(chamber, year, bill_type):
    cname = {"upper": "s", "lower": "h"}[chamber]
    bill_slug = {
        "bill": "intro%sb" % (cname),
        "cr": "%sCR" % (cname.upper()),
        "r": "%sR" % (cname.upper()),
    }

    return HI_URL_BASE + "/report.aspx?type=" + bill_slug[bill_type] + "&year=" + year


def categorize_action(action):
    classifiers = (
        ("Pass(ed)? First Reading", "reading-1"),
        ("Introduced and Pass(ed)? First Reading", ["introduction", "reading-1"]),
        ("Introduced", "introduction"),
        ("Re(-re)?ferred to ", "referral-committee"),
        (
            "Passed Second Reading .* referred to the committee",
            ["reading-2", "referral-committee"],
        ),
        (".* that the measure be PASSED", "committee-passage-favorable"),
        ("Received from (House|Senate)", "introduction"),
        ("Floor amendment .* offered", "amendment-introduction"),
        ("Floor amendment adopted", "amendment-passage"),
        ("Floor amendment failed", "amendment-failure"),
        (".*Passed Third Reading", "passage"),
        ("Enrolled to Governor", "executive-receipt"),
        ("Act ", "executive-signature"),
        # Note, occasionally the gov sends intent to veto then doesn't. So use Vetoed not Veto
        ("Vetoed .* line-item", "executive-veto-line-item"),
        ("Vetoed", "executive-veto"),
        ("Veto overridden", "veto-override-passage"),
        # these are for resolutions
        ("Offered", "introduction"),
        ("Adopted", "passage"),
    )
    ctty = None
    for pattern, types in classifiers:
        if re.match(pattern, action):
            if "referral-committee" in types:
                ctty = re.findall(r"\w+", re.sub(pattern, "", action))
            return (types, ctty)
    # return other by default
    return (None, ctty)


def split_specific_votes(voters):
    if voters is None or voters.startswith("none"):
        return []
    elif voters.startswith("Senator(s)"):
        voters = voters.replace("Senator(s) ", "")
    elif voters.startswith("Representative(s)"):
        voters = voters.replace("Representative(s)", "")
    # Remove trailing spaces and semicolons
    return (v.rstrip(" ;") for v in voters.split(", "))


class HIBillScraper(Scraper):
    def parse_bill_metainf_table(self, metainf_table):
        def _sponsor_interceptor(line):
            return [guy.strip() for guy in line.split(",")]

        interceptors = {"Introducer(s)": _sponsor_interceptor}

        ret = {}
        for tr in metainf_table:
            row = tr.xpath("td")
            key = row[0].text_content().strip()
            value = row[1].text_content().strip()
            if key[-1:] == ":":
                key = key[:-1]
            if key in interceptors:
                value = interceptors[key](value)
            ret[key] = value
        return ret

    _vote_type_map = {
        "S": "upper",
        "H": "lower",
        "D": "legislature",  # "Data Systems",
        "$": "Appropriation measure",
        "CONAM": "Constitutional Amendment",
    }

    def parse_bill_actions_table(
        self, bill, action_table, bill_id, session, url, bill_chamber
    ):

        # vote types that have been reconsidered since last vote of that type
        reconsiderations = set()

        for action in action_table.xpath("*")[1:]:
            date = action[0].text_content()
            date = dt.datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")
            actor_code = action[1].text_content().upper()
            string = action[2].text_content()
            actor = self._vote_type_map[actor_code]
            act_type, committees = categorize_action(string)
            # XXX: Translate short-code to full committee name for the
            #      matcher.

            real_committees = []

            if committees:
                for committee in committees:
                    try:
                        committee = self.short_ids[committee]["name"]
                        real_committees.append(committee)
                    except KeyError:
                        pass
            act = bill.add_action(string, date, chamber=actor, classification=act_type)

            for committee in real_committees:
                act.add_related_entity(name=committee, entity_type="organization")
            vote = self.parse_vote(string)

            if vote:
                v, motion = vote
                motion_text = (
                    ("Reconsider: " + motion) if actor in reconsiderations else motion
                )
                vote = VoteEvent(
                    start_date=date,
                    chamber=actor,
                    bill=bill_id,
                    bill_chamber=bill_chamber,
                    legislative_session=session,
                    motion_text=motion_text,
                    result="pass" if "passed" in string.lower() else "fail",
                    classification="passage",
                )
                reconsiderations.discard(actor)
                vote.add_source(url)
                vote.set_count("yes", int(v["n_yes"] or 0))
                vote.set_count("no", int(v["n_no"] or 0))
                vote.set_count("not voting", int(v["n_excused"] or 0))
                for voter in split_specific_votes(v["yes"]):
                    voter = self.clean_voter_name(voter)
                    vote.yes(voter)
                for voter in split_specific_votes(v["yes_resv"]):
                    voter = self.clean_voter_name(voter)
                    vote.yes(voter)
                for voter in split_specific_votes(v["no"]):
                    voter = self.clean_voter_name(voter)
                    vote.no(voter)
                for voter in split_specific_votes(v["excused"]):
                    voter = self.clean_voter_name(voter)
                    vote.vote("not voting", voter)

                yield vote

            elif re.search("reconsider", string, re.IGNORECASE):
                reconsiderations.add(actor)

    def clean_voter_name(self, name):
        if name[-1] == ".":
            name = name[:-2]
        if name[0] == " ":
            name = name[1:]
        return name.strip()

    def parse_bill_versions_table(self, bill, versions):
        versions = versions.xpath("./*")

        if versions == []:
            raise Exception("Missing bill versions.")

        for version in versions:
            tds = version.xpath("./*")
            if "No other versions" in tds[0].text_content():
                return

            if version.xpath("./a"):
                http_href = tds[0].xpath("./a")
                name = http_href[0].text_content().strip()
                pdf_href = tds[1].xpath("./a")

                http_link = http_href[0].attrib["href"]
                pdf_link = pdf_href[0].attrib["href"]

                bill.add_version_link(name, http_link, media_type="text/html")
                bill.add_version_link(name, pdf_link, media_type="application/pdf")

    def classify_media(self, url):
        media_type = None
        if "pdf" in url.lower():
            media_type = "application/pdf"
        elif ".htm" in url.lower():
            media_type = "text/html"
        elif ".docx" in url.lower():
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ".doc" in url.lower():
            media_type = "application/msword"
        return media_type

    def parse_testimony(self, bill, page):
        links = page.xpath("//table[contains(@id, 'GridViewTestimony')]/tr/td/a")

        # sometimes they have a second link w/ an icon for the pdf, sometimes now
        last_item = ""

        for link in links:
            filename = link.attrib["href"]
            name = link.text_content().strip()
            if name == "" and last_item != "":
                name = last_item
            else:
                name = "Testimony {}".format(name)

            last_item = name
            media_type = self.classify_media(filename)

            bill.add_document_link(name, filename, media_type=media_type)

    def parse_cmte_reports(self, bill, page):
        links = page.xpath("//table[contains(@id, 'GridViewCommRpt')]/tr/td/a")
        # sometimes they have a second link w/ an icon for the pdf, sometimes now
        last_item = ""

        for link in links:
            filename = link.attrib["href"]
            name = link.text_content().strip()
            if name == "" and last_item != "":
                name = last_item
            else:
                name = "Committee Report {}".format(name)

            last_item = name
            media_type = self.classify_media(filename)

            bill.add_document_link(name, filename, media_type=media_type)

    def scrape_bill(self, session, chamber, bill_type, url):
        bill_html = self.get(url).text
        bill_page = lxml.html.fromstring(bill_html)

        qs = dict(urlparse.parse_qsl(urlparse.urlparse(url).query))
        bill_id = "{}{}".format(qs["billtype"], qs["billnumber"])
        versions = bill_page.xpath("//table[contains(@id, 'GridViewVersions')]")[0]

        metainf_table = bill_page.xpath(
            '//div[contains(@id, "itemPlaceholder")]//table[1]'
        )[0]
        action_table = bill_page.xpath(
            '//div[contains(@id, "UpdatePanel1")]//table[1]'
        )[0]

        meta = self.parse_bill_metainf_table(metainf_table)

        subs = [s.strip() for s in meta["Report Title"].split(";")]
        if "" in subs:
            subs.remove("")
        b = Bill(
            bill_id,
            session,
            meta["Measure Title"],
            chamber=chamber,
            classification=bill_type,
        )
        if meta["Description"]:
            b.add_abstract(meta["Description"], "description")
        for subject in subs:
            b.add_subject(subject)
        if url:
            b.add_source(url)

        prior_session = "{} Regular Session".format(str(int(session[:4]) - 1))
        companion = meta["Companion"].strip()
        if companion:
            b.add_related_bill(
                identifier=companion.replace(u"\xa0", " "),
                legislative_session=prior_session,
                relation_type="companion",
            )
        if bill_page.xpath(
            "//table[@id='ContentPlaceHolderCol1_GridViewStatus']/tr/td/font/text()"
        ):
            prior = bill_page.xpath(
                "//table[@id='ContentPlaceHolderCol1_GridViewStatus']/tr/td/font/text()"
            )[-1]
            if "carried over" in prior.lower():
                b.add_related_bill(
                    identifier=bill_id.replace(u"\xa0", " "),
                    legislative_session=prior_session,
                    relation_type="companion",
                )
        for sponsor in meta["Introducer(s)"]:
            if "(Introduced by request of another party)" in sponsor:
                sponsor = sponsor.replace(
                    " (Introduced by request of another party)", ""
                )
            b.add_sponsorship(sponsor, "primary", "person", True)

        self.parse_bill_versions_table(b, versions)
        self.parse_testimony(b, bill_page)
        self.parse_cmte_reports(b, bill_page)

        yield from self.parse_bill_actions_table(
            b, action_table, bill_id, session, url, chamber
        )
        yield b

    def parse_vote(self, action):
        vote_re = r"""
                (?P<n_yes>\d+)\sAye\(?s\)?  # Yes vote count
                (:\s+(?P<yes>.*?))?;\s+  # Yes members
                Aye\(?s\)?\swith\sreservations:\s+(?P<yes_resv>.*?);?
                (?P<n_no>\d*)\sNo\(?es\)?:\s+(?P<no>.*?);?
                (\s+and\s+)?
                (?P<n_excused>\d*)\sExcused:\s(?P<excused>.*)\.?
                """
        result = re.search(vote_re, action, re.VERBOSE)
        if result is None:
            return None
        result = result.groupdict()
        motion = action.split(".")[0] + "."
        return result, motion

    def scrape_type(self, chamber, session, billtype):
        for i in self.jurisdiction.legislative_sessions:
            if i["identifier"] == session:
                session_urlslug = i["_scraped_name"]
        report_page_url = create_bill_report_url(chamber, session_urlslug, billtype)
        billtype_map = {
            "bill": "bill",
            "cr": "concurrent resolution",
            "r": "resolution",
        }[billtype]

        list_html = self.get(report_page_url).text
        list_page = lxml.html.fromstring(list_html)
        for bill_url in list_page.xpath("//a[@class='report']"):
            bill_url = HI_URL_BASE + bill_url.attrib["href"]
            yield from self.scrape_bill(session, chamber, billtype_map, bill_url)

    def scrape(self, chamber=None, session=None):
        get_short_codes(self)
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        bill_types = ["bill", "cr", "r"]
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            for typ in bill_types:
                yield from self.scrape_type(chamber, session, typ)
