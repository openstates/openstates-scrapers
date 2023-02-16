from spatula import HtmlPage, HtmlListPage, CSS, XPath, SkipItem, SelectorError, URL
from openstates.models import ScrapeCommittee
import lxml.html
import requests
import re


member_name_re = re.compile(r"(Senator\s+|Representative\s+)(.+)(\s+\(.+\))")
sub_comm_re = re.compile(r"(.+) Subcommittee of .+ on (.+)")
oversight_on_re = re.compile(r"(Oversight) Committee on (.+)")
oversight_comm_re = re.compile(r"Joint Legislative (.+) (Oversight) Committee")
comm_on_re = re.compile(r"(Committee on )(.+)")


class UnknownSubcommitteeError(BaseException):
    def __init__(self, sub_com_name):
        super().__init__(f"Parent unknown for: {sub_com_name}")


def get_joint_comm_name(root):
    raw_com_name = XPath(".//h1").match(root)[0].text
    if sub_comm_re.search(raw_com_name):
        name = sub_comm_re.search(raw_com_name).groups()[0]
    elif oversight_on_re.search(raw_com_name):
        name_group = oversight_on_re.search(raw_com_name).groups()
        name = f"{name_group[1]}, {name_group[0]}"
    elif oversight_comm_re.search(raw_com_name):
        name_group = oversight_comm_re.search(raw_com_name).groups()
        name = f"{name_group[0]}, {name_group[1]}"
    elif comm_on_re.search(raw_com_name):
        name = comm_on_re.search(raw_com_name).groups()[1]
    else:
        name = raw_com_name.replace("Committee", "").replace("Joint", "").strip()
    return name


def get_role(text):
    if text.endswith("s"):
        text = text[:-1]
    return text.lower()


class CommitteeDetail(HtmlPage):
    example_source = (
        "https://www.ncleg.gov/Committees/CommitteeInfo/SenateStanding/1162"
    )

    def process_page(self):
        url_name_dict, list_page_url, com = self.input

        # Reassign with more accurate committee name
        if com.chamber == "legislature":
            name = get_joint_comm_name(self.root)
            com.name = name

        com.add_source(list_page_url, note="committees list page")
        com.add_source(self.source.url, note="committee details page")
        com.add_link(self.source.url, note="homepage")

        try:
            membership_types = CSS("div#Membership h5").match(self.root)
        except SelectorError:
            raise SkipItem(f"{com.name} is empty committee")

        for membership_type in membership_types:
            role = get_role(membership_type.text_content())

            members = CSS("p").match(membership_type.getnext())
            for member in members:
                member_url = member.getparent().get("href")
                # Get full and accurate name when member links present
                if member_url:
                    if url_name_dict.get(member_url):
                        name = url_name_dict[member_url]
                    else:
                        response = requests.get(member_url, timeout=30)
                        page = lxml.html.fromstring(response.content)
                        raw_name = CSS("h1.section-title").match(page)[0].text
                        name = member_name_re.search(raw_name).groups()[1]
                        url_name_dict[member_url] = name
                # When no link, typically public member or former legislator
                else:
                    if "Sen." not in member.text and "Rep." not in member.text:
                        if role == "member":
                            role = "public member"
                    name = " ".join(member.text.split()[1:])
                com.add_member(name=name, role=role)

        if not com.members:
            raise SkipItem(f"{com.name} is empty committee")

        return com


class CommitteeList(HtmlListPage):
    source = "https://www.ncleg.gov/committees"
    selector = XPath(
        ".//h2[not(contains(text(), 'Expired'))]"
        "/following-sibling::div//a[contains(@href, 'CommitteeInfo')]"
    )
    header_comm_chambers = {
        "House Standing": "lower",
        "House Select": "lower",
        "Senate Standing": "upper",
        "Senate Select": "upper",
        "Non-Standing": "legislature",
    }
    sub_comm_parents = {"Municipal Incorporations Subcommittee": "Local Government"}
    member_urls_and_names = {}

    def process_item(self, item):
        header = (
            item.getparent()
            .getparent()
            .getparent()
            .getparent()
            .xpath("h2/text()")[0]
            .strip()
        )

        if self.header_comm_chambers.get(header):
            chamber = self.header_comm_chambers[header]
        else:
            raise SkipItem("Unwanted section")

        name = item.text_content().strip()
        parent = None
        classification = "committee"
        if "Subcommittee" in name:
            if self.sub_comm_parents.get(name):
                parent = self.sub_comm_parents[name]
                classification = "subcommittee"
            else:
                raise UnknownSubcommitteeError(name)

        return CommitteeDetail(
            [
                self.member_urls_and_names,
                self.source.url,
                ScrapeCommittee(
                    name=item.text_content(),
                    chamber=chamber,
                    classification=classification,
                    parent=parent,
                ),
            ],
            source=URL(item.get("href"), timeout=30),
        )
