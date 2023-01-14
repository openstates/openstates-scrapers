from spatula import XPath, URL, HtmlListPage, HtmlPage, SkipItem
from openstates.models import ScrapeCommittee


class CommitteeList(HtmlListPage):
    source = URL(
        "https://www.legis.iowa.gov/committees"
    )
    # Committee pages selector
    selector = XPath("//*[@id=\"content\"]/section/section/div/section/ul/li[*]")
    def process_item(self, item):
        homeUrl = self.source.url
        com = CommitteeDetails(homeUrl, source = XPath("./a/@href").match_one(item))
        return com
        
class CommitteeDetails(HtmlPage):
    def process_page(self):
        # Helper method to parse member list item strings
        def _parseMemberString(member:str, com:ScrapeCommittee):
            if member.lower() == "no member data available":
                return
            # H/S members have (party/district) info
            if "(" in member:
                memberName = member.split("(", 1)[0].strip()
                memberRole = member.rsplit(")", 1)[1].strip()
                if len(memberRole) > 0:
                    memberRole = memberRole.split(",", 1)[1].strip()
                    com.add_member(name=memberName, role=memberRole)
                else:
                    com.add_member(name=memberName)
            # Public members have names, role
            elif "," in member:
                memberName, memberRole = member.split(",", 1)
                if len(memberRole) > 0:
                    com.add_member(name=memberName.strip(), role=memberRole.strip())
            else:
                memberName = member.strip()
                if len(memberName) == 0:
                    return
                com.add_member(name=memberName)

        # page header holds name and chamber
        header = XPath("//*[@id=\"content\"]/div/section/h1").match_one(self.root).text.strip().rsplit(" ", 1)
        name = header[0]
        chamber = None
        if "s" in header[1].lower():
            chamber = "upper"
        elif "h" in header[1].lower():
            chamber = "lower"
        elif "j" in header[1].lower():
            chamber = "legislature"
        else:
            raise SkipItem("No chamber")
        
        # determines if subcommittee
        isSubcommittee=False
        if "subcommittee" in name.lower():
            isSubcommittee = True
            
        # Conditionally create because altering parent/classification
        # gives error
        com:ScrapeCommittee()
        if isSubcommittee:
            com = ScrapeCommittee(
            name=name,
            chamber=chamber,
            parent = "Appropriations",
            classification = "subcommittee"
            )
        else:
            com = ScrapeCommittee(
            name=name,
            chamber=chamber,
            classification = "committee"
            )
        com.add_source(self.source.url)
        # TODO Hard-coded
        com.add_source("https://www.legis.iowa.gov/committees", "Committee list page")
        # Get list of members contained in nested grid_12
        # Translation hack in case they switch to all-caps
        try:
            membersList = XPath(
                "//section/div/section[contains(@class, 'grid_12 alpha omega') and \
                (contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'house members') or \
                contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'senate members'))] //descendant::li"
                ).match(self.root)
        except:
            raise SkipItem("No Members")
        
        # Loop through member lis, parse textContent
        for member in membersList:
            member = member.text_content().strip()
            _parseMemberString(member, com)            
        return com