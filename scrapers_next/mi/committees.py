import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://committees.senate.michigan.gov/details?com=ADVC&sessionId=14"
    )

    def process_page(self):

        print("self source url", self.source.url)

        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        members = CSS("#MainContent_BLMembers li").match(self.root)
        for member in members:

            member = member.text_content().strip().replace("(D)", "").replace("(R)", "")
            positions = ["Majority Vice Chair", "Minority Vice Chair", "Chair"]

            for position in positions:
                if member.endswith(position):
                    position_str = position
                    break
                else:
                    position_str = "member"

            com.add_member(member.split("  ")[0], position_str)

        clerk = CSS("#MainContent_HLComClerk").match_one(self.root).text_content()

        com.extras["clerk"] = clerk
        com.extras["clerk phone number"] = (
            CSS("#MainContent_HLCCPhone").match_one(self.root).text_content()
        )

        com.extras["meeting time"] = (
            CSS("#MainContent_lblDayTime").match_one(self.root).text_content()
        )
        meeting_location = (
            CSS("#MainContent_lblLocation").match_one(self.root).text_content()
        )

        # This is some formatting to make the address easier to read
        if "Building" in meeting_location:
            meeting = re.split("(Building)", meeting_location)
            meeting = meeting[0] + meeting[1] + "; " + meeting[2]
            if " Room" in meeting_location:
                room = re.split("(Room)|(Building)", meeting_location)
                meeting = f"{room[0]}{room[1]}; {room[3]}{room[5]}; {room[6]}"
        elif "Tower" in meeting_location:
            meeting = re.split("(Tower)", meeting_location)
            if " Room" in meeting_location:
                room = re.split("(Room)|(Tower)", meeting_location)
                meeting = f"{room[0]}{room[1]}; {room[3]}{room[5]}; {room[6]}"
            else:
                meeting = meeting[0] + meeting[1] + "; " + meeting[2]

        elif "Call of the Chair" in meeting_location:
            meeting = "Call of the Chair"

        com.extras["meeting location"] = meeting

        com.add_link(CSS("#MainContent_HLcbr").match_one(self.root).get("href"))
        com.add_link(CSS("#MainContent_HyperLink1").match_one(self.root).get("href"))
        com.add_link(CSS("#MainContent_HLComAudio").match_one(self.root).get("href"))

        return com


class SenateCommitteeList(HtmlListPage):
    source = "https://committees.senate.michigan.gov/"
    selector = CSS("form .col-md-6 ul li")
    chamber = "upper"

    def process_item(self, item):
        try:
            title = XPath("..//preceding-sibling::h3/text()").match(item)

        except SelectorError:
            title = XPath("../../..//preceding-sibling::h3/text()").match(item)

        for comm_name in title:
            if (
                comm_name == "Standing Committees"
                or comm_name == "Appropriations Subcommittees"
            ):
                name_link = CSS("a").match_one(item)
                name = name_link.text_content()
                source = name_link.get("href")
                if comm_name == "Standing Committees":
                    com = ScrapeCommittee(name=name, chamber=self.chamber)
                else:
                    com = ScrapeCommittee(
                        name=name,
                        classification="subcommittee",
                        chamber=self.chamber,
                        parent="Appropriations",
                    )
                return SenateCommitteeDetail(com, source=source)
            else:
                self.skip()


class HouseCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.house.mi.gov/MHRPublic/CommitteeInfo.aspx?comcode=AGRI"
    )

    def process_page(self):
        print("self source url", self.source.url)

        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        member_position = CSS("#divMembers div").match(self.root)
        member_name = CSS("#divMembers a").match(self.root)

        positions = ["Majority Vice-Chair", "Minority Vice-Chair", "Committee Chair"]

        num_members = range(len(member_name))

        for i in num_members:
            member_pos_str = member_position[i].text_content()
            pos = "member"
            for position in positions:
                if position in member_pos_str:
                    pos = position
            com.add_member(member_name[i].text_content(), pos)

        com.extras["clerk"] = CSS("#divClerk a").match_one(self.root).text_content()
        com.extras["clerk phone number"] = (
            CSS("#divClerk").match_one(self.root).text_content()[-10:]
        )

        com.add_link(CSS("#lnkSubscribe").match_one(self.root).get("href"))
        com.add_link(CSS("#hlPublicVCommitteeSched").match_one(self.root).get("href"))

        # attempt at subcommittees
        # try:
        #     subcommittee = CSS("#lnkSubcommittees").match_one(self.root).get("href")
        #     print("SUBCOMM link", subcommittee)
        #     # return HouseSubcommittees(com, source=subcommittee)
        # except SelectorError:
        #     print("no subcom")
        #     pass

        # subcommittee = CSS("#lnkSubcommittees").match_one(self.root).get("href")
        # if subcommittee is not None:
        #     print("SUBCOMM link", subcommittee)
        #     return com, HouseSubcommittees(com, source=subcommittee)
        # else:

        return com


class HouseSubcommitteeDetail(HtmlListPage):
    example_source = "https://www.house.mi.gov/MHRPublic/SubCommittee.aspx?comcode=APPR"
    selector = CSS("#DataList1 tr td")
    chamber = "lower"

    def process_item(self, item):

        com = ScrapeCommittee(
            name="name",
            classification="subcommittee",
            chamber=self.chamber,
            parent=CSS("#lblTitle")
            .match_one(self.root)
            .text_content()
            .replace("HOUSE", "")
            .replace("SUBCOMMITTEES", ""),
        )
        return com


# Due to faulty subcommittee webpages, this doesn't work as intended right now
class HouseSubcommitteeList(HtmlListPage):
    source = "https://www.house.mi.gov/mhrpublic/committee.aspx"
    selector = CSS("select option")
    chamber = "lower"

    def process_item(self, item):
        name = item.text_content()
        if name != "Statutory Committees" and name != "Select One":
            comcode = item.get("value")
            return HouseSubcommitteeDetail(
                source="https://www.house.mi.gov/MHRPublic/SubCommittee.aspx?comcode="
                + comcode,
            )
        else:
            self.skip()


class HouseCommitteeList(HtmlListPage):
    source = "https://www.house.mi.gov/mhrpublic/committee.aspx"
    selector = CSS("select option")
    chamber = "lower"

    def process_item(self, item):
        name = item.text_content()
        if name != "Statutory Committees" and name != "Select One":
            comcode = item.get("value")

            com = ScrapeCommittee(name=name, chamber=self.chamber)
            return HouseCommitteeDetail(
                com,
                source="https://www.house.mi.gov/MHRPublic/CommitteeInfo.aspx?comcode="
                + comcode,
            )
        else:
            self.skip()
