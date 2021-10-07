from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee

class CommitteeDetails(HtmlPage):
    example_source = "https://leg.colorado.gov/committees/agriculture-livestock-water/2021-regular-session"
    example_input = "Agriculture and Livestock"
    def process_page(self):
        chamber = CSS("span.committee-title.page-qualifying-title").match_one(self.root).text
        if chamber == "House Committee of Reference":
            chamber = "lower"
        elif chamber =="Senate Committee of Reference":
            chamber = "upper"
        else:
            chamber = "legislature"
        print("CHAMBER: ",chamber)
        com = ScrapeCommittee(name=self.input, chamber=chamber)
        members = CSS("div div.block-content div div:nth-child(1) div div.member-details").match(self.root)
        for member in members:
            member_name = CSS("h4 a").match_one(member).text
            try :
                member_role = CSS(".member-role").match_one(member).text
            except SelectorError:
                member_role = "member"
            com.add_member(member_name, member_role)
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")
        return com

class CommitteeList(HtmlListPage):
    source = "https://leg.colorado.gov/content/committees"
    selector = CSS("div.view-content tbody a[href]",num_items=49)

    def process_item(self, item):
        name = item.text
        return CommitteeDetails(
            name, source=CSS("a").match_one(item).get("href"))
