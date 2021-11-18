from spatula import CSS, HtmlPage, HtmlListPage
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    example_source = "http://www.kslegislature.org/li/b2021_22/committees/ctte_s_agriculture_and_natural_resources_1/"
    example_input = "Senate Committee on Agriculture and Natural Resources"

    def process_page(self):
        com = self.input
        members = CSS("#sidebar ul li a").match(self.root)
        rolez = CSS("#sidebar h3").match(self.root)
        if len(rolez) == 4:
            member_Chair = rolez[0].text
            member_Vice = rolez[1].text
            member_M = "Member"

            Chair_Mem = members[0]
            com.add_member(
                Chair_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Chair,
            )
            Vice_Mem = members[1]
            com.add_member(
                Vice_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Vice,
            )
            Member_Mems = members[2:]
            for mem in Member_Mems:
                member = mem.text.strip()
                role_m = member_M
                com.add_member(
                    member.replace("Rep.", "").replace("Sen.", "").strip(), role_m
                )
        elif len(rolez) == 6:
            member_Chair = rolez[0].text
            member_Vice = rolez[1].text
            member_M = "Member"

            Chair_Mem = members[0]
            com.add_member(
                Chair_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Chair,
            )
            Vice_Mem = members[1]
            com.add_member(
                Vice_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Vice,
            )
            Member_Mems = members[2:]
            for mem in Member_Mems:
                member = mem.text.strip()
                role_m = member_M
                com.add_member(
                    member.replace("Rep.", "").replace("Sen.", "").strip(), role_m
                )
        elif len(rolez) == 5:
            member_Chair = rolez[0].text
            member_Vice = rolez[1].text
            member_Minor = rolez[2].text
            member_M = "Member"
            Chair_Mem = members[0]
            com.add_member(
                Chair_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Chair,
            )
            Vice_Mem = members[1]
            com.add_member(
                Vice_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Vice,
            )
            Minor_Mem = members[2]
            com.add_member(
                Minor_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Minor,
            )
            Member_Mems = members[3:]
            for mem in Member_Mems:
                member = mem.text.strip()
                role_m = member_M
                com.add_member(
                    member.replace("Rep.", "").replace("Sen.", "").strip(), role_m
                )
        elif len(rolez) == 3:
            member_Chair = rolez[0].text
            member_M = "Member"

            Chair_Mem = members[0]
            com.add_member(
                Chair_Mem.text.replace("Rep.", "").replace("Sen.", "").strip(),
                member_Chair,
            )
            Member_Mems = members[1:]
            for mem in Member_Mems:
                member = mem.text.strip()
                role_m = member_M
                com.add_member(
                    member.replace("Rep.", "").replace("Sen.", "").strip(), role_m
                )
        else:
            raise ValueError("no members scraped!")
        return com


class CommitteeList(HtmlListPage):
    def process_item(self, item):
        com_link = CSS("a").match(item)[0]
        name = com_link.text
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = com_link.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        return CommitteeDetail(com, source=detail_link)


class Senate1CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "upper"
    selector = CSS("#senate-standing-comm-tab-1 li")


class Senate2CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "upper"
    selector = CSS("#senate-standing-comm-tab-2 li")


class House1CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "lower"
    selector = CSS("#house-standing-comm-tab-1 li")


class House2CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "lower"
    selector = CSS("#house-standing-comm-tab-2 li")


class Joint1CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "legislature"
    selector = CSS("#joint-comm-tab-1 li")


class Other1CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "legislature"
    selector = CSS("#other-comm-tab-1 li")


class Special1CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "legislature"
    selector = CSS("#special-comm-tab-1 li")


class Sub1CommittteeList(CommitteeList):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "legislature"
    selector = CSS("#subcommittee-comm-tab-1 li")


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])
