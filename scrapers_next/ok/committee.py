from spatula import HtmlPage, CSS, HtmlListPage, SelectorError
from openstates.models import ScrapeCommittee
class SenateCommitteeDetail(HtmlPage):
    example_source = "https://oksenate.gov/committees/agriculture-and-wildlife"
    example_input = "Agriculture and Wildlife"
    def process_page(self):
        com = self.input
        try:
            members_name = CSS(
                "section.section.section_ind_f.section_bg-color_b div div div div a span"
            ).match(self.root)
            for member in members_name:
                name = member.text_content()
                member_role = "member"
                com.add_member(name, member_role)
        except SelectorError:
            pass
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
                com.add_member(name, role)
        except SelectorError:
            members = CSS("#ctl00_ContentPlaceHolder1_dlstHMembers td").match(self.root)
            for member in members:
                name = member.text_content().replace("Rep.", "")
                role = "member"
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
        #return com
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
        selector = CSS("div.bTiles__items")

        def process_item(self, item):
            com_link = CSS("a").match(item)[0]
            name = CSS("a div span.bTiles__title", num_items=15).match(item)[0].text_content()
            com = ScrapeCommittee(
                name=name, classification="committee", chamber=self.chamber
            )
            detail_link = com_link.get("href")
            com.add_source(detail_link)
            com.add_link(detail_link, note="homepage")
            # return com
            return SenateCommitteeDetail(com, source=detail_link)


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committees"])
