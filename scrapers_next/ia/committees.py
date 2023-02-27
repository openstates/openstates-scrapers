from spatula import XPath, URL, HtmlListPage, HtmlPage, SkipItem, SelectorError
from openstates.models import ScrapeCommittee
import requests
import lxml.html
import re


"""
The two scrapers that need to be run here are:
- CommitteeList
- JointAppropriationsComm

`CommitteeList` scrapes all committees and subcommittees, but
`JointAppropriationsComm` scrapes the membership of each
chamber's appropriations committee, and writes a committee object
that is of classification="legislature" and membership consists of both
upper and lower chamber appropriations committees members.
--- There are two reasons for this
    1. All scraped appropriations subcommittees are joint, and must correspond
        to joint committee parent.
    2. The appropriations committees of each chamber effectively coordinate
        in a joint capacity, so this addition of additional comm reflects that.

IMPORTANT: when this jurisdiction's committee data are merged/imported into
the database, the following steps should occur to avoid a KeyError when merging
the joint appropriations subcommittees. The steps must occur  in this order:
    1. merge only the one comm written from `JointAppropriationsComm`
    2. move the JSON file for that comm into the folder with all the committees
        scraped by `CommitteeList`
    3. merge all committees
    4. if a KeyError is raised, re-run each scraper,
        and then repeat the above 3 steps
"""


members_list_xpath = """
//section/div/section[contains(@class, 'grid_12 alpha omega') and (contains
(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),
 'house members') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
 'abcdefghijklmnopqrstuvwxyz'), 'senate members'))] //descendant::li
 """


def parse_member_string(member: str, com: ScrapeCommittee):
    """
    Helper function to parse member list item strings.
    """
    if member.lower() == "no member data available":
        raise SkipItem("empty committee")
    # Legislative members also have (party/district) info
    if "(" in member:
        member_name = member.split("(", 1)[0].strip()
        member_role = member.rsplit(")", 1)[1].strip()
        if member_role:
            member_role = member_role.split(",", 1)[1].strip()
            com.add_member(name=member_name, role=member_role)
        else:
            com.add_member(name=member_name)
    # Public members simply have name, role
    elif "," in member:
        member_name, member_role = member.split(",", 1)
        if member_role:
            com.add_member(name=member_name.strip(), role=member_role.strip())
    else:
        member_name = member.strip()
        if not member_name:
            return
        com.add_member(name=member_name)


class UnknownChamberError(BaseException):
    def __init__(self, com_name):
        super().__init__(f"Chamber unknown for committee: {com_name}")


class CommitteeDetails(HtmlPage):
    def process_page(self):
        # Page header holds name and chamber
        header = (
            XPath('//*[@id="content"]/div/section/h1')
            .match_one(self.root)
            .text.strip()
            .rsplit(" ", 1)
        )
        name = header[0]

        if "s" in header[1].lower():
            chamber = "upper"
        elif "h" in header[1].lower():
            chamber = "lower"
        elif "j" in header[1].lower():
            chamber = "legislature"
        else:
            raise UnknownChamberError(name)

        if "subcommittee" in name.lower():
            classification = "subcommittee"
        else:
            classification = "committee"

        com = ScrapeCommittee(
            name=name,
            chamber=chamber,
            parent="Appropriations" if classification == "subcommittee" else None,
            classification=classification,
        )
        com.add_source(self.source.url)
        com.add_source("https://www.legis.iowa.gov/committees", "Committee list page")
        com.add_link(self.source.url, note="homepage")

        # Get list of members contained in nested grid_12
        # Translation hack in case they switch to all-caps
        try:
            members_list = XPath(members_list_xpath).match(self.root)
        except SelectorError:
            raise SkipItem("No members found")

        for member in members_list:
            member = member.text_content().strip()
            parse_member_string(member, com)

        return com


class CommitteeList(HtmlListPage):
    source = URL("https://www.legis.iowa.gov/committees")
    # Committee pages selector
    selector = XPath('//*[@id="content"]/section/section/div/section/ul/li[*]')

    def process_item(self, item):
        home_url = self.source.url
        com = CommitteeDetails(
            home_url, source=URL(XPath("./a/@href").match_one(item), timeout=30)
        )
        return com


class JointAppropriationsComm(HtmlPage):
    source = URL("https://www.legis.iowa.gov/committees")
    name_and_role_re = re.compile(r"(.+)\s+\(.+\),\s+(.+)")
    name_only_re = re.compile(r"(.+)\s+(\(.+\))")

    def process_page(self):
        joint_com = ScrapeCommittee(
            name="Appropriations", chamber="legislature", classification="committee"
        )

        appr_coms = XPath(
            ".//section[@class='divideVert grid_9 alpha omega'][1]//"
            "li//a[text() = 'Appropriations']"
        ).match(self.root)

        com_urls = [x.get("href") for x in appr_coms]

        for com_url in com_urls:
            response = requests.get(com_url)
            content = lxml.html.fromstring(response.content)
            members_list = XPath(members_list_xpath).match(content)

            header = (
                XPath('//*[@id="content"]/div/section/h1')
                .match_one(content)
                .text.strip()
                .rsplit(" ", 1)
            )
            chamber_dict = {"H": "House", "S": "Senate"}
            specific_chamber = chamber_dict[header[1][1]]

            joint_com.add_source(com_url, note=f"{specific_chamber} Committee Page")

            for member in members_list:
                member = member.text_content().strip()
                officer = self.name_and_role_re.search(member)
                if officer:
                    name, partial_role = officer.groups()
                    role = f"{partial_role}, {specific_chamber}"
                else:
                    name_match = self.name_only_re.search(member).groups()[0]
                    name, role = name_match, "member"
                joint_com.add_member(name=name, role=role)

        joint_com.add_source(self.source.url, "Committee list page")
        joint_com.add_link(self.source.url, "homepage")

        return joint_com
