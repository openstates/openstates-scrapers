from spatula import HtmlPage, HtmlListPage, CSS, SelectorError, URL
from openstates.models import ScrapeCommittee


class CommitteeDetails(HtmlPage):
    example_source = "https://leg.col-orado.gov/committees/agriculture-livestock-water/2021-regular-session"
    example_input = "Agriculture and Livestock"

    def process_page(self):
        chamber = (
            CSS("span.committee-title.page-qualifying-title").match_one(self.root).text
        )
        if chamber == "House Committee of Reference":
            chamber = "lower"
        elif chamber == "Senate Committee of Reference":
            chamber = "upper"
        else:
            chamber = "legislature"
        com = ScrapeCommittee(name=self.input, chamber=chamber)
        members = CSS(".member ").match(self.root)
        for member in members:
            try:
                member_name = CSS("h4 a").match_one(member).text_content()
            except SelectorError:
                continue
            try:
                positions = ["Chair", "Vice Chair"]
                position = CSS("span.member-role").match_one(member).text_content()
                if position in positions:
                    member_role = position
            except SelectorError:
                member_role = "member"
            com.add_member(member_name, member_role)
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")
        return com


class CommitteeList(HtmlListPage):
    source = URL("https://leg.colorado.gov/content/committees", timeout=30)
    selector = CSS("div.view-content tbody a[href]", num_items=50)

    def process_item(self, item):
        name = item.text
        return CommitteeDetails(
            name, source=URL(CSS("a").match_one(item).get("href"), timeout=30)
        )


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["Committee"])
