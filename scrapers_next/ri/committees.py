from spatula import URL, HtmlListPage, XPath
from openstates.models import ScrapeCommittee


class CommitteeList(HtmlListPage):
    source = URL("https://www.rilegislature.gov/pages/committees.aspx")

    def process_item(self, item):

        name = item.text_content()

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
        )

        com.add_source(self.source.url)
        # source = item.get("href")

        return com


class House(CommitteeList):
    # selector = CSS("table .s4-wpTopTable table table tr")
    chamber = "lower"
    selector = XPath(
        "//*[@id='{4C4879FB-E046-42C7-BEC9-8F569B03E55D}-{811ABDBE-2D09-4586-8D38-D18203BD2C7E}']//a"
    )


class Senate(CommitteeList):
    # selector = CSS("table .s4-wpTopTable table table tr")
    chamber = "upper"
    selector = XPath(
        "//*[@id='{4C4879FB-E046-42C7-BEC9-8F569B03E55D}-{733ACC1D-0F41-4EB2-ABC2-0E815521BD5E}']//a"
    )


class Joint(CommitteeList):
    # selector = CSS("table .s4-wpTopTable table table tr")
    chamber = "legislature"
    selector = XPath(
        "//*[@id='{4C4879FB-E046-42C7-BEC9-8F569B03E55D}-{E09F0FD2-B6DF-4422-8B22-FBF09B2C85EB}']//a"
    )
