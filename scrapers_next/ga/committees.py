from spatula import HtmlListPage, CSS, HtmlPage
from openstates.people.models.committees import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    # selector = CSS('ul .list-unstyled')[0]

    def process_page(self, item):
        return self.input


class CommitteeList(HtmlListPage):
    # selector = XPath("/html/body/app-root/div/main/app-committee-list/div[2]/app-loader/div[2]/div/app-chamber-committees/ul")

    def process_item(self, item):
        return CommitteeDetail(
            ScrapeCommittee(
                name=item.text_content(),
                parent=self.chamber,
            ),
            source=item.get("href"),
        )


class HouseCommitteeList(CommitteeList):
    source = "https://www.legis.ga.gov/committees/house"
    chamber = "lower"


class SenateCommitteeList(CommitteeList):
    source = "https://www.legis.ga.gov/committees/senate"
    chamber = "upper"
    selector = CSS("body app-root div.container main")
