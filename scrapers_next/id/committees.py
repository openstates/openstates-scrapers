from spatula import HtmlListPage, CSS, URL
from openstates.models import ScrapeCommittee


class JointCommitteeList(HtmlListPage):
    selector = CSS("div .vc-column-innner-wrapper ul li", num_items=5)

    def process_item(self, item):
        com_link = CSS("a").match_one(item)
        name = com_link.text_content()

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
        )

        detail_link = com_link.get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return com


class CommitteeList(HtmlListPage):
    selector = CSS("div .padding-one-top.hcode-inner-row")

    def process_item(self, item):
        name = CSS("strong").match(item)[0].text_content()

        # skip header row
        if name == "Committees":
            self.skip()

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
        )

        detail_link = CSS("a").match(item)[0].get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return com


class Senate(CommitteeList):
    source = URL("https://legislature.idaho.gov/committees/senatecommittees/")
    chamber = "upper"


class House(CommitteeList):
    source = URL("https://legislature.idaho.gov/committees/housecommittees/")
    chamber = "lower"


class Joint(JointCommitteeList):
    source = URL("https://legislature.idaho.gov/committees/jointcommittees/")
    chamber = "legislature"
