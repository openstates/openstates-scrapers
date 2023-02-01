from spatula import XPath, URL, CSS, HtmlListPage, HtmlPage, SkipItem
from openstates.models import ScrapeCommittee

# what I need to scrape
    # name
    # chamber ("upper", "lower")
    # classification ("committee", "subcommittee")
    # parent (only if it is a subcommittee)
    # sources - link to home page, committee specific page - use add_source() from ScrapeCommittee
    # members - use add_member() from ScrapeCommittee

class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.capitol.hawaii.gov/legislature/committeepage.aspx?comm=AEN&year=2023"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url, note="Committee Details Page")

        # committee name


        # chamber

        # classification
        # parent (only if it is a subcommittee)

        
        
        # members 

        ### chairs

        ### vice chairs

        ### all non-chair members
        members = self.root.CSS("#table.ctl00_MainContent_DataList1 tbody")

        #for member in members:

        return com

        #example from other scraper_next

        # if not members:
        #     raise SkipItem(f"No membership data found for: {com.name}")

        # for member in members:
        #     member_text = member.text_content()

        #     if "vacancy" in member_text.lower():
        #         continue

        #     com_leader = leader_name_pos.search(member_text)
        #     com_member = member_name_pos.search(member_text)
        #     if com_leader:
        #         name, role = com_leader.groups()[1:]
        #     else:
        #         name, role = com_member.groups()[1], "Member"

        #     com.add_member(name=name, role=role)







class SenateCommitteeList(HtmlListPage):
    #run through loop of @id="sen", "house", "special" eventually to abstract away from Senate
    committee_type = "sen"
    chamber = "upper"
    
    source = "https://www.capitol.hawaii.gov/comminfolist.aspx"
    selector = CSS("#" + committee_type + "ul li")

    def process_item(self, item):
        
        committee_page = item.CSS("#h3 a.uw-rm-external-link-id").text_content
        self.add_source()

        
        name = item.text_content()
        
        # find 

        # com = ScrapeCommittee(
        #                  name=comm_name,
        #                  chamber=chamber,
        #                  classification="committee",
        #                  parent=parent,
        #              )





        