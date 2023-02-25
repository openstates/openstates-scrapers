from spatula import HtmlPage, CSS, HtmlListPage, SelectorError, XPath, URL, SkipItem
from openstates.models import ScrapeCommittee
import re


"""
The scrapers to be run are:
- SenateCommitteeList
- House
- Joint
- Conference
- Special
"""


class HouseMemberDetailsError(BaseException):
    def __init__(self, com_name):
        super().__init__("Unexpected quantity of member details found on card")


class HouseCommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        try:
            member_cards = XPath(
                ".//div[@class='flex-1 ig--member-info p-6 md:p-4']"
            ).match(self.root)
            for card in member_cards:
                p_tags = XPath(".//p").match(card)
                raw_detail_list = [p.text_content() for p in p_tags]
                detail_list = [
                    detail
                    for detail in raw_detail_list
                    if "District" not in detail and len(detail) > 1
                ]
                if len(detail_list) == 2:
                    role, name = detail_list
                elif len(detail_list) == 1:
                    role, name = "Member", detail_list[0]
                else:
                    raise HouseMemberDetailsError
                com.add_member(name=name, role=role)
        except SelectorError:
            raise SkipItem("empty committee")

        if not com.members:
            raise SkipItem("empty committee")

        com.add_source(self.source.url, note="Committee details page")
        com.add_link(self.source.url, note="homepage")

        return com


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://oksenate.gov/committees/agriculture-and-wildlife"
    example_input = "Agriculture and Wildlife"

    def process_page(self):
        com = self.input
        try:
            mem_name_C = (
                CSS(
                    "div div div.senators__items span div article a span.senators__name span"
                )
                .match(self.root)[0]
                .text_content()
            )
            mem_name_VC = (
                CSS(
                    "div div div.senators__items span div article a span.senators__name span"
                )
                .match(self.root)[1]
                .text_content()
            )
            role_C = (
                CSS("div div div.senators__items span div span.senators__position")
                .match(self.root)[0]
                .text_content()
            )
            role_VC = (
                CSS("div div div.senators__items span div span.senators__position")
                .match(self.root)[1]
                .text_content()
            )
            if mem_name_C:
                com.add_member(mem_name_C, role_C)
            if mem_name_VC:
                com.add_member(mem_name_VC, role_VC)
        except IndexError:
            mem_name_C = (
                CSS(
                    "div div div.senators__items span div article a span.senators__name span"
                )
                .match(self.root)[0]
                .text_content()
            )
            role_C = (
                CSS("div div div.senators__items span div span.senators__position")
                .match(self.root)[0]
                .text_content()
            )
            if mem_name_C:
                com.add_member(mem_name_C, role_C)
        members = CSS("div div div div a span.sSen__sName").match(self.root)
        for member in members:
            name = member.text_content().strip()
            role = "member"
            if name:
                com.add_member(name, role)

        if not com.members:
            raise SkipItem("empty committee")

        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")
        return com


class CommitteeList(HtmlListPage):
    selector = XPath(".//div[@class='grid grid-cols-1 md:grid-cols-2 gap-6']//a")

    def process_item(self, item):
        name = XPath("./div/h3").match(item)[0].text_content()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        com.add_source(self.source.url, note="House committees list page")
        detail_link = item.get("href")
        return HouseCommitteeDetail(com, source=URL(detail_link, timeout=20))


class SenateCommitteeList(HtmlListPage):
    source = "https://oksenate.gov/committees-list"
    chamber = "upper"
    selector = CSS(
        "section.section.section_ind_c.section_bg-color_c div div div.bTiles__items a"
    )

    def process_item(self, item):

        name = CSS("div span.bTiles__title").match(item)[0].text_content()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        com.add_source(self.source.url, note="Senate committees list page")
        detail_link = item.get("href")
        return SenateCommitteeDetail(com, source=detail_link)


class HouseAppropriationsSubComs(HtmlListPage):
    source = URL("https://www.okhouse.gov/committees/house/approp", timeout=20)
    selector = XPath(".//a[@class='cursor-pointer text-primary underline']")
    chamber = "lower"
    classification = "subcommittee"
    sub_com_name_re = re.compile(r"A&B (.+) (Subcommittee)")

    def process_item(self, item):
        raw_name = item.text_content()
        name = self.sub_com_name_re.search(raw_name).groups()[0]
        com = ScrapeCommittee(
            name=name,
            classification=self.classification,
            chamber=self.chamber,
            parent="Appropriations and Budget",
        )
        com.add_source(self.source.url, note="House committees list page")
        detail_link = item.get("href")
        return HouseCommitteeDetail(com, source=URL(detail_link, timeout=20))


class House(CommitteeList):
    source = URL("https://www.okhouse.gov/committees/house", timeout=20)
    chamber = "lower"


class Joint(CommitteeList):
    source = URL("https://www.okhouse.gov/committees/joint", timeout=20)
    chamber = "legislature"


class Conference(CommitteeList):
    source = URL("https://www.okhouse.gov/committees/conference", timeout=20)
    chamber = "legislature"


class Special(CommitteeList):
    source = URL("https://www.okhouse.gov/committees/special", timeout=20)
    chamber = "legislature"
