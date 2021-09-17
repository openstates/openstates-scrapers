from spatula import URL, CSS, HtmlListPage, SelectorError
from openstates.models import ScrapeCommittee


class SenList(HtmlListPage):
    source = URL("https://senate.arkansas.gov/senators/committees/")
    selector = CSS("ins > ul > li")

    def process_item(self, item):
        comm_name = CSS("a").match(item)[0].text_content().strip()

        previous_sibs = item.getparent().itersiblings(preceding=True)
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

        com.add_source(self.source.url)

        try:
            sub_committees = CSS("ul li a").match(item)
            for sub_comm in sub_committees:
                sub_name = sub_comm.text_content().strip()

                com = ScrapeCommittee(
                    name=sub_name,
                    classification="subcommittee",
                    chamber=chamber,
                    parent=comm_name,
                )
                return com
        except SelectorError:
            pass

        return com


# class House(CommList):
#     source = URL("https://www.arkleg.state.ar.us/Committees/List?type=House")
#     chamber = "lower"


# class Joint(CommList):
#     source = URL("https://www.arkleg.state.ar.us/Committees/List?type=Joint")
#     chamber = "legislature"
