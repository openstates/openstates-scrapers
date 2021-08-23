# import re
from spatula import HtmlPage, HtmlListPage, CSS
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.senate.mo.gov/agri/"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        members = CSS(".gallery .desc").match(self.root)

        positions = ["Chairman", "Vice-Chairman"]
        for member in members:
            member_position = member.text_content().replace("Senator", "").split(", ")

            if (
                member_position[0] == "House Vacancy"
                or member_position[0] == "Senate Vacancy"
            ):
                continue

            member_pos_str = "member"
            member_name = member_position[0]

            for pos in positions:
                if pos in member_position:
                    member_pos_str = pos

            com.add_member(member_name, member_pos_str)

        return com


class SenateTypeCommitteeList(HtmlListPage):
    example_source = "https://www.senate.mo.gov/standing-committees/"
    selector = CSS(".entry-content a")
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content()

        if (
            name != "2021 Senate Committee Hearing Schedule"
            and name != "Assigned Bills"
            and name != "Committee Minutes"
            and name != "Appointees To Be Considered"
        ):
            if "Committee" in name:

                comm_name = (
                    name.replace("Joint Committee on the ", "")
                    .replace("Joint Committee on ", "")
                    .replace("Committee on ", "")
                    .replace(" Committee", "")
                )

                if "Subcommittee" in name:
                    name_parent = comm_name.split(" – ")
                    comm_name = name_parent[0]
                    parent = name_parent[1].replace("Subcommittee", "")

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

            return SenateCommitteeDetail(com, source=item.get("href"))
        else:
            self.skip()


class SenateCommitteeList(HtmlListPage):
    source = "https://www.senate.mo.gov/committee/"
    selector = CSS("#post-90 a")

    def process_item(self, item):

        type = item.text_content()
        if type == "Standing" or type == "Statutory":
            return SenateTypeCommitteeList(source=item.get("href"))
        else:
            self.skip()
