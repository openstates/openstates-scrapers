from spatula import CSS, HtmlPage, HtmlListPage, XPath, SelectorError
from openstates.models import ScrapeCommittee


class HouseCommitteeDetail(HtmlPage):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/index.cfm?Code=32&CteeBody=H&SessYear=2021"
    input = "Aging & Older Adult Services"

    def process_page(self):
        com = self.input
        try:
            Chair_Member1 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a"
                )
                .match(self.root)[0]
                .text.strip()
            )
            Chair_Member_rolez_1 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[0]
                .text.strip()
            )
            com.add_member(Chair_Member1, Chair_Member_rolez_1)
            Chair_Member2 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a"
                )
                .match(self.root)[1]
                .text.strip()
            )
            Chair_Member_rolez_2 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[1]
                .text.strip()
            )
            com.add_member(Chair_Member2, Chair_Member_rolez_2)
        except IndexError:
            pass
        Members = XPath("/html/body/div/section/div/div[12]/div/div/div/div[2]").match(
            self.root
        )
        for mem in Members:
            try:
                member_name = XPath("div[1]/a").match_one(mem).text.strip()
                mem_position = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                mem_position = "Member"
            com.add_member(member_name, mem_position)
        Members_2 = XPath(
            "/html/body/div/section/div/div[14]/div/div/div/div[2]"
        ).match(self.root)
        for mem in Members_2:
            try:
                member_name2 = XPath("div[1]/a").match_one(mem).text.strip()
                mem_position2 = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                mem_position2 = "Member"
            com.add_member(member_name2, mem_position2)
        return com


class SenateCommitteeDetail(HtmlPage):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/index.cfm?Code=32&CteeBody=H&SessYear=2021"
    input = "Aging & Older Adult Services"

    def process_page(self):
        com = self.input
        try:
            Chair_Member1 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a"
                )
                .match(self.root)[0]
                .text.strip()
            )
            Chair_Member_rolez_1 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[0]
                .text.strip()
            )
            com.add_member(Chair_Member1, Chair_Member_rolez_1)
            Chair_Member2 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a"
                )
                .match(self.root)[1]
                .text.strip()
            )
            Chair_Member_rolez_2 = (
                CSS(
                    "div div div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[1]
                .text.strip()
            )
            com.add_member(Chair_Member2, Chair_Member_rolez_2)
        except IndexError:
            pass
        Members = XPath("/html/body/div/section/div/div[10]/div/div/div/div[2]").match(
            self.root
        )
        for mem in Members:
            try:
                member_name = XPath("div[1]/a").match_one(mem).text.strip()
                mem_position = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                mem_position = "Member"
            com.add_member(member_name, mem_position)
        Members_2 = XPath(
            "/html/body/div/section/div/div[12]/div/div/div/div[2]"
        ).match(self.root)
        for mem in Members_2:
            try:
                member_name2 = XPath("div[1]/a").match_one(mem).text.strip()
                mem_position2 = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                mem_position2 = "Member"
            com.add_member(member_name2, mem_position2)

        return com


class SenateCommitteeList(HtmlListPage):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=S"
    chamber = "upper"
    selector = CSS("table tbody tr td:nth-child(1) a")

    def process_item(self, item):
        name = item.text_content().strip()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = item.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        return SenateCommitteeDetail(com, source=detail_link)


class HouseCommitteeList(HtmlListPage):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=H"
    chamber = "lower"
    selector = CSS("table tbody tr td:nth-child(1) a")

    def process_item(self, item):
        name = item.text_content().strip()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = item.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        return HouseCommitteeDetail(com, source=detail_link)


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
