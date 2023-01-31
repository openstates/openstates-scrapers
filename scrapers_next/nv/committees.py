from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, URL, SkipItem
from openstates.models import ScrapeCommittee
import re, time


leader_name_pos = re.compile(r"(Senator\s+|Repr.+tive\s+)(.+),\s+(.+),\s+.+")
member_name_pos = re.compile(r"(Senator\s+|Repr.+tive\s+)(.+),\s+.+")


class CommitteeDetail(HtmlPage):
    example_source = "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Committee/398/Overview"

    # def postprocess_response(self):
    #     time.sleep(5)

    def process_page(self):
        com = self.input

        try:
           members = CSS("a.bio").match(self.root)
        except SelectorError:
            raise SkipItem('No members found')

        if not members:
            raise SkipItem(f"No membership data found for: {com.name}")

        for member in members:
            name = member.text_content()
            print(f"member name: {name}")
            print(f"tail to member:{member.tail}")
            role_text = member.tail.strip()

            if role_text:
                role = role_text.replace("- ", "")
            else:
                role = "Member"

            # com_leader = leader_name_pos.search(member_text)
            # com_member = member_name_pos.search(member_text)
            # if com_leader:
            #     name, role = com_leader.groups()[1:]
            # else:
            #     name, role = com_member.groups()[1], "Member"

            com.add_member(name=name, role=role)

        return com


# class SenateTypeCommitteeList(HtmlListPage):
#     example_source = "https://www.senate.mo.gov/standing-committees/"
#     selector = XPath(".//div[@id='main']//p//a[1]")
#     chamber = "upper"

#     def process_item(self, item):
#         name = item.text_content()

#         if "hearing schedule" in name.lower():
#             self.skip()

#         if "Joint" in name:
#             chamber = "legislature"
#         else:
#             chamber = "upper"

#         if (
#             name != "2021 Senate Committee Hearing Schedule"
#             and name != "Assigned Bills"
#             and name != "Committee Minutes"
#             and name != "Appointees To Be Considered"
#         ):
#             if "Committee" in name:

#                 comm_name = (
#                     name.replace("Joint Committee on the ", "")
#                     .replace("Joint Committee on ", "")
#                     .replace("Committee on ", "")
#                     .replace(" Committee", "")
#                 )

#                 if "Subcommittee" in name:
#                     name_parent = [x.strip() for x in comm_name.split("-")]
#                     parent = name_parent[0]
#                     comm_name = name_parent[1].replace("Subcommittee", "")

#                     com = ScrapeCommittee(
#                         name=comm_name,
#                         chamber=chamber,
#                         classification="subcommittee",
#                         parent=parent,
#                     )
#                 else:
#                     com = ScrapeCommittee(name=comm_name, chamber=chamber)
#             else:
#                 com = ScrapeCommittee(name=name, chamber=chamber)

#             com.add_source(self.source.url, note="Committees List Page")

#             return SenateCommitteeDetail(com, source=URL(item.get("href"), timeout=30))
#         else:
#             self.skip()


# class SenateCommitteeList(HtmlListPage):
#     source = "https://senate.mo.gov/Committees/"
#     selector = XPath(".//div[@id='main']//li//a")

#     def process_item(self, item):
#         item_type = item.text_content()
#         for com_type in ("standing", "statutory", "interim", "select"):
#             if com_type in item_type.lower():
#                 return SenateTypeCommitteeList(source=URL(item.get("href"), timeout=30))
#         else:
#             self.skip()


# class HouseCommitteeDetail(HtmlPage):

#     example_source = (
#         "https://www.house.mo.gov/MemberGridCluster.aspx?"
#         "filter=compage&category=committee&Committees.aspx?"
#         "category=all&committee=2571&year=2023&code=R"
#     )

#     def process_page(self):
#         com = self.input
#         com.add_source(self.source.url, note="Committee Details Page")
#         link = self.source.url.replace(
#             "MemberGridCluster.aspx?filter=compage&category=committee&", ""
#         )
#         com.add_link(link, note="homepage")

#         # As of now, one committee's page is empty.
#         # Just in case it is updated soon, the page will still be scraped
#         try:
#             members = CSS("#theTable tr").match(self.root)

#             for member in members:
#                 # skip first row with table headers
#                 if member.text_content().strip() == "NamePartyPosition":
#                     continue

#                 __, name, __, position = CSS("td").match(member)

#                 name = (
#                     name.text_content()
#                     .replace("Rep. ", "")
#                     .replace("Sen. ", "")
#                     .split(",")
#                 )
#                 name = name[1] + " " + name[0]

#                 if position.text_content():
#                     position = position.text_content()
#                 else:
#                     position = "member"

#                 com.add_member(name, position)
#         except SelectorError:
#             raise SkipItem(f"No membership data found for: {com.name}")
#         return com


class CommitteeList(HtmlListPage):
    # committee list doesn't actually come in with initial
    source = "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/HomeCommittee/LoadCommitteeListTab?selectedTab=List"
    selector = XPath('//div[@class="list-group-item"]//a')
    #hardcode for now
    chamber = "lower"

    # def postprocess_response(self) -> None:
    #     time.sleep(5)
    #     pass

    def process_item(self, item):

        print(item.text_content())
        committee_name = item.text_content().strip()

        if committee_name == 'View Meetings':
            self.skip()

        com = ScrapeCommittee(name=committee_name, chamber=self.chamber)

        committee_id = item.get("href").split("/")[8] # committee number is after the 6th slash in the href
        print(committee_id)
        detail_source = (
            "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Committee/"
            f"FillSelectedCommitteeTab?selectedTab=Overview&committeeOrSubCommitteeKey={committee_id}"
        )
        
        # detail_source = item.get("href")
        # print(detail_source)

        com.add_source(self.source.url, note="Committees List Page")
        com.add_source(detail_source, note="Committees Detail Page")

        return CommitteeDetail(com, source=detail_source)
