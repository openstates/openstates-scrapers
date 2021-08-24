# import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
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


class HouseCommitteeDetail(HtmlPage):
    # example_source = "https://www.house.mo.gov/MemberGridCluster.aspx?filter=compage&category=committee&Committees.aspx?category=all&committee=2582&year=2021&code=R"
    example_source = "https://www.house.mo.gov/MemberGridCluster.aspx?filter=compage&category=committee&Committees.aspx?category=all&committee=2571&year=2021&code=R"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        link = self.source.url.replace(
            "MemberGridCluster.aspx?filter=compage&category=committee&", ""
        )
        com.add_link(link, note="homepage")

        # TODO: remember to add the link after constructing it

        # add members and positions

        try:
            members = CSS("#theTable tr").match(self.root)
            # print("MEMBERS", members)

            for member in members:
                # member = member.text_content()
                # print("NAMES", member.text_content())
                if member.text_content().strip() == "NamePartyPosition":
                    # print("TRIGG")
                    continue

                # member = member.text_content()
                # info = CSS("td").match(member)

                # for infos in info:
                __, name, __, position = CSS("td").match(member)
                # print("NAME", name.text_content())

                # rearrange name
                name = (
                    name.text_content()
                    .replace("Rep. ", "")
                    .replace("Sen. ", "")
                    .split(",")
                )
                name = name[1] + " " + name[0]
                # print("FINAL NAME", name)

                if position.text_content():
                    position = position.text_content()
                    # print("POSITION", position)
                else:
                    position = "member"
                # print("POSITION", position)
                com.add_member(name, position)
        except SelectorError:
            print("selector error")
            pass
        return com


# com.add_member(member_name, member_pos_str)


class HouseCommitteeList(HtmlListPage):
    source = "https://www.house.mo.gov/CommitteeHierarchy.aspx"
    selector = CSS("a")
    chamber = "lower"

    def process_item(self, item):
        # this seems to be the homepage: https://www.house.mo.gov/CommitteeDetail.aspx?filter=compage&committee=2497&year=2021&code=R%20&viewCode=&cluster=true
        # can be accessed through the current source a tags
        # but this is better:
        # from here: https://www.house.mo.gov/CommitteeHierarchy.aspx
        # craft a url: https://www.house.mo.gov/MemberGridCluster.aspx?filter=compage&category=committee&
        committee_name = item.text_content()

        committee_name = (
            committee_name.replace("Joint Committee on", "")
            .replace("Special Committee on", "")
            .replace("Special Interim Committee on", "")
            .replace(", Standing", "")
            .replace(", Statutory", "")
            .replace(", Interim", "")
            .replace(", Special Standing", "")
        )
        committee_name = committee_name.strip()
        # print(committee_name)

        if "Subcommittee" in committee_name:
            # Subcommittee on Appropriations - Public Safety, Corrections, Transportation and Revenue, Subcommittee
            # Appropriations - Public Safety, Corrections, Transportation and Revenue
            name = committee_name.replace("Subcommittee on ", "").replace(
                ", Subcommittee", ""
            )
            # print("name then parent", name)

            parent = (
                XPath("..//..//preceding-sibling::a")
                .match(item)[0]
                .text_content()
                .replace("Joint Committee on", "")
                .replace("Special Committee on", "")
                .replace("Special Interim Committee on", "")
                .replace(", Standing", "")
                .replace(", Interim", "")
                .replace(", Special Standing", "")
            )
            # print("PARENT", parent)

            com = ScrapeCommittee(
                name=name,
                chamber=self.chamber,
                classification="subcommittee",
                parent=parent,
            )

        else:
            com = ScrapeCommittee(name=committee_name, chamber=self.chamber)

        comm_link = item.get("href").replace("https://www.house.mo.gov/", "")
        source = f"https://www.house.mo.gov/MemberGridCluster.aspx?filter=compage&category=committee&{comm_link}"
        return HouseCommitteeDetail(com, source=source)
