from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapeCommittee


class CommList(HtmlListPage):
    def process_item(self, item):
        comm_name = item.text_content().strip()

        com = ScrapeCommittee(
            name=comm_name,
            classification="committee",
            chamber=self.chamber,
        )

        com.add_source(self.source.url)

        return com


class Senate(CommList):
    source = URL(
        "http://www.legislature.state.al.us/aliswww/ISD/senate/SenateCommittees.aspx"
    )
    chamber = "upper"
    selector = CSS("li.interim_listpad a")


class House(CommList):
    source = URL(
        "http://www.legislature.state.al.us/aliswww/ISD/House/HouseCommittees.aspx"
    )
    chamber = "lower"
    selector = CSS("li.interim_listpad a")


class Joint(CommList):
    source = URL(
        "http://www.legislature.state.al.us/aliswww/ISD/House/JointInterimCommittees.aspx"
    )
    chamber = "legislature"
    selector = CSS("tr td a")
