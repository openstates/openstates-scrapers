import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://committees.senate.michigan.gov/details?com=ADVC&sessionId=14"
    )

    def process_page(self):
        # com = self.input
        # print("a new comm")
        # print("item name", )
        print("self source url", self.source.url)

        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        # committee chair
        # chair = CSS("#MainContent_HLChair").match_one(self.root).text_content().strip()
        # print("CHAIR: ", chair)

        # comm members
        members = CSS("#MainContent_BLMembers li").match(self.root)
        for member in members:

            member = member.text_content().strip().replace("(D)", "").replace("(R)", "")
            # print("here's a member: ", member)
            positions = ["Majority Vice Chair", "Minority Vice Chair", "Chair"]
            # if member.endswith("Majority Vice Chair"):
            #     position = "Majority Vice Chair"
            # if member.endswith("Minority Vice Chair"):
            #     position = "Majority Vice Chair"
            # if any(member for things in positions):
            #     print('what', things)

            # if any(ext in member for ext in positions):
            # print("okay then", positions)
            # print [extension for extension in positions if(extension in member)]
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
        if "Building" in meeting_location:
            meeting = re.split("(Building)", meeting_location)
            meeting = meeting[0] + meeting[1] + "; " + meeting[2]
        elif "Tower" in meeting_location:
            meeting = re.split("(Tower)", meeting_location)
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
                return None

        # for comm_name in title:
        #     # try:
        #     print(comm_name.text_content())
        #     comm_name = comm_name.text_content()
        #     # except SelectorError:
        #     if comm_name == "Standing Committees":
        #         for committee in CSS("ul li").match(item):

        #             name = committee.text_content()
        #             com = ScrapeCommittee(name=name, chamber=self.chamber)
        #         #     # print("com", com)
        #         #     # print("source OKAY", CSS("a").match_one(committee).get("href"))
        #             source = CSS("a").match_one(committee).get("href")
        #         #     # print("HERE")
        #             # yield SenateCommitteeDetail(com, source=source)
        #         # return [SenateCommitteeDetail(ScrapeCommittee(name=committee.text_content(), chamber=self.chamber), source=CSS("a").match_one(committee).get("href")) for committee in CSS("ul li").match(item)]
        #     elif comm_name == "Appropriations Subcommittees":
        #         for committee in CSS("ul li").match(item):

        #             name = committee.text_content()
        #             com = ScrapeCommittee(
        #                 name=name,
        #                 classification="subcommittee",
        #                 chamber=self.chamber,
        #                 parent="Appropriations",
        #             )
        #             # print("com", com)
        #             source = CSS("a").match_one(committee).get("href")
        # print("HERE2")
        # return SenateCommitteeDetail(com, source=source)
        # return SenateCommitteeDetail(com, source=item.get("href"))


class HouseCommitteeList(HtmlListPage):
    source = "https://capitol.texas.gov/Committees/CommitteesMbrs.aspx?Chamber=H"
    chamber = "lower"
