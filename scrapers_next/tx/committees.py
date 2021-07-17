import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    example_source = "https://capitol.texas.gov/Committees/MembershipCmte.aspx?LegSess=87R&CmteCode=C014"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        table = XPath("//div[@id='content']/table[2]/tr[position()>1]").match(self.root)
        for person in table:
            name = person.text_content()

            positions = ["chair", "vice chair"]
            if name:
                try:
                    label_text = XPath("./td[1]//text()").match(person)
                    for label in label_text:
                        label = label.lower()
                        if label.endswith(":"):
                            label = label[:-1]
                        if label in positions:
                            role = label
                        elif label == "members":
                            role = "member"
                        else:
                            self.warn(f"unknown role {label}")
                            role = "member"
                    name = person.text_content().split(":")[1]
                except SelectorError:
                    role = "member"

            # there are two spaces in between each name
            name = (
                name.replace("Sen.", "").replace("Rep.", "").replace("  ", " ").strip()
            )
            com.add_member(name, role)

        # extra information
        table = XPath("//div[@id='content']/table[1]/tr/td//text()").match(self.root)
        table = [
            info.replace("\r", "").replace("\n", "").replace("\t", "").replace(": ", "")
            for info in table
        ]

        # the fields, like "clerk", etc. are located at every odd indice
        # the information for each field, like the clerk's name, are located at every even indice
        fields = table[1::2]
        extra = table[2::2]
        num_of_fields = range(len(fields))

        for i in num_of_fields:
            com.extras[fields[i].lower()] = extra[i].strip()

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


class CommitteeList(HtmlListPage):
    selector = CSS("#content form ul li a")

    def process_item(self, item):
        name = item.text_content()
        if re.search(" - ", name):
            parent, name = name.split(" - ")

            # there is one subcommittee that has a shortened parent called "Approps."
            if parent == "Approps.":
                parent = "Appropriations"
            committee = ScrapeCommittee(
                name=name,
                classification="subcommittee",
                parent=parent,
                chamber=self.chamber,
            )
        else:
            committee = ScrapeCommittee(name=name, chamber=self.chamber)

        committee.add_source(self.source.url)
        return CommitteeDetail(committee, source=item.get("href"))


class SenateCommitteeList(CommitteeList):
    source = "https://capitol.texas.gov/Committees/CommitteesMbrs.aspx?Chamber=S"
    chamber = "upper"


class HouseCommitteeList(CommitteeList):
    source = "https://capitol.texas.gov/Committees/CommitteesMbrs.aspx?Chamber=H"
    chamber = "lower"
