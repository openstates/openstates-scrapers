import datetime as dt
import lxml.html
import re
from openstates.scrape import Scraper, Bill, VoteEvent
from .actions import Categorizer, find_committee
from .utils import get_short_codes
from urllib import parse as urlparse

HI_URL_BASE = "https://capitol.hawaii.gov"
SHORT_CODES = "%s/legislature/committees.aspx?chamber=all" % (HI_URL_BASE)
repeated_action = ["Excused: none", "Representative(s) Eli"]


def create_bill_report_url(chamber, year, bill_type):
    cname = {"upper": "s", "lower": "h"}[chamber]
    bill_slug = {
        "bill": "%sb" % (cname),
        "cr": "%scr" % (cname.upper()),
        "r": "%sr" % (cname.upper()),
        "gm": "gm",
    }

    return (
        HI_URL_BASE
        + "/advreports/advreport.aspx?report=deadline&rpt_type=&measuretype="
        + bill_slug[bill_type]
        + "&year="
        + year
    )


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
    categorizer = Categorizer()

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
            committees = find_committee(string)

            action_attr = self.categorizer.categorize(string)
            atype = action_attr["classification"]
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
            # there are some double actions on the source site
            if (
                bill_id == "HB2466"
                and date == "2022-04-29"
                and any(description in string for description in repeated_action)
            ):
                continue
            act = bill.add_action(string, date, chamber=actor, classification=atype)

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
            name = name[:-1]
        return name.strip()

    def parse_bill_versions_table(self, bill, versions):
        if not versions:
            self.logger.warning("No version table for {}".format(bill.identifier))

        for version in versions:
            td = version.xpath("./a")[0]
            if "No other versions" in td.text_content():
                return

            if version.xpath("./a"):
                http_href = td.attrib["href"]
                name = td.text_content().strip()

                if not http_href.startswith("http"):
                    http_link = f"{HI_URL_BASE}{http_href}"
                else:
                    http_link = http_href
                pdf_link = http_link.replace("HTM", "PDF")

                # some bills (and GMs) swap the order or double-link to the same format
                # so detect the type, and ignore dupes
                bill.add_version_link(
                    name, http_link, media_type=self.classify_media(http_link)
                )
                bill.add_version_link(
                    name,
                    pdf_link,
                    media_type=self.classify_media(pdf_link),
                    on_duplicate="ignore",
                )

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
            filename = link.attrib["href"].replace("www.", "")
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
            filename = link.attrib["href"].replace("www.", "")
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
        versions = bill_page.xpath(
            "//*[@id='ctl00_MainContent_UpdatePanel2']/div/div/div"
        )

        metainf_table = bill_page.xpath(
            '//div[contains(@id, "itemPlaceholder")]//table[1]'
        )[0]
        action_table = bill_page.xpath(
            '//div[contains(@id, "UpdatePanel1")]//table[1]'
        )[0]

        meta = self.parse_bill_metainf_table(metainf_table)

        subs = [s.strip() for s in re.split(r";|,", meta["Report Title"])]
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

        # check for companion bills
        companion = meta["Companion"].strip()
        if companion:
            companion_url = bill_page.xpath(
                "//span[@id='ctl00_MainContent_ListView1_ctrl0_companionLabel']/a/@href"
            )[0]
            # a companion's session year is the last 4 chars of the link
            # this will match the _scraped_name of a session in __init__.py
            companion_year = companion_url[-4:]
            companion_session = self.session_from_scraped_name(companion_year)
            b.add_related_bill(
                identifier=companion.replace("\xa0", " "),
                legislative_session=companion_session,
                relation_type="companion",
            )

        # check for prior session bills
        if bill_page.xpath(
            "//table[@id='ContentPlaceHolderCol1_GridViewStatus']/tr/td/font/text()"
        ):
            prior = bill_page.xpath(
                "//table[@id='ContentPlaceHolderCol1_GridViewStatus']/tr/td/font/text()"
            )[-1]
            # "2023 Regular Session" -> "2022" -> "2022 Regular Session"
            prior_year = str(int(session[:4]) - 1)
            prior_session = f"{prior_year} Regular Session"
            if "carried over" in prior.lower():
                b.add_related_bill(
                    identifier=bill_id.replace("\xa0", " "),
                    legislative_session=prior_session,
                    relation_type="prior-session",
                )

        for sponsor in meta["Introducer(s)"]:
            if "(Introduced by request of another party)" in sponsor:
                sponsor = sponsor.replace(
                    " (Introduced by request of another party)", ""
                )
            if sponsor != "":
                # all caps sponsors are primary, others are secondary
                primary = sponsor.upper() == sponsor
                b.add_sponsorship(
                    sponsor, "primary" if primary else "cosponsor", "person", primary
                )

        if "gm" in bill_id.lower():
            b.add_sponsorship("governor", "primary", "person", True)

        self.parse_bill_versions_table(b, versions)
        self.parse_testimony(b, bill_page)
        self.parse_cmte_reports(b, bill_page)

        if bill_page.xpath(
            "//input[@id='ctl00_ContentPlaceHolderCol1_ImageButtonPDF']"
        ):
            self.parse_bill_header_versions(b, bill_id, session, bill_page)

        current_referral = meta["Current Referral"].strip()
        if current_referral:
            b.extras["current_referral"] = current_referral

        yield from self.parse_bill_actions_table(
            b, action_table, bill_id, session, url, chamber
        )
        yield b

    # sometimes they link to a version that's only in the header,
    # and works via a form submit, so hardcode it here
    def parse_bill_header_versions(self, bill, bill_id, session, page):
        pdf_link = (
            f"https://capitol.hawaii.gov/session{session[0:4]}/bills/{bill_id}_.PDF"
        )
        bill.add_version_link(
            bill_id,
            pdf_link,
            media_type="application/pdf",
            on_duplicate="ignore",
        )

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
            "gm": "proclamation",
        }[billtype]

        list_html = self.get(report_page_url).text
        list_page = lxml.html.fromstring(list_html)
        for bill_url in list_page.xpath("//a[@class='report']"):
            bill_url = bill_url.attrib["href"].replace("www.", "")
            if not bill_url.startswith("http"):
                bill_url = f"{HI_URL_BASE}{bill_url}"
            yield from self.scrape_bill(session, chamber, billtype_map, bill_url)

    def scrape(self, chamber=None, session=None):
        get_short_codes(self)
        bill_types = ["bill", "cr", "r"]
        chambers = [chamber] if chamber else ["lower", "upper"]
        for chamber in chambers:
            # only scrape GMs once
            if chamber == "upper":
                bill_types.append("gm")
            for typ in bill_types:
                yield from self.scrape_type(chamber, session, typ)

    def session_from_scraped_name(self, scraped_name):
        # find the session from __init__.py matching scraped_name
        details = next(
            each
            for each in self.jurisdiction.legislative_sessions
            if each["_scraped_name"] == scraped_name
        )
        return details["name"]
