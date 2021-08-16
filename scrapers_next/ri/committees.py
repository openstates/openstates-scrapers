from spatula import URL, HtmlListPage, XPath, HtmlPage, CSS
from openstates.models import ScrapeCommittee
import re


class SubCommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        return com


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        members = XPath(
            "/html/body/div/table/tr[7]/td[2]/table/tr[2]/td/div/table/tr/td/table/tr"
        ).match(self.root)
        for member in members:
            if member.get("class") == "bodyCopyBL":
                continue

            name = CSS("td div").match(member)[0].text_content().strip()
            name = re.search(r"(Senator|Representative)\s(.+)", name).groups()[1]
            role = CSS("td div").match(member)[1].text_content().strip()
            com.add_member(name, role)

        return com


class CommitteeList(HtmlListPage):
    source = URL("https://www.rilegislature.gov/pages/committees.aspx")

    def process_item(self, item):

        name = item.text_content()

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
        )

        com.add_source(self.source.url)

        source = item.get("href")
        com.add_source(source)
        com.add_link(source, note="homepage")

        if re.search(r"Subcommittees", name):
            return SubCommitteeDetail(
                com,
                source=source,
            )
        return CommitteeDetail(
            com,
            source=source,
        )


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
