from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, SkipItem
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.senate.mo.gov/agri/"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        members = CSS(".gallery .desc").match(self.root)

        if not members:
            raise SkipItem("empty committee")

        positions = ["Chairman", "Vice-Chairman"]
        for member in members:
            member_position = member.text_content().replace("Senator", "").split(", ")

            if (
                member_position[0] == "House Vacancy"
                or member_position[0] == "Senate Vacancy"
            ):
                continue

            member_pos_str = "member"
            member_name = (
                member_position[0].replace("Representative ", "").replace("Rep. ", "")
            )

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
        if "Joint" in name:
            chamber = "legislature"
        else:
            chamber = "upper"

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
                    parent = name_parent[0]
                    comm_name = name_parent[1].replace("Subcommittee", "")

                    com = ScrapeCommittee(
                        name=comm_name,
                        chamber=chamber,
                        classification="subcommittee",
                        parent=parent,
                    )
                else:
                    com = ScrapeCommittee(name=comm_name, chamber=chamber)
            else:
                com = ScrapeCommittee(name=name, chamber=chamber)

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

        # As of now, one committees page is empty. Just in case it is updated soon, the page will still be scraped
        try:
            members = CSS("#theTable tr").match(self.root)

            for member in members:
                # skip first row with table headers
                if member.text_content().strip() == "NamePartyPosition":
                    continue

                __, name, __, position = CSS("td").match(member)

                name = (
                    name.text_content()
                    .replace("Rep. ", "")
                    .replace("Sen. ", "")
                    .split(",")
                )
                name = name[1] + " " + name[0]

                if position.text_content():
                    position = position.text_content()
                else:
                    position = "member"

                com.add_member(name, position)
        except SelectorError:
            pass
        return com


def remove_comm(comm_name):
    return (
        comm_name.replace("Joint Committee on the", "")
        .replace("Joint Committee on", "")
        .replace("Special Committee on", "")
        .replace("Special Interim Committee on", "")
        .replace(", Standing", "")
        .replace(", Statutory", "")
        .replace(", Interim", "")
        .replace(", Special Standing", "")
    )


class HouseCommitteeList(HtmlListPage):
    source = "https://www.house.mo.gov/CommitteeHierarchy.aspx"
    selector = CSS("a")
    chamber = "lower"

    def process_item(self, item):
        committee_name = item.text_content()

        # only scrape joint coms on senate scrape
        if (
            "Joint" in committee_name
            or "Task Force" in committee_name
            or "Conference" in committee_name
        ):
            self.skip()

        committee_name = remove_comm(committee_name)
        committee_name = committee_name.strip()

        if "Subcommittee" in committee_name:
            name = committee_name.replace("Subcommittee on ", "").replace(
                ", Subcommittee", ""
            )

            parent = remove_comm(
                XPath("..//..//preceding-sibling::a").match(item)[0].text_content()
            )

            com = ScrapeCommittee(
                name=name,
                chamber=self.chamber,
                classification="subcommittee",
                parent=parent,
            )
        else:
            com = ScrapeCommittee(name=committee_name, chamber=self.chamber)

        # We can construct a URL that would make scraping easier, as opposed to the link that is directly given
        comm_link = item.get("href").replace("https://www.house.mo.gov/", "")
        source = f"https://www.house.mo.gov/MemberGridCluster.aspx?filter=compage&category=committee&{comm_link}"
        return HouseCommitteeDetail(com, source=source)
