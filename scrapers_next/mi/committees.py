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

        # comm members
        members = CSS("#MainContent_BLMembers li").match(self.root)
        for member in members:

            member = member.text_content().strip().replace("(D)", "").replace("(R)", "")
            # print("here's a member: ", member)
            positions = ["Majority Vice Chair", "Minority Vice Chair", "Chair"]

            for position in positions:
                if member.endswith(position):
                    position_str = position
                    break
                else:
                    position_str = "member"
            # print("FINAL", member.split("  ")[0], position_str)

            com.add_member(member.split("  ")[0], position_str)

        # extras (clerk and phone number)
        clerk = CSS("#MainContent_HLComClerk").match_one(self.root).text_content()
        # print("CLERK", clerk)
        com.extras["clerk"] = clerk
        com.extras["clerk phone number"] = (
            CSS("#MainContent_HLCCPhone").match_one(self.root).text_content()
        )

        # meeting schedule
        # MainContent_lblDayTime
        com.extras["meeting time"] = (
            CSS("#MainContent_lblDayTime").match_one(self.root).text_content()
        )
        meeting_location = (
            CSS("#MainContent_lblLocation").match_one(self.root).text_content()
        )
        # meeting = meeting_location.split("(Building)")
        # TODO: still iffy for Approps comm: "Room, "

        # if "Room" is the last word on the line, add a space

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
                # meeting = room[0] + room[1] + "; " + meeting[0] + meeting[1] + "; " + meeting[2]
            else:
                meeting = meeting[0] + meeting[1] + "; " + meeting[2]
        # print("BUILDING MEETING", meeting)
        elif "Call of the Chair" in meeting_location:
            meeting = "Call of the Chair"

        print("MEETING", meeting)
        # TODO: add semicolon after "Building"
        com.extras["meeting location"] = (
            # CSS("#MainContent_lblLocation").match_one(self.root).text_content()
            meeting
        )

        # TODO: links are not directly related?
        com.add_link(CSS("#MainContent_HLcbr").match_one(self.root).get("href"))
        com.add_link(CSS("#MainContent_HyperLink1").match_one(self.root).get("href"))
        com.add_link(CSS("#MainContent_HLComAudio").match_one(self.root).get("href"))

        return com


class SenateCommitteeList(HtmlListPage):
    source = "https://committees.senate.michigan.gov/"
    selector = CSS("form .col-md-6 ul li")
    # since im passing the selector off to another function, selector must be the actual link?
    chamber = "upper"

    def process_item(self, item):
        try:
            # title = CSS("h3").match(item)
            title = XPath("..//preceding-sibling::h3/text()").match(item)
            # print("try title", title)

        except SelectorError:
            title = XPath("../../..//preceding-sibling::h3/text()").match(item)
            # print("try title", title)

        for comm_name in title:
            # print("single title", comm_name)

            #    for comm_name in title:
            # print("single title:", comm_name)
            if (
                comm_name == "Standing Committees"
                or comm_name == "Appropriations Subcommittees"
            ):
                name_link = CSS("a").match_one(item)
                name = name_link.text_content()
                # print("NAME: ", name)
                source = name_link.get("href")
                # print("source: ", source)
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
        # TODO: look for subcommittees
        com = self.input
        # com.add_source(self.source.url)
        # com.add_link(self.source.url, note="homepage")

        # comm members
        member_position = CSS("#divMembers div").match(self.root)
        member_name = CSS("#divMembers a").match(self.root)

        print("member pos", member_position)

        for i in member_position:
            print("here's a member pos REALLY", i.text_content())
        print("member name", member_name)

        positions = ["Majority Vice-Chair", "Minority Vice-Chair", "Committee Chair"]
        # TODO: warning if none of the positions are triggered?
        # TODO:

        # ex: [Majority Vice-Chair, 106th District, Committee Chair]
        num_members = range(len(member_name))

        for i in num_members:
            member_pos_str = member_position[i].text_content()

            # if member_pos_str in positions:
            # pos = member_pos_str
            # com.add_member(member_name[i], member_position[i])
            # if ["Majority Vice-Chair", "Minority Vice-Chair", "Committee Chair"] in member_pos_str:
            #     print("OH I SEE")
            pos = "member"
            for position in positions:
                if position in member_pos_str:
                    pos = position
                    # print("I WAS REACHED")
            # else:
            # pos = "member"
            # com.add_member(member_name[i], "member")
            print(member_name[i].text_content(), pos)
            # com.add_member(member_name[i], pos)

            # extra clerk info
        # clerk = CSS("#divClerk a").match_one(self.root).text_content()
        # clerk_phone = CSS("#divClerk").match_one(self.root).text_content()[-10:]
        # print(clerk, clerk_phone)

        com.extras["clerk"] = CSS("#divClerk a").match_one(self.root).text_content()
        com.extras["clerk phone number"] = (
            CSS("#divClerk").match_one(self.root).text_content()[-10:]
        )


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
