from spatula import XPath, CSS, HtmlListPage, HtmlPage, SelectorError, SkipItem
from openstates.models import ScrapeCommittee
import re


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
    selector = XPath("//body/table/tr[3]/td[3]/table/tr[1]/td[1]/table[1]/td[@class ='content']")
    code = None
    last_parent = None
    count = 0
    current_committee_name = None
    def process_item(self, item):
        # find out which column were in using mode.
        Mode_Value = self.count % 3
        # check the count for the name
        # extract the name
        if Mode_Value == 0:
            self.current_committee_name = CSS("a").match(item)[0]

        # use the count to get the code
        elif Mode_Value == 1:
            self.code = item.text_content().strip()
        elif Mode_Value == 2:
            if item.text_content().strip() == "Not Scheduled":
                raise SkipItem("Not Scheduled")
            if re.search(r"-", str(self.code)):
                name = self.current_committee_name.text_content().strip()
                parent = self.last_parent
                com = ScrapeCommittee(
                    name=name,
                    classification="subcommittee",
                    chamber=self.chamber,
                    parent=parent)
            else:
                name = self.current_committee_name.text_content().strip()
                self.last_parent = name
                com = ScrapeCommittee(
                    name=name,
                    classification="committee",
                    chamber=self.chamber)
                detail_link = self.current_committee_name.get("href")
            com.add_source(detail_link, "homepage")
            return Committee_Detail(com, source=detail_link)



class HouseCommittee(HtmlListPage):
    source = "https://ilga.gov/house/committees/default.asp"
    chamber = "lower"
    selector = CSS("table:nth-child(7) tr:not(:first-child)")
    last_parent = None
    def process_item(self, item):
        #the tab link has the name.
        tab_link = CSS("td:nth-child(1) a").match(item)[0]
        #got the code to check for subcommittee
        code = CSS("td:nth-child(2)").match(item)[0].text_content()
        name = tab_link.text_content().strip()
        #Logic to get the subcommittee
        if re.search(r"-",str(code)):
            parent = self.last_parent
            com = ScrapeCommittee(
               name = name,
               classification = "subcommittee",
               chamber = self.chamber,
               parent = parent )
        else:
            self.last_parent = name
            com = ScrapeCommittee(
                name=name,
                classification="committee",
                chamber=self.chamber
            )
        detail_link = tab_link.get("href")
        com.add_source(detail_link)
        com.add_source(detail_link, "homepage")
        return Committee_Detail(com, source=detail_link)




if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
