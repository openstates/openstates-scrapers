from spatula import XPath, CSS, HtmlListPage, HtmlPage, SelectorError
from openstates.models import ScrapeCommittee


class Committee_Detail(HtmlPage):
    example_source = "https://ilga.gov/senate/committees/members.asp?CommitteeID=2678"
    example_name = "Agriculture - Members"
    example_input = ScrapeCommittee(
        name=example_name, classification="committee", chamber="lower"
    )

    def process_page(self):
        com = self.input
        try:
            # Has all the members in the list
            Members = XPath("//table[2]/tr").match(self.root)
            for member in Members:
                # This is so that it skips the title row like "Role" and "Sentor" or "Rep"
                if member.get("bgcolor") == "navy":
                    continue
                # The name and the role is below.
                role = CSS("td.heading").match_one(member).text.replace(":", "").strip()
                Name = CSS("td.content a").match_one(member).text.strip()
                com.add_member(Name, role)
        except SelectorError:
            # This is because there are some committees that have no members
            role = "None"
            Name = "None"
            com.add_member(Name, role)
        return com


class SenateCommittee(HtmlListPage):
    source = "https://ilga.gov/senate/committees/default.asp"
    chamber = "upper"
    selector = CSS("tr")

    def process_item(self, item):
        tab_link = CSS("td.content a").match(item)[0]
        name = tab_link.text.strip()

        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = tab_link.get("href")
        com.add_source(detail_link)
        com.add_source(detail_link, "homepage")
        # return Committee_Detail(com, source=detail_link)
        return com


class HouseCommittee(HtmlListPage):
    source = "https://ilga.gov/house/committees/default.asp"
    chamber = "lower"
    selector = CSS("table:nth-child(7) tr:not(:first-child)")

    def process_item(self, item):
        tab_link = CSS("td:nth-child(1) a").match(item)[0]
        code = CSS("td:nth-child(2)").match(item)[0].text_content()
        name = tab_link.text_content().strip()
        dash = "-"

        if re.search(r"-", str(code)):
            if dash not in code.getprevious(self):
                parent = name.getprevious(self)
            else:
                parent = parent.getprevious(self)
            com = ScrapeCommittee(
                name=name,
                classification="subcommittee",
                chamber=self.chamber,
                parent=parent,
            )
        else:
            com = ScrapeCommittee(
                name=name, classification="committee", chamber=self.chamber
            )
        detail_link = tab_link.get("href")
        com.add_source(detail_link)
        com.add_source(detail_link, "homepage")
        # return Committee_Detail(com, source=detail_link)
        return com


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
