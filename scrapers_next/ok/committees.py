from spatula import HtmlPage, CSS, HtmlListPage, SelectorError
from openstates.models import ScrapeCommittee


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
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")
        return com


class HouseCommitteeDetail(HtmlPage):
    example_source = "https://www.okhouse.gov/Committees/CommitteeMembers.aspx?CommID=417&SubCommID=0"
    example_input = "Administrative Rules"

    def process_page(self):
        com = self.input
        try:
            Chair_member = (
                CSS("#ctl00_ContentPlaceHolder1_lnkChair")
                .match_one(self.root)
                .getchildren()[0]
                .tail.strip()
                .replace("Rep.", "")
            )
            VC_member = (
                CSS("#ctl00_ContentPlaceHolder1_lnkViceChair")
                .match_one(self.root)
                .getchildren()[0]
                .tail.replace("Rep.", "")
            )
            role_C = (
                CSS("#ctl00_ContentPlaceHolder1_lnkChair")
                .match_one(self.root)
                .text_content()[:5]
                .strip()
                .replace("Rep.", "")
            )
            role_VC = (
                CSS("#ctl00_ContentPlaceHolder1_lnkViceChair")
                .match_one(self.root)
                .text_content()[:10]
                .strip()
                .replace("Rep.", "")
            )
            com.add_member(Chair_member, role_C)
            com.add_member(VC_member, role_VC)
        except SelectorError:
            CoChair_member = (
                CSS("#ctl00_ContentPlaceHolder1_lnkChair")
                .match_one(self.root)
                .getchildren()[0]
                .tail.strip()
                .replace("Rep.", "")
            )
            role_CoC = (
                CSS("#ctl00_ContentPlaceHolder1_lnkChair")
                .match_one(self.root)
                .text_content()[:10]
                .strip()
                .replace("Rep.", "")
            )
            com.add_member(CoChair_member, role_CoC)
        try:
            members = CSS("#ctl00_ContentPlaceHolder1_dlstMembers td").match(self.root)
            for member in members:
                name = member.text_content().replace("Rep.", "")
                role = "member"
                if name:
                    com.add_member(name, role)
        except SelectorError:
            members = CSS("#ctl00_ContentPlaceHolder1_dlstHMembers td").match(self.root)
            for member in members:
                name = member.text_content().replace("Rep.", "")
                role = "member"
                if name:
                    com.add_member(name, role)
        return com


class CommitteeList(HtmlListPage):
    def process_item(self, item):
        com_link = CSS("a").match(item)[0]
        name = com_link.text_content()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = com_link.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")
        # return com
        return HouseCommitteeDetail(com, source=detail_link)


class HouseCommitteeList(CommitteeList):
    selector = CSS("#ctl00_ContentPlaceHolder1_dgrdCommittee_GridData td")
    source = "https://www.okhouse.gov/Committees/Default.aspx"
    chamber = "lower"


class JointCommitteeList(CommitteeList):
    selector = CSS("#ctl00_ContentPlaceHolder1_rgdJoint_GridData td")
    source = "https://www.okhouse.gov/Committees/Default.aspx"
    chamber = "legislature"


class ConfrenceCommitteeList(CommitteeList):
    selector = CSS("#ctl00_ContentPlaceHolder1_rgdConference_GridData td")
    source = "https://www.okhouse.gov/Committees/Default.aspx"
    chamber = "legislature"


class SpecialCommitteeList(CommitteeList):
    selector = CSS("#ctl00_ContentPlaceHolder1_rgdSpecial_GridData td")
    source = "https://www.okhouse.gov/Committees/Default.aspx"
    chamber = "legislature"


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
        detail_link = item.get("href")
        return SenateCommitteeDetail(com, source=detail_link)


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committees"])
