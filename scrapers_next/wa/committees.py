from spatula import HtmlListPage, HtmlPage, CSS
from openstates.models import ScrapeCommittee


# "//*[@id="housecommittees"]/h3/a"
# https://leg.wa.gov/legislature/_api/search/searchcenterurl
# "https://app.leg.wa.gov/ContentParts/LegislativeCommittees/Index"


"//*[@id='CommitteeMembers']/table/tbody/tr[1]/td[1]/a"


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        members = CSS("td a.ui-link").match(self.root)
        for member in members:
            dirty_name = member.text_content().strip().split(", ")
            last_name = dirty_name[0]
            first_name = dirty_name[1]
            name = first_name + " " + last_name

            role = member.getnext().getnext().getnext()
            # .getnext().getnext().getnext()
            # .tail()

            com.add_member(name, role)

        return com


class CommitteeList(HtmlListPage):
    # source = URL("https://app.leg.wa.gov/ContentParts/LegislativeCommittees/Index", headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'})
    # source = URL("https://leg.wa.gov/legislature/Pages/CommitteeListing.aspx")
    source = "https://app.leg.wa.gov/ContentParts/LegislativeCommittees/Index"
    selector = CSS("div ul li span a.ms-srch-item-link", num_items=57)

    def process_item(self, item):

        name = item.text_content().strip()
        print(name)

        com = ScrapeCommittee(
            name=name,
            # chamber=self.chamber,
        )

        com.add_source(self.source.url)
        source = item.get("href")
        com.add_source(source)
        com.add_link(source, note="homepage")

        return com
