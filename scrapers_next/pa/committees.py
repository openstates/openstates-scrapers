from spatula import CSS, HtmlPage, HtmlListPage, SelectorError
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
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
            chair_member = (
                CSS("div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a")
                .match(self.root)[0]
                .text.strip()
            )
            # main chair role
            chair_member_role = (
                CSS(
                    "div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[0]
                .text.strip()
            )
        except IndexError:
            pass
        try:
            com.add_member(chair_member, chair_member_role)
            # Democratic Chair member and or the minority chair member
            demo_chair_member = (
                CSS("div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText a")
                .match(self.root)[1]
                .text.strip()
            )
            # Democratic Chair member and or the minority chair member role
            demo_chair_member_role = (
                CSS(
                    "div.MemberInfoList-MemberWrapper.ChairWrapper div.ChairNameText div"
                )
                .match(self.root)[1]
                .text.strip()
            )
            com.add_member(demo_chair_member, demo_chair_member_role)
        except IndexError:
            pass
        majority_members = CSS(
            ".Widget.CteeInfo-MajorityList .MemberInfoList-MemberWrapper.Member"
        ).match(self.root)
        for mem in majority_members:
            try:
                major_member_name = CSS("div a").match_one(mem).text.strip()
                major_mem_position = CSS(".position").match_one(mem).text.strip()
            except SelectorError:
                major_mem_position = "member"
            com.add_member(major_member_name, major_mem_position)
        minority_members = CSS(
            ".Widget.CteeInfo-MinorityList .MemberInfoList-MemberWrapper.Member"
        ).match(self.root)
        for mem in minority_members:
            try:
                minor_member_name = CSS("div a").match_one(mem).text.strip()
                minor_mem_position = CSS(".position").match_one(mem).text.strip()
            except SelectorError:
                minor_mem_position = "member"
            com.add_member(minor_member_name, minor_mem_position)
        return com


class CommitteeList(HtmlListPage):
    selector = CSS("table tbody tr td:nth-child(1) a")

    def process_item(self, item):
        name = item.text_content().strip()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = item.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        return CommitteeDetail(com, source=detail_link)


class SenateCommitteeList(CommitteeList):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=S"
    chamber = "upper"


class HouseCommitteeList(CommitteeList):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=H"
    chamber = "lower"
