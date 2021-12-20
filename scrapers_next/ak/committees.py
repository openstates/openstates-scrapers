from spatula import URL, CSS, HtmlListPage, HtmlPage, SkipItem
from openstates.models import ScrapeCommittee
import re


class CommiteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        # no members
        if (
            CSS("div.Membership fieldset").match_one(self.root).text_content().strip()
            == ""
        ):
            raise SkipItem("empty committee")

        members = CSS("fieldset div.area-holder ul.list li span.col01").match(self.root)

        num_members = 0
        for member in members:
            role = member.getnext().text_content().strip()
            # skip Public Members
            if role == "Public Member":
                continue

            if role == "Member":
                role = "member"

            num_members += 1
            mem_name = CSS("span span").match_one(member).text_content().strip()
            mem_name = re.search(r"(Representative|Senator)\s(.+)", mem_name).groups()[
                1
            ]

            com.add_member(mem_name, role)

        if not num_members:
            raise SkipItem("only public members")

        return com


class CommitteeList(HtmlListPage):
    source = URL("http://www.akleg.gov/basis/Committee/List/32")
    selector = CSS("div.area-frame ul.list li", num_items=112)

    def process_item(self, item):
        comm_name = (
            item.text_content().strip().split(" (")[0].title().replace("(Fin Sub)", "")
        )

        if "Conference" in comm_name:
            self.skip()

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
                parent="Finance",
            )
        else:
            com = ScrapeCommittee(
                name=comm_name,
                classification="committee",
                chamber=chamber,
            )

        detail_link = CSS("a").match_one(item).get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return CommiteeDetail(com, source=URL(detail_link, timeout=30))
