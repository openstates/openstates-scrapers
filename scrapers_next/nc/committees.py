from spatula import HtmlPage, HtmlListPage, CSS
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    example_source = (
        "https://www.ncleg.gov/Committees/CommitteeInfo/SenateStanding/1162"
    )

    def get_role(self, text):
        if text.endswith("s"):
            text = text[:-1]
        return text.lower()

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)

        for membership_type in CSS("div#Membership h5").match(self.root):
            role = self.get_role(membership_type.text_content())
            # sibling div contains members
            members = [
                p.text_content() for p in CSS("a p").match(membership_type.getnext())
            ]
            for member in members:
                member = member.replace("Rep.", "").replace("Sen.", "").strip()
                com.add_member(member, role)

        return com


class CommitteeList(HtmlListPage):
    source = "https://www.ncleg.gov/committees"

    def process_item(self, item):
        return CommitteeDetail(
            ScrapeCommittee(
                name=item.text_content(),
                parent=self.chamber,
            ),
            source=item.get("href"),
        )


class HouseCommitteeList(CommitteeList):
    selector = CSS("#houseStandingSection a.list-group-item")
    chamber = "lower"


class SenateCommitteeList(CommitteeList):
    selector = CSS("#senateStandingSection a.list-group-item")
    chamber = "upper"
