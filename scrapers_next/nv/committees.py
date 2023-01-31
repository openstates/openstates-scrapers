from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, SkipItem
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    example_source = (
        "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Committee/398/Overview"
    )

    def process_page(self):
        com = self.input

        try:
            # one committee (probably Senate committee of the whole) doesn't have members listed
            members = CSS("a.bio").match(self.root)
        except SelectorError:
            raise SkipItem("No members found")

        if not members:
            raise SkipItem(f"No membership data found for: {com.name}")

        for member in members:
            name = member.text_content()
            # Chair and Vice-Chair immediately follow anchor tag:
            role_text = member.tail.strip()

            if role_text:
                # remove leading hyphen/space from role
                role = role_text.replace("- ", "")
            else:
                role = "Member"

            com.add_member(name=name, role=role)

        return com


class CommitteeList(HtmlListPage):
    # committee list doesn't actually come in with initial page; have to get committee list from subpage call:
    source = "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/HomeCommittee/LoadCommitteeListTab?selectedTab=List"
    selector = XPath('//div[@class="list-group-item"]//a')
    # TODO: Add logic to properly set chamber - It appears in a H2 element with class 'card-header h3' above all the committees in that chamber
    # TODO: Add logic to correctly categorize subcommittees (Parents: Assembly Ways & Means, Senate Finance, probably more to be added.)
    chamber = "lower"

    def process_item(self, item):

        committee_name = item.text_content().strip()

        if committee_name == "View Meetings":
            self.skip()

        com = ScrapeCommittee(name=committee_name, chamber=self.chamber)

        committee_id = item.get("href").split("/")[
            8
        ]  # committee number is after the 6th slash in the href

        # committee member list also comes from a sub-page request
        detail_source = (
            "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Committee/"
            f"FillSelectedCommitteeTab?selectedTab=Overview&committeeOrSubCommitteeKey={committee_id}"
        )

        com.add_source(self.source.url, note="Committees List Page")
        com.add_source(detail_source, note="Committees Overview Page")

        return CommitteeDetail(com, source=detail_source)
