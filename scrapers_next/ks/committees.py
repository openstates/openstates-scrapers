from spatula import CSS, HtmlPage, HtmlListPage
from openstates.models import ScrapeCommittee

class HouseCommitteeDetail(HtmlPage):
    example_source = "http://www.kslegislature.org/li/b2021_22/committees/ctte_h_agriculture_1/"
    example_input = "House Committee on Agriculture"
    def process_page(self):
        com = self.input
        members = CSS("#sidebar ul li a").match(self.root)
        rolez = CSS("#sidebar h3").match(self.root)

        member_Chair = rolez[0].text
        member_Vice = rolez[1].text
        member_M = "Member"

        Chair_Mem = members[0]
        com.add_member(Chair_Mem.text.replace("Rep.",""), member_Chair)
        Vice_Mem = members[1]
        com.add_member(Vice_Mem.text.replace("Rep.",""),member_Vice)
        Member_Mems = members[2:]
        for mem in Member_Mems:
                 member = mem.text.strip()
                 role_m = member_M
                 com.add_member(member.replace("Rep.",""), role_m)
        return com

# class Senate1CommittteeList(HtmlListPage):
#     source = "http://www.kslegislature.org/li/b2021_22/committees/"
#     chamber = "upper"
#     selector = CSS("#senate-standing-comm-tab-1 li")

    # def process_item(self, item):
    #     com_link = CSS("a").match(item)[0]
    #     name = com_link.text
    #     com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
    #     detail_link = com_link.get("href")
    #     com.add_source(detail_link)
    #     com.add_link(detail_link, "homepage")
    #     return com
    #     #return SenateCommitteeDetail(com, source=detail_link)

# class Senate2CommittteeList(HtmlListPage):
#     source = "http://www.kslegislature.org/li/b2021_22/committees/"
#     chamber = "upper"
#     selector = CSS("#senate-standing-comm-tab-2 li")
#
#     def process_item(self, item):
#         com_link = CSS("a").match(item)[0]
#         name = com_link.text
#         com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
#         detail_link = com_link.get("href")
#         com.add_source(detail_link)
#         com.add_link(detail_link, "homepage")
#         return com
#         #return CommitteeDetail(com, source=detail_link)
#
class House1CommittteeList(HtmlListPage):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "lower"
    selector = CSS("#house-standing-comm-tab-1 li")

    def process_item(self, item):
        com_link = CSS("a").match(item)[0]
        name = com_link.text
        com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
        detail_link = com_link.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        #return com
        return HouseCommitteeDetail(com, source=detail_link)

class House2CommittteeList(HtmlListPage):
    source = "http://www.kslegislature.org/li/b2021_22/committees/"
    chamber = "lower"
    selector = CSS("#house-standing-comm-tab-2 li")

    def process_item(self, item):
        com_link = CSS("a").match(item)[0]
        name = com_link.text
        com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
        detail_link = com_link.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        #return com
        return HouseCommitteeDetail(com, source=detail_link)

# class Joint1CommittteeList(HtmlListPage):
#     source = "http://www.kslegislature.org/li/b2021_22/committees/"
#     chamber = "lower"
#     selector = CSS("#joint-comm-tab-1 li")
#
#     def process_item(self, item):
#         com_link = CSS("a").match(item)[0]
#         name = com_link.text
#         com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
#         detail_link = com_link.get("href")
#         com.add_source(detail_link)
#         com.add_link(detail_link, "homepage")
#         return com
#         #return CommitteeDetail(com, source=detail_link)
#
# class Other1CommittteeList(HtmlListPage):
#     source = "http://www.kslegislature.org/li/b2021_22/committees/"
#     chamber = "lower"
#     selector = CSS("#other-comm-tab-1 li")
#
#     def process_item(self, item):
#         com_link = CSS("a").match(item)[0]
#         name = com_link.text
#         com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
#         detail_link = com_link.get("href")
#         com.add_source(detail_link)
#         com.add_link(detail_link, "homepage")
#         return com
#         #return CommitteeDetail(com, source=detail_link)
#
#
# class Special1CommittteeList(HtmlListPage):
#     source = "http://www.kslegislature.org/li/b2021_22/committees/"
#     chamber = "lower"
#     selector = CSS("#special-comm-tab-1 li")
#
#     def process_item(self, item):
#         com_link = CSS("a").match(item)[0]
#         name = com_link.text
#         com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
#         detail_link = com_link.get("href")
#         com.add_source(detail_link)
#         com.add_link(detail_link, "homepage")
#         return com
#         #return CommitteeDetail(com, source=detail_link)
#
# class Sub1CommittteeList(HtmlListPage):
#     source = "http://www.kslegislature.org/li/b2021_22/committees/"
#     chamber = "lower"
#     selector = CSS("#subcommittee-comm-tab-1 li")
#
#     def process_item(self, item):
#         com_link = CSS("a").match(item)[0]
#         name = com_link.text
#         com = ScrapeCommittee(name=name, classification="committee", chamber=self.chamber)
#         detail_link = com_link.get("href")
#         com.add_source(detail_link)
#         com.add_link(detail_link, "homepage")
#         return com
#         #return CommitteeDetail(com, source=detail_link)

if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])

