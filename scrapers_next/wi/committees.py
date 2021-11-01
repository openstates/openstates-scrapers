from spatula import URL, CSS, HtmlListPage, HtmlPage
from openstates.models import ScrapeCommittee


class CommitteeDetails(HtmlPage):
    source = "https://docs.legis.wisconsin.gov/2021/committees/assembly/2349"
    input = "2021 Assembly Committee for Review of Administrative Rules"

    def process_page(self):
        com = self.input
        members = CSS("#members p").match(self.root)
        for member in members:
            member_name = member.text_content()
            # print(member_name)
            pos = "member"
            positions = ["(Chair)", "(Co-Chair)", "(Vice-Chair)"]
            for position in positions:
                if member_name.endswith(position):
                    pos = position.strip().replace("(", "").replace(")", "")

            com.add_member(
                member_name.split(" ", 1)[1]
                .strip()
                .replace("(Chair)", "")
                .replace("(Co-Chair)", "")
                .replace("(Vice-Chair)", ""),
                pos,
            )
        return com


class CommitteeList(HtmlListPage):
    selector = CSS("div ul li p a")

    def process_item(self, item):
        name = item.text_content().strip()
        com = ScrapeCommittee(
            name=name,
            classification="committee",
            chamber=self.chamber,
        )
        detail_link = item.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        return CommitteeDetails(com, source=detail_link)


class SenateCommitteeList(CommitteeList):
    source = URL("https://docs.legis.wisconsin.gov/2021/committees/senate")
    chamber = "upper"


class HouseCommitteeList(CommitteeList):
    source = URL("https://docs.legis.wisconsin.gov/2021/committees/assembly")
    chamber = "lower"


class JointCommitteeList(CommitteeList):
    source = URL("https://docs.legis.wisconsin.gov/2021/committees/joint")
    chamber = "legislature"


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])
