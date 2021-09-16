from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapeCommittee


class CommitteeList(HtmlListPage):
    source = URL("http://www.akleg.gov/basis/Committee/List/32")
    selector = CSS("div.area-frame ul.list li", num_items=112)

    def process_item(self, item):
        comm_name = item.text_content().strip()

        chamber = item.getparent().getprevious().getprevious().text_content().strip()
        if chamber == "House":
            chamber = "lower"
        elif chamber == "Senate":
            chamber = "upper"
        elif chamber == "Joint Committee":
            chamber = "legislature"

        classification = item.getparent().getprevious().text_content().strip()

        if classification == "Finance Subcommittee":
            com = ScrapeCommittee(
                name=comm_name,
                classification="subcommittee",
                chamber=chamber,
                parent="FINANCE(FIN)",
            )
        else:
            com = ScrapeCommittee(
                name=comm_name,
                classification="committee",
                chamber=chamber,
            )

        return com


# class House(CommitteeList):
#     source = URL("http://www.akleg.gov/basis/Committee/List/32")
#     chamber = "lower"


# class Senate(CommitteeList):
#     source = URL("http://www.akleg.gov/basis/Committee/List/32")
#     chamber = "upper"


# class Joint(CommitteeList):
#     source = URL("http://www.akleg.gov/basis/Committee/List/32#tabCom3")
#     chamber = "legislature"
