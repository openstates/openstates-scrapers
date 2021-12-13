from spatula import CSS, HtmlPage, HtmlListPage, XPath, SelectorError
from openstates.models import ScrapeCommittee


class HouseCommitteeDetail(HtmlPage):
    example_source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/index.cfm?Code=32&CteeBody=H&SessYear=2021"
    example_name = "Aging & Older Adult Services"
    example_input = ScrapeCommittee(
        name=example_name, classification="committee", chamber="lower"
    )

    def process_page(self):
        com = self.input
        try:
            # This section has the chair memebers the regular, democratic and minority and the roles
            # main chair
            Chair_Member = (
                CSS("div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a")
                .match(self.root)[0]
                .text.strip()
            )
            # main chair role
            Chair_Member_role = (
                CSS(
                    "div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[0]
                .text.strip()
            )
            com.add_member(Chair_Member, Chair_Member_role)
            # Democratic Chair member and or the minority chair member
            Demo_Chair_Member = (
                CSS("div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a")
                .match(self.root)[1]
                .text.strip()
            )
            # Democratic Chair member and or the minority chair member role
            Demo_Chair_Member_role = (
                CSS(
                    "div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[1]
                .text.strip()
            )
            com.add_member(Demo_Chair_Member, Demo_Chair_Member_role)
        except IndexError:
            pass
        # Regular majority members and their roles
        Majority_Members = XPath("//div[12]/div/div/div/div[2]").match(self.root)
        for mem in Majority_Members:
            try:
                major_member_name = XPath("div[1]/a").match_one(mem).text.strip()
                major_mem_position = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                major_mem_position = "Member"
            com.add_member(major_member_name, major_mem_position)
        # Regular minority members and their roles
        Minority_Members = XPath("//div[14]/div/div/div/div[2]").match(self.root)
        for mem in Minority_Members:
            try:
                minor_member_name = XPath("div[1]/a").match_one(mem).text.strip()
                minor_mem_position = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                minor_mem_position = "Member"
            com.add_member(minor_member_name, minor_mem_position)
        return com


class SenateCommitteeDetail(HtmlPage):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/index.cfm?Code=32&CteeBody=H&SessYear=2021"
    example_name = "Aging & Older Adult Services"
    example_input = ScrapeCommittee(
        name=example_name, classification="committee", chamber="lower"
    )

    def process_page(self):
        com = self.input
        try:
            # This section has the chair memebers the regular, democratic and minority and the roles
            # main chair
            Chair_Member = (
                CSS("div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a")
                .match(self.root)[0]
                .text.strip()
            )
            # main chair role
            Chair_Member_role = (
                CSS(
                    "div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[0]
                .text.strip()
            )
            com.add_member(Chair_Member, Chair_Member_role)
            # Democratic Chair member and or the minority chair member
            Demo_Chair_Member = (
                CSS("div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a")
                .match(self.root)[1]
                .text.strip()
            )
            # Democratic Chair member and or the minority chair member role
            Demo_Chair_Member_role = (
                CSS(
                    "div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[1]
                .text.strip()
            )
            com.add_member(Demo_Chair_Member, Demo_Chair_Member_role)
        except IndexError:
            pass
        # Regular majority members and their roles
        Majority_Members = XPath("//div[10]/div/div/div/div[2]").match(self.root)
        for mem in Majority_Members:
            try:
                major_member_name = XPath("div[1]/a").match_one(mem).text.strip()
                major_mem_position = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                major_mem_position = "Member"
            com.add_member(major_member_name, major_mem_position)
        # Regular minority members and their roles
        Minority_Members = XPath("//div[12]/div/div/div/div[2]").match(self.root)
        for mem in Minority_Members:
            try:
                minor_member_name = XPath("div[1]/a").match_one(mem).text.strip()
                minor_mem_position = XPath("div[2]").match_one(mem).text.strip()
            except SelectorError:
                minor_mem_position = "Member"
            com.add_member(minor_member_name, minor_mem_position)
        return com


class SenateCommitteeList(HtmlListPage):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=S"
    chamber = "upper"
    selector = CSS("table tbody tr td:nth-child(1) a")
    # The list of various the Senate committees

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

    # The list of various the House committees

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
