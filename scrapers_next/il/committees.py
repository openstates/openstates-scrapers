from spatula import XPath, CSS, HtmlListPage, HtmlPage, SelectorError
from openstates.models import ScrapeCommittee


class Committee_Detail(HtmlPage):
    example_source = "https://ilga.gov/senate/committees/members.asp?CommitteeID=2678"
    example_input = "Agriculture - Members"

    def process_page(self):
        com = self.input
        try:
            Members = XPath(
                "/html/body/table/tr[3]/td[3]/table/tr[1]/td/table[2]/tr"
            ).match(self.root)
            for member in Members:
                if member.get("bgcolor") == "navy":
                    continue
                role = CSS("td.heading").match_one(member).text.replace(":", "").strip()
                Name = CSS("td.content a").match_one(member).text.strip()
                com.add_member(Name, role)
        except SelectorError:
            role = "None"
            Name = "None"
            com.add_member(Name, role)
        return com


class CommitteeList(HtmlListPage):
    def process_item(self, item):
        name = item.text.strip()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = item.get("href")
        com.add_source(detail_link)
        com.add_source(detail_link, "homepage")
        return Committee_Detail(com, source=detail_link)
        # return com


class SenateCommittee(CommitteeList):
    source = "https://ilga.gov/senate/committees/default.asp"
    chamber = "upper"
    selector = CSS("tr td.content a")


class HouseCommittee(CommitteeList):
    source = "https://ilga.gov/house/committees/default.asp"
    chamber = "lower"
    selector = CSS("tr td.content a")


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])
