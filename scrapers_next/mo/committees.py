from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, URL, SkipItem
from openstates.models import ScrapeCommittee
import re


leader_name_pos = re.compile(r"(Senator\s+|Repr.+tive\s+)(.+),\s+(.+),\s+.+")
member_name_pos = re.compile(r"(Senator\s+|Repr.+tive\s+)(.+),\s+.+")


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.senate.mo.gov/agri/"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url, note="Committee Details Page")

        members = self.root.xpath(".//div[@class='senator-Text']//strong")

        if not members:
            raise SkipItem(f"No membership data found for: {com.name}")

        for member in members:
            member_text = member.text_content()

            if "vacancy" in member_text.lower():
                continue

            com_leader = leader_name_pos.search(member_text)
            com_member = member_name_pos.search(member_text)
            if com_leader:
                name, role = com_leader.groups()[1:]
            else:
                name, role = com_member.groups()[1], "Member"

            com.add_member(name=name, role=role)

        return com


class SenateTypeCommitteeList(HtmlListPage):
    example_source = "https://www.senate.mo.gov/standing-committees/"
    selector = XPath(".//div[@id='main']//p//a[1]")
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content()

        if "hearing schedule" in name.lower():
            self.skip()

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
                    name_parent = [x.strip() for x in comm_name.split("-")]
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

            com.add_source(self.source.url, note="Committees List Page")

            return SenateCommitteeDetail(com, source=URL(item.get("href"), timeout=30))
        else:
            self.skip()


class SenateCommitteeList(HtmlListPage):
    source = "https://senate.mo.gov/Committees/"
    selector = XPath(".//div[@id='main']//li//a")

    def process_item(self, item):
        item_type = item.text_content()
        for com_type in ("standing", "statutory", "interim", "select"):
            if com_type in item_type.lower():
                return SenateTypeCommitteeList(source=URL(item.get("href"), timeout=30))
        else:
            self.skip()


class HouseCommitteeDetail(HtmlPage):

    example_source = (
        "https://www.house.mo.gov/MemberGridCluster.aspx?"
        "filter=compage&category=committee&Committees.aspx?"
        "category=all&committee=2571&year=2023&code=R"
    )

    def process_page(self):
        com = self.input
        com.add_source(self.source.url, note="Committee Details Page")
        link = self.source.url.replace(
            "MemberGridCluster.aspx?filter=compage&category=committee&", ""
        )
        com.add_link(link, note="homepage")

        # As of now, one committee's page is empty.
        # Just in case it is updated soon, the page will still be scraped
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
            raise SkipItem(f"No membership data found for: {com.name}")
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

        com.add_source(self.source.url, note="Committees List Page")

        # We can construct a URL that would make scraping easier,
        # as opposed to the link that is directly given
        comm_link = item.get("href").replace("https://www.house.mo.gov/", "")
        source = (
            "https://www.house.mo.gov/MemberGridCluster.aspx?"
            f"filter=compage&category=committee&{comm_link}"
        )
        return HouseCommitteeDetail(com, source=URL(source, timeout=30))
