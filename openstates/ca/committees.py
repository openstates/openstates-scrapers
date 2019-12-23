# -*- coding: utf-8 -*-
import re
from operator import methodcaller

import lxml.html
import requests.exceptions
from pupa.scrape import Scraper, Organization

from openstates.utils import LXMLMixin


strip = methodcaller("strip")


def clean(s):
    s = s.strip(u"\xa0 \n\t").replace(u"\xa0", " ")
    s = re.sub(r"[\s+\xa0]", " ", s)
    return s.strip()


class CACommitteeScraper(Scraper, LXMLMixin):
    urls = {
        "upper": "http://senate.ca.gov/committees",
        "lower": "http://assembly.ca.gov/committees",
    }

    base_urls = {"upper": "http://senate.ca.gov/", "lower": "http://assembly.ca.gov/"}

    def scrape(self, chamber=None):
        if chamber in ["lower", None]:
            yield from self.scrape_lower()
        elif chamber in ["upper", None]:
            # Also captures joint committees
            yield from self.scrape_upper()

    def scrape_lower(self):
        url = self.urls["lower"]
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(self.base_urls["lower"])

        for type_ in ["Standing", "Select"]:

            if type_ == "Joint":
                _chamber = type_.lower()
            else:
                _chamber = "lower"

            for xpath in [
                '//div[contains(@class, "view-view-%sCommittee")]' % type_,
                '//div[contains(@id, "block-views-view_StandingCommittee-block_1")]',
                '//div[contains(@class, "views-field-title")]',
            ]:
                div = doc.xpath(xpath)
                if div:
                    break

            div = div[0]
            committees = div.xpath('descendant::span[@class="field-content"]/a/text()')
            committees = map(strip, committees)
            urls = div.xpath('descendant::span[@class="field-content"]/a/@href')

            for c, _url in zip(committees, urls):

                if "autism" in _url:
                    # The autism page takes a stunning 10 minutes to respond
                    # with a 403. Skip it.
                    continue

                c = c.replace("Committee on ", "").replace(" Committee", "")
                org = Organization(name=c, chamber=_chamber, classification="committee")
                self.info(u"Saving {} committee.".format(c))
                org.add_source(_url)
                org.add_source(url)
                for member, role in self.scrape_lower_members(_url):
                    org.add_member(member, role)

                _found = False
                if not org._related:
                    try:
                        for member, role in self.scrape_lower_members(
                            _url + "/membersstaff"
                        ):
                            _found = True
                            org.add_member(member, role)
                        if _found:
                            source = _url + "/membersstaff"
                            org.add_source(source)
                    except requests.exceptions.HTTPError:
                        self.error(
                            "Unable to access member list for {} "
                            "committee.".format(c)
                        )

                if org._related:
                    yield org
                else:
                    self.warning("No members found for {} committee.".format(c))

        # Subcommittees
        div = doc.xpath('//div[contains(@class, "view-view-SubCommittee")]')[0]
        for subcom in div.xpath('div/div[@class="item-list"]'):
            committee = self.get_node(subcom, "h4/text()")

            if committee is None:
                continue

            names = subcom.xpath("descendant::a/text()")
            names = map(strip, names)
            urls = subcom.xpath("descendant::a/@href")
            for n, _url in zip(names, urls):
                n = re.search(r"^Subcommittee.*?on (.*)$", n).group(1)
                org = Organization(
                    name=n,
                    chamber="lower",
                    classification="committee",
                    parent_id={"name": committee, "classification": "lower"},
                )
                org.add_source(_url)
                org.add_source(url)

                for member, role in self.scrape_lower_members(_url):
                    org.add_member(member, role)

                _found = False
                if not org._related:
                    try:
                        for member, role in self.scrape_lower_members(
                            _url + "/membersstaff"
                        ):
                            _found = True
                            org.add_member(member, role)
                        if _found:
                            source = _url + "/membersstaff"
                            org.add_source(source)
                    except requests.exceptions.HTTPError:
                        self.error(
                            "Unable to access member list for {} subcommittee.".format(
                                org.name
                            )
                        )

                if org._related:
                    yield org
                else:
                    self.warning(
                        "No members found for {} subcommittee of {} "
                        "committee".format(org.name)
                    )

    def scrape_lower_members(self, url):
        """ Scrape the members from this page. """

        doc = self.lxmlize(url)
        members = doc.xpath(
            '//table/thead/tr//*[contains(text(), "Committee Members")]/'
            "ancestor::table//tr/td[1]/a/text()"
        )

        for member in members:
            (mem_name, mem_role) = re.search(
                r"""(?ux)
                    ^\s*(.+?)  # Capture the senator's full name
                    (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                    \s*$
                    """,
                member,
            ).groups()
            if not mem_role:
                mem_role = "member"
            yield (mem_name, mem_role)

    def scrape_upper(self):
        # Retrieve index list of committees.
        url = "http://senate.ca.gov/committees"
        doc = self.lxmlize(url)

        standing_committees = doc.xpath(
            '//h2[text()="Standing Committees"]/../following-sibling::div//a'
        )
        sub_committees = doc.xpath(
            '//h2[text()="Sub Committees"]/../following-sibling::div//a'
        )
        joint_committees = doc.xpath(
            '//h2[text()="Joint Committees"]/../following-sibling::div//a'
        )
        other_committees = doc.xpath(
            '//h2[text()="Other"]/../following-sibling::div//a'
        )

        # Iterates over each committee [link] found.
        for committee in (
            standing_committees + sub_committees + joint_committees + other_committees
        ):
            # Get the text of the committee link, which should be the name of
            # the committee.
            (comm_name,) = committee.xpath("text()")

            org = Organization(
                chamber="upper", name=comm_name, classification="committee"
            )

            (comm_url,) = committee.xpath("@href")
            org.add_source(comm_url)
            comm_doc = self.lxmlize(comm_url)

            if comm_name.startswith("Joint"):
                org["chamber"] = "legislature"
                org["committee"] = (
                    comm_name.replace("Joint ", "")
                    .replace("Committee on ", "")
                    .replace(" Committee", "")
                )

            if comm_name.startswith("Subcommittee"):
                (full_comm_name,) = comm_doc.xpath(
                    '//div[@class="banner-sitename"]/a/text()'
                )
                full_comm_name = re.search(
                    r"^Senate (.*) Committee$", full_comm_name
                ).group(1)
                org["committee"] = full_comm_name

                comm_name = re.search(r"^Subcommittee.*?on (.*)$", comm_name).group(1)
                org["subcommittee"] = comm_name

            # Special case of members list being presented in text blob.
            member_blob = comm_doc.xpath(
                'string(//div[contains(@class, "field-item") and '
                'starts-with(text(), "Senate Membership:")][1]/text()[1])'
            )

            if member_blob:
                # Separate senate membership from assembly membership.
                # This should strip the header from assembly membership
                # string automatically.
                delimiter = "Assembly Membership:\n"
                senate_members, delimiter, assembly_members = member_blob.partition(
                    delimiter
                )

                # Strip header from senate membership string.
                senate_members = senate_members.replace("Senate Membership:\n", "")

                # Clean membership strings.
                senate_members = senate_members.strip()
                assembly_members = assembly_members.strip()

                # Parse membership strings into lists.
                senate_members = senate_members.split("\n")
                assembly_members = assembly_members.split("\n")

                members = senate_members + assembly_members
            # Typical membership list format.
            else:
                members = comm_doc.xpath(
                    '//a[(contains(@href, "/sd") or '
                    'contains(@href, "assembly.ca.gov/a")) and '
                    '(starts-with(text(), "Senator") or '
                    'starts-with(text(), "Assembly Member"))]/text()'
                )

            for member in members:
                if not member.strip():
                    continue

                (mem_name, mem_role) = re.search(
                    r"""(?ux)
                        ^(?:Senator|Assembly\sMember)\s  # Legislator title
                        (.+?)  # Capture the senator's full name
                        (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                        (?:\s\([RD]\))?  # There may be a party affiliation
                        \s*$
                        """,
                    member,
                ).groups()
                org.add_member(mem_name, role=mem_role if mem_role else "member")

            if not org._related:
                self.warning("No members found for committee {}".format(comm_name))

            yield org
