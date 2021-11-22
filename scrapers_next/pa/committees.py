from spatula import CSS, HtmlPage, HtmlListPage, XPath, SelectorError
from openstates.models import ScrapeCommittee

class HouseCommitteeDetail(HtmlPage):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/index.cfm?Code=32&CteeBody=H&SessYear=2021"
    input = "Aging & Older Adult Services"
    def process_page(self):
        com = self.input
        Members = CSS("body div section div div div div div:nth-child(2)").match(self.root)
        for mem in Members:
         try:
            Members_name = CSS("a").match_one(mem).text.strip()
            Members_pos = CSS("div.position").match_one(mem).text.strip()
            com.add_member(Members_name, Members_pos)
         except SelectorError:
            Members_pos = "Member"
            com.add_member(Members_name, Members_pos)
        return com


class CommitteeList(HtmlListPage):
    selector = CSS("table tbody tr td:nth-child(1) a")

    def process_item(self, item):
        name = item.text_content().strip()
        com = ScrapeCommittee(name = name, classification = "committee", chamber = self.chamber)
        detail_link = item.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        #return com
        return HouseCommitteeDetail(com, source=detail_link )

class SenateCommitteeList(CommitteeList):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=S"
    chamber = "upper"

class HouseCommitteeList(CommitteeList):
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=H"
    chamber = "lower"


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
