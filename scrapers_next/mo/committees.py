# import re
from spatula import HtmlPage, HtmlListPage, CSS
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.senate.mo.gov/agri/"

    def process_page(self):
        # com = self.input
        # com.add_source(self.source.url)
        # com.add_link(self.source.url, note="homepage")

        members = CSS(".gallery .desc").match(self.root)
        # TODO: are there more positions?

        positions = ["Chairman", "Vice-Chairman"]
        for member in members:
            member_position = member.text_content().replace("Senator", "").split(", ")

            member_pos_str = "member"
            member_name = member_position[0]

            for pos in positions:
                if pos in member_position:
                    member_pos_str = pos

            print("member", member_name, member_pos_str)
            # com.add_member(member_name, member_pos_str)


class SenateTypeCommitteeList(HtmlListPage):
    # Im guessing there are no subcommittees?
    # source = "https://www.senate.mo.gov/committee/"
    example_source = "https://www.senate.mo.gov/statutory-committees/"
    selector = CSS(".entry-content a")
    chamber = "upper"

    def process_item(self, item):
        # TODO: don't scrape the schedule in standing
        name = item.text_content()
        print("NAME", name)
        # com = ScrapeCommittee(name=name, chamber=self.chamber)

        if (
            name != "2021 Senate Committee Hearing Schedule"
            and name != "Assigned Bills"
            and name != "Committee Minutes"
            and name != "Appointees To Be Considered"
        ):
            if "Committee" in name:
                # name.split("Committee on", "").split("-", "")

                # "Joint, Capital Security" so take the last index here
                # Joint Committee on Legislative Research – Oversight Subcommittee
                # "Joint, Legislative Research, Oversight"
                # comm_name =
                print("So there's a committee listed in the above name")

                comm_name = (
                    name.replace("Joint Committee on the ", "")
                    .replace("Joint Committee on ", "")
                    .replace("Committee on ", "")
                    .replace(" Committee", "")
                )
                # comm_name = name.replace("Joint ", "").replace("Committee ", "").replace("on ", "").replace(" the ", "").replace(" Committee", "")
                # Legislative Research - Personnel Subcommittee
                # Legislative Research
                # Missouri Works Job Training Joint Legislative Oversight Committee
                if "Subcommittee" in name:
                    # there is a subcommittee
                    name_parent = comm_name.split(" – ")
                    print("NAME PAENT", name_parent)
                    comm_name = name_parent[0]
                    parent = name_parent[1].replace("Subcommittee", "")
                    print("NAME and parent", comm_name, parent)

                    com = ScrapeCommittee(
                        name=comm_name,
                        chamber=self.chamber,
                        classification="subcommittee",
                        parent=parent,
                    )
                else:
                    com = ScrapeCommittee(name=comm_name, chamber=self.chamber)
            else:
                com = ScrapeCommittee(name=name, chamber=self.chamber)
                # | Subcommittee
                # re.split('; |, ',str)

            return SenateCommitteeDetail(com, source=item.get("href"))
        else:
            self.skip()


class SenateCommitteeList(HtmlListPage):
    # Im guessing there are no subcommittees?
    source = "https://www.senate.mo.gov/committee/"
    selector = CSS("#post-90 a")
    # chamber = "upper"

    def process_item(self, item):
        # print("selector", item.text_content())

        type = item.text_content()
        print("type", type)
        # smarter way of doing this?
        if type == "Standing" or type == "Statutory":
            # print("EXCUSE")
            return SenateTypeCommitteeList(source=item.get("href"))
        else:
            # print("SKIPPED")
            self.skip()


# would it be better to have SenCommList, SenTypeList, and then Detail (with a )
