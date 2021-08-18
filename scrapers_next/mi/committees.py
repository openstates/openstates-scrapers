from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.senate.mn/committees/committee_bio.html?cmte_id=3087&ls=92"
    )

    def process_page(self):
        # com = self.input
        print("a new comm")
        # print("item name", )
        print("self source url", self.source.url)


class SenateCommitteeList(HtmlListPage):
    source = "https://committees.senate.michigan.gov/"
    selector = CSS("form .col-md-6 ul li")
    # since im passing the selector off to another function, selector must be the actual link?
    chamber = "upper"

    def process_item(self, item):
        try:
            # title = CSS("h3").match(item)
            title = XPath("..//preceding-sibling::h3/text()").match(item)
            # print("try title", title)

        except SelectorError:
            title = XPath("../../..//preceding-sibling::h3/text()").match(item)
            # print("try title", title)

        for comm_name in title:
            # print("single title", comm_name)

            #    for comm_name in title:
            # print("single title:", comm_name)
            if (
                comm_name == "Standing Committees"
                or comm_name == "Appropriations Subcommittees"
            ):
                name_link = CSS("a").match_one(item)
                name = name_link.text_content()
                # print("NAME: ", name)
                source = name_link.get("href")
                # print("source: ", source)
                if comm_name == "Standing Committees":
                    com = ScrapeCommittee(name=name, chamber=self.chamber)
                else:
                    com = ScrapeCommittee(
                        name=name,
                        classification="subcommittee",
                        chamber=self.chamber,
                        parent="Appropriations",
                    )
                return SenateCommitteeDetail(com, source=source)

        # for comm_name in title:
        #     # try:
        #     print(comm_name.text_content())
        #     comm_name = comm_name.text_content()
        #     # except SelectorError:
        #     if comm_name == "Standing Committees":
        #         for committee in CSS("ul li").match(item):

        #             name = committee.text_content()
        #             com = ScrapeCommittee(name=name, chamber=self.chamber)
        #         #     # print("com", com)
        #         #     # print("source OKAY", CSS("a").match_one(committee).get("href"))
        #             source = CSS("a").match_one(committee).get("href")
        #         #     # print("HERE")
        #             # yield SenateCommitteeDetail(com, source=source)
        #         # return [SenateCommitteeDetail(ScrapeCommittee(name=committee.text_content(), chamber=self.chamber), source=CSS("a").match_one(committee).get("href")) for committee in CSS("ul li").match(item)]
        #     elif comm_name == "Appropriations Subcommittees":
        #         for committee in CSS("ul li").match(item):

        #             name = committee.text_content()
        #             com = ScrapeCommittee(
        #                 name=name,
        #                 classification="subcommittee",
        #                 chamber=self.chamber,
        #                 parent="Appropriations",
        #             )
        #             # print("com", com)
        #             source = CSS("a").match_one(committee).get("href")
        # print("HERE2")
        # return SenateCommitteeDetail(com, source=source)
        # return SenateCommitteeDetail(com, source=item.get("href"))


class HouseCommitteeList(HtmlListPage):
    source = "https://capitol.texas.gov/Committees/CommitteesMbrs.aspx?Chamber=H"
    chamber = "lower"
