from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, URL, SkipItem
from openstates.models import ScrapeCommittee
import re, time


leader_name_pos = re.compile(r"(Senator\s+|Repr.+tive\s+)(.+),\s+(.+),\s+.+")
member_name_pos = re.compile(r"(Senator\s+|Repr.+tive\s+)(.+),\s+.+")


class CommitteeDetail(HtmlPage):
    example_source = "https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Committee/398/Overview"

    def process_page(self):
        com = self.input

        try:
            # one committee (probably Senate committee of the whole) doesn't have members listed
           members = CSS("a.bio").match(self.root)
        except SelectorError:
            raise SkipItem('No members found')

        if not members:
            raise SkipItem(f"No membership data found for: {com.name}")

        for member in members:
            name = member.text_content()
            # Chair and Vice-Chair immediately follow anchor tag:
            role_text = member.tail.strip()

            if role_text:
                # remove leading hyphen/space from role
                role = role_text.replace("- ", "")
            else:
                role = "Member"

            com.add_member(name=name, role=role)

        return com

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
