import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    example_source = "https://capitol.texas.gov/Committees/MembershipCmte.aspx?LegSess=87R&CmteCode=C014"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)

        table = XPath("//div[@id='content']/table[2]/tr[position()>1]").match(self.root)
        # table = CSS("#content p table tbody").match(self.root)
        # print(table)
        for person in table:
            # print(committee.text_content())
            # name = XPath("./td[0]//text()").match(committee)
            # print(name)
            name = person.text_content()
            # print("raw name", name)

            positions = ["chair", "vice chair"]
            # role = "filler"
            if name:
                try:
                    label_text = XPath("./td[1]//text()").match(person)
                    # print("label", label_text)
                    for label in label_text:
                        label = label.lower()
                        if label.endswith(":"):
                            label = label[:-1]
                            # ['Members:']
                        if label in positions:
                            # print("new role: ", label)
                            role = label
                        else:
                            role = "member"
                    name = person.text_content().split(":")[1]
                    # print("new name", name)
                except SelectorError:
                    # print("member")
                    role = "member"

            # there are two spaces in between each name
            name = (
                name.replace("Sen.", "").replace("Rep.", "").replace("  ", " ").strip()
            )
            com.add_member(name, role)

        # extra information
        table = XPath("//div[@id='content']/table[1]/tr/td//text()").match(self.root)
        table = [
            thing.replace("\r", "")
            .replace("\n", "")
            .replace("\t", "")
            .replace(": ", "")
            for thing in table
        ]

        hello = table[1::2]
        extra = table[2::2]

        for i in range(5):
            com.extras[hello[i].lower()] = extra[i].strip()

        # more links
        membership = CSS("#content #lnkCmteMbrHistory").match(self.root)
        meetings = XPath("//center//a[contains(@href, 'MeetingsByCmte')]").match(
            self.root
        )

        try:
            bills = XPath("//center//a[contains(@href, '/Reports/Report')]").match(
                self.root
            )
            links = membership + bills + meetings
        except SelectorError:
            links = membership + meetings

        for link in links:
            com.add_link(link.get("href"))

        return com


# problem: does not recognize some characters in name
class CommitteeList(HtmlListPage):
    selector = CSS("#content form ul li a")

    def process_item(self, item):
        name = item.text_content()
        if re.search(" - ", name):
            parent, name = name.split(" - ")
            committee = ScrapeCommittee(
                name=name, parent=parent, classification="subcommittee"
            )
        else:
            committee = ScrapeCommittee(name=name, parent=self.chamber)
        print(committee)
        # print(item.get("href"))
        committee.add_source(self.source.url)
        return CommitteeDetail(committee, source=item.get("href"))


class SenateCommitteeList(CommitteeList):
    source = "https://capitol.texas.gov/Committees/CommitteesMbrs.aspx?Chamber=S"
    chamber = "upper"


class HouseCommitteeList(CommitteeList):
    source = "https://capitol.texas.gov/Committees/CommitteesMbrs.aspx?Chamber=H"
    chamber = "lower"
