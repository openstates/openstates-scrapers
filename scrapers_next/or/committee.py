from spatula import URL, HtmlListPage, HtmlPage, CSS
from openstates.models import ScrapeCommittee
import re


class CommitteeDetail(HtmlPage):
    example_source = URL(
        "https://olis.oregonlegislature.gov/liz/2023R1/Committees/JCT/CommitteeMembers"
    )

    def process_page(self):
        com = self.input
        members = CSS("tbody tr").match(self.root)
        for member in members:
            position, name = member.getchildren()
            name = re.sub(r"Senator |Representative ", "", name.text_content().strip())
            position = position.text_content().strip()
            com.add_member(name, position)
        return com


class CommitteeList(HtmlListPage):
    source = "https://olis.oregonlegislature.gov/liz/Committees/list/"

    def process_item(self, item):
        url_parts = item.get("href").split("/")
        comm_url = (
            f"https://olis.oregonlegislature.gov/liz/{url_parts[4]}/"
            f"Committees/{url_parts[6]}/CommitteeMembers"
        )

        try:
            parent = self.parent
        except AttributeError:
            parent = None

        com = ScrapeCommittee(
            name=item.text_content(),
            chamber=self.chamber,
            classification="subcommittee" if parent else "committee",
            parent=parent,
        )
        print(com.name)
        com.add_source(comm_url, note="Committee details page")
        com.add_link(comm_url, note="homepage")

        return CommitteeDetail(
            com,
            source=comm_url,
        )


class House(CommitteeList):
    selector = CSS("#HouseCommittees_search li a")
    chamber = "lower"


class Senate(CommitteeList):
    selector = CSS("#SenateCommittees_search li a")
    chamber = "upper"


class Joint(CommitteeList):
    selector = CSS("#JointCommittees_search > li > a")
    chamber = "legislature"


class WaysMeans(CommitteeList):
    selector = CSS("#JointCommittees_search > li > ul > li > a")
    chamber = "legislature"
    parent = "Ways and Means"
