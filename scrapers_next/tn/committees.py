from spatula import HtmlPage, HtmlListPage, XPath, URL
from openstates.models import ScrapeCommittee
import requests
import lxml.html


def get_parent_name(url):
    """
    Helper function called in `CommitteeList()` class,
    when item is of classification "subcommittee".

    Takes in string: url for the subcommittee's detail page.
    Returns string: name of the parent committee.
    """
    sub_com_response = requests.get(url)
    sub_com_content = lxml.html.fromstring(sub_com_response.content)
    parent_url = sub_com_content.xpath(".//a[@class='button block icon-hammer']")[
        0
    ].get("href")
    parent_response = requests.get(
        f"https://wapp.capitol.tn.gov/apps/CommitteeInfo/{parent_url}"
    )
    parent_content = lxml.html.fromstring(parent_response.content)
    parent_name = parent_content.xpath(".//h1//text()")[-1].replace("\r\n", "").strip()
    return parent_name


class CommitteeDetail(HtmlPage):
    example_source = "https://wapp.capitol.tn.gov/apps/CommitteeInfo/SenateComm.aspx?ga=113&committeeKey=620000"

    def process_page(self):
        com = self.input

        officers = self.root.xpath(
            ".//h2[contains(text(),'Committee Officers')]/" "following-sibling::div//a"
        )
        for officer in officers:
            name_and_title = [
                x.strip() for x in officer.text_content().split("\r\n") if len(x)
            ]
            name, title = name_and_title
            com.add_member(name, title)

        raw_members = self.root.xpath(
            ".//h2[contains(text(),'Committee Members')]/"
            "following-sibling::div//a//text()"
        )
        members_no_new_line = [x.replace("\r\n", "") for x in raw_members]
        regular_members = [x.strip() for x in members_no_new_line if len(x)]

        if regular_members:
            for member in regular_members:
                com.add_member(member, "Member")

        com.add_source(self.source.url, note="Committee Detail Page")
        com.add_link(self.source.url, note="homepage")

        return com


class CommitteeList(HtmlListPage):
    selector = XPath(
        ".//div[@class='row content']//h2[contains(text(),'Committee')]/"
        "following-sibling::div//div//dt//a"
    )
    classification = "committee"
    parent = None

    def process_item(self, item):
        comm_name = item.text_content()

        comm_url = item.get("href")

        if self.classification == "subcommittee":
            self.parent = get_parent_name(comm_url)

        com = ScrapeCommittee(
            name=comm_name.strip(),
            chamber=self.chamber,
            classification=self.classification,
            parent=self.parent,
        )
        com.add_source(self.source.url, note="Committees List Page")

        return CommitteeDetail(com, source=URL(comm_url, timeout=30))


class Senate(CommitteeList):
    source = "https://wapp.capitol.tn.gov/apps/CommitteeInfo/AllSenate.aspx"
    chamber = "upper"


class House(CommitteeList):
    source = "https://wapp.capitol.tn.gov/apps/CommitteeInfo/AllHouse.aspx"
    chamber = "lower"


class Joint(CommitteeList):
    source = "https://wapp.capitol.tn.gov/apps/CommitteeInfo/AllJoint.aspx"
    chamber = "legislature"


class HouseSubComs(CommitteeList):
    source = "https://wapp.capitol.tn.gov/apps/CommitteeInfo/AllHouse.aspx"
    selector = XPath(".//a[@class='icon-angle-right']")
    chamber = "lower"
    classification = "subcommittee"
