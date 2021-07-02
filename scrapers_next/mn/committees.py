from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.people.models.committees import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.senate.mn/committees/committee_bio.html?cmte_id=3087&ls=92"
    )

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)

        for link in XPath(
            '//div[contains(@class, "media-body")]//a[contains(@href, "member_bio")]'
        ).match(self.root):
            name = link.text_content().split(",")[0]
            if name:
                try:
                    positions = ("chair", "vice chair", "ranking minority member")
                    position = XPath("..//preceding-sibling::b/text()").match(link)
                    for role in position:
                        position_str = ""
                        position_str += role.lower()
                        if position_str not in positions:
                            raise ValueError("unknown position")
                except SelectorError:
                    position_str = "member"
            com.add_member(name, position_str)

        return com


#  todo: subcommittees!
class SenateCommitteeList(HtmlListPage):
    selector = CSS(" .card .list-group-flush .d-flex a")
    source = "https://www.senate.mn/committees"
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content().strip()

        com = ScrapeCommittee(name=name, parent=self.chamber)
        com.add_source(self.source.url)
        return SenateCommitteeDetail(com, source=item.get("href"))


class HouseCommitteeList(HtmlListPage):
    selector = CSS("list-group-flush list-group-item")
    source = "https://www.house.leg.state.mn.us/committees"
    chamber = "lower"
