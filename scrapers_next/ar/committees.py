from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapeCommittee


class SenList(HtmlListPage):
    source = URL("https://senate.arkansas.gov/senators/committees/")
    selector = CSS("ins > ul > li > a")

    def process_item(self, item):
        comm_name = item.text_content().strip()

        previous_sibs = item.getparent().getparent().itersiblings(preceding=True)
        for sib in previous_sibs:
            if len(sib.getchildren()) == 0:
                chamber_type = sib.text_content().strip()
                break

        if chamber_type == "Senate Committees":
            chamber = "upper"
        elif chamber_type == "Joint Committees":
            self.skip()
        elif chamber_type == "Task Forces":
            self.skip()

        com = ScrapeCommittee(
            name=comm_name,
            classification="committee",
            chamber=chamber,
        )

        return com


# class House(CommList):
#     source = URL("https://www.arkleg.state.ar.us/Committees/List?type=House")
#     chamber = "lower"


# class Joint(CommList):
#     source = URL("https://www.arkleg.state.ar.us/Committees/List?type=Joint")
#     chamber = "legislature"
