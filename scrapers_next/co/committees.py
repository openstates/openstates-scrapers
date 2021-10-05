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
        print("CHAMBER: ",chamber)
        com = ScrapeCommittee(name=self.input, chamber=chamber)

        members = CSS("div.member-details h4 a[href] ").match(self.root)
        for member in members:
            members_t = CSS("div:nth-child(1) div div.member-details").match(self.root)
            for member_t in members_t:
                member_title = CSS(".member-title").match_one(member_t).text
                member_role = CSS("span.member-role").match_one(member_t).text
                roles = ["Chair", "Vice Chair"]
                p_role = "member"
                for role in roles:
                    if role in member_role:
                        p_role = role
        com.add_member(member.text_content(), p_role, member_title)
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")
        return com

class CommitteeList(HtmlListPage):
    source = "https://leg.colorado.gov/content/committees"
    selector = CSS("div.view-content tbody a[href]")

    def process_item(self, item):
        name = item.text
        return CommitteeDetails(
            name, source="https://leg.colorado.gov/content/committees")