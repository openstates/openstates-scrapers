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
    parent_candidate = None

    def process_item(self, item):

        name = item.text_content().strip()

        # Only committees have parens abbreviation: "Commerce and Labor (CL)"
        #   while subcommittees are just listed as: "Audit" or "Human Services"
        if "(" in name:
            name = " ".join(name.split("(")[:-1]).strip()
            classification = "committee"
            parent = None
            self.parent_candidate = name
        else:
            classification = "subcommittee"
            parent = self.parent_candidate

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
            classification=classification,
            parent=parent,
        )

        committee_id = item.get("href").split("/")[
            8
        ]  # committee number is after the 6th slash in the href

        # committee member list also comes from a sub-page request
        detail_source = (
            "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Committee/"
            f"FillSelectedCommitteeTab?selectedTab=Overview&committeeOrSubCommitteeKey={committee_id}"
        )

        com.add_source(self.source.url, note="Committees list page")
        com.add_source(detail_source, note="Committee detail page")
        com.add_link(detail_source, note="homepage")

        return CommitteeDetail(com, source=detail_source)


class Assembly(CommitteeList):
    selector = XPath(
        ".//h2[contains(text(), 'Assembly')]/parent::div//div"
        "[@class='list-group-item']//a[not(contains(text(), 'View Meetings'))]"
    )
    chamber = "lower"


class Senate(CommitteeList):
    selector = XPath(
        ".//h2[contains(text(), 'Senate')]/parent::div//div"
        "[@class='list-group-item']//a[not(contains(text(), 'View Meetings'))]"
    )
    chamber = "upper"
