from spatula import URL, CSS, HtmlListPage, SelectorError, XPath, HtmlPage
from openstates.models import ScrapeCommittee

class CommitteeDetails (HtmlPage):
    example_source = "https://docs.legis.wisconsin.gov/2021/committees/assembly/2349"
    example_input = "2021 Assembly Committee for Review of Administrative Rules"
    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note = "homepage" )
        members = CSS("#members p").match(self.root)
        for member in members:
            member_name = member.text_content()
            positions = ["(Chair)", "(Co-Chair)", "(Vice-Chair)"]
            for position in positions:
                if member_name.endswith(position):
                    pos_str = position.strip().replace("(","").replace(")","")
                    break
                else:
                    pos_str = "member"
            com.add_member(member_name.split(" ")[0], pos_str)
            return com



class CommitteeList(HtmlListPage):
    selector = CSS("div ul li p a")

    def process_item(self, item):
        name = item.text_content().strip()
        com = ScrapeCommittee(
            name = name,
            classification = "committee",
            chamber = self.chamber,
        )
        detail_link = item.get("href")
        com.add_source(detail_link )
        com.add_link(detail_link, "homepage")
        return CommitteeDetails(com, source = detail_link)







class SenateCommitteeList(CommitteeList):
    source = URL ("https://docs.legis.wisconsin.gov/2021/committees/senate")
    chamber = "upper"



class HouseCommitteeList(CommitteeList):
    source = URL ("https://docs.legis.wisconsin.gov/2021/committees/assembly")
    chamber = "lower"

class JointCommitteeList(CommitteeList):
    source = URL ("https://docs.legis.wisconsin.gov/2021/committees/joint")
    chamber = "legislature"