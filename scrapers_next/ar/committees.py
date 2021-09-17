from spatula import URL, CSS, HtmlListPage
from openstates.models import ScrapeCommittee


class SenSubComms(HtmlListPage):
    source = URL("https://senate.arkansas.gov/senators/committees/")
    selector = CSS("ins > ul > li > ul > li", num_items=87)

    def process_item(self, item):
        sub_name = CSS("a").match_one(item).text_content().strip()

        previous_sibs = (
            item.getparent().getparent().getparent().itersiblings(preceding=True)
        )
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

        comm_name = (
            CSS("a").match(item.getparent().getparent())[0].text_content().strip()
        )

        com = ScrapeCommittee(
            name=sub_name,
            classification="subcommittee",
            chamber=chamber,
            parent=comm_name,
        )

        return com


class SenList(HtmlListPage):
    source = URL("https://senate.arkansas.gov/senators/committees/")
    selector = CSS("ins > ul > li", num_items=45)

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

        return com


# class House(CommList):
#     source = URL("https://www.arkleg.state.ar.us/Committees/List?type=House")
#     chamber = "lower"


# class Joint(CommList):
#     source = URL("https://www.arkleg.state.ar.us/Committees/List?type=Joint")
#     chamber = "legislature"
