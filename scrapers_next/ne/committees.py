from spatula import HtmlListPage, HtmlPage, XPath
from openstates.models import ScrapeCommittee
import re

leader_re = re.compile(r"Sen.\s+(.+),\s+(.+)")
member_re = re.compile(r"Sen.\s+(.+)")


def get_name_role(member):
    leader = leader_re.search(member)
    member = member_re.search(member)
    if leader:
        name, role = leader.groups()
    else:
        name, role = member.groups()[0], "Member"
    return name, role


class StandingCommMembership(HtmlPage):
    example_source = (
        "https://nebraskalegislature.gov/committees/landing_pages/index.php?cid=1"
    )

    def process_page(self):
        comm = self.input
        membership = (
            self.root.xpath(".//div[@class='feature-heading']")[0]
            .getnext()
            .getchildren()
        )
        members = [x.text_content() for x in membership]
        for member in members:
            name, role = get_name_role(member)
            comm.add_member(name, role)

        return comm


class StandingCommList(HtmlListPage):
    source = "https://nebraskalegislature.gov/committees/standing-committees.php"
    selector = XPath(".//div[@class='list-group']//a")

    def process_item(self, item):
        comm_name = item.text_content().strip()
        irrelevant = (
            "Committee Hearings",
            "Legislative Calendar",
            "Tips on Testifying at a Committee Hearing",
        )
        if comm_name in irrelevant:
            self.skip()

        comm = ScrapeCommittee(
            name=comm_name,
            chamber="legislature",
            classification="committee",
        )

        comm.add_source(self.source.url, note="Standing Committees List Page")
        comm_url = item.get("href")
        comm.add_source(comm_url, note="Committee Details Page")
        comm.add_link(comm_url, note="homepage")

        return StandingCommMembership(comm, source=comm_url)


class SelectCommList(HtmlPage):
    source = "https://nebraskalegislature.gov/committees/select-committees.php"

    def process_page(self):
        comm_cards = XPath(".//div[@class='card mb-1']").match(self.root)

        for card in comm_cards:
            group = XPath("//div[@class='list-group']").match(card)

            if not group or "Sen." not in card.text_content():
                continue

            comm_name = card.text_content().strip().split("\n")[0].strip()

            comm = ScrapeCommittee(
                name=comm_name, chamber="legislature", classification="committee"
            )

            members = [x.text_content() for x in group[0].getchildren()]

            for member in members:
                name, role = get_name_role(member)
                comm.add_member(name, role)

            comm.add_source(self.source.url, note="Committees list page")
            comm.add_link(self.source.url, note="homepage")

            yield comm
