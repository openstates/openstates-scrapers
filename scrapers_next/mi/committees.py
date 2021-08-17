from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.senate.mn/committees/committee_bio.html?cmte_id=3087&ls=92"
    )

    def process_page(self):
        # com = self.input
        print("a new comm")


class SenateCommitteeList(HtmlListPage):
    source = "https://committees.senate.michigan.gov/"
    selector = CSS("form .col-md-6")
    chamber = "upper"

    def process_item(self, item):
        try:
            title = CSS("h3").match(item)
        except SelectorError:
            title = XPath("..//preceding-sibling::h3").match(item)

        for comm_name in title:
            # try:
            print(comm_name.text_content())
            comm_name = comm_name.text_content()
            # except SelectorError:
            if comm_name == "Standing Committees":
                for committee in CSS("ul li").match(item):

                    name = committee.text_content()
                    com = ScrapeCommittee(name=name, chamber=self.chamber)
                    # print("com", com)
                    # print("source OKAY", CSS("a").match_one(committee).get("href"))
                    source = CSS("a").match_one(committee).get("href")
                    # print("HERE")
                    return SenateCommitteeDetail(com, source=source)
            elif comm_name == "Appropriations Subcommittees":
                for committee in CSS("ul li").match(item):

                    name = committee.text_content()
                    com = ScrapeCommittee(
                        name=name,
                        classification="subcommittee",
                        chamber=self.chamber,
                        parent="Appropriations",
                    )
                    # print("com", com)
                    source = CSS("a").match_one(committee).get("href")
                    # print("HERE2")
                    return SenateCommitteeDetail(com, source=source)
            # return SenateCommitteeDetail(com, source=item.get("href"))


class HouseCommitteeList(HtmlListPage):
    source = "https://capitol.texas.gov/Committees/CommitteesMbrs.aspx?Chamber=H"
    chamber = "lower"
