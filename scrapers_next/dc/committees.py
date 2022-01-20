from spatula import CSS, HtmlListPage, URL, HtmlPage
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    example_source = "https://dccouncil.us/committees/committee-human-services/"
    example_input = "Committee on Human Services"

    def get_role(self, text):
        if text.endswith("s"):
            text = text[:-1]
        return text.lower()

    def process_page(self):
        com = self.input

        for member_type in CSS("div article div div h4 ").match(self.root):
            role = self.get_role(member_type.text_content())
            members = [p.text_content() for p in CSS("a").match(member_type.getnext())]
            for member in members:
                if member[:2] == "At":
                    member = member[22:].strip()
                elif member[:2] == "Wa":
                    member = member[21:].strip()
                elif member[:2] == "Ch":
                    member = member[8:].strip()
                com.add_member(member, role)

        return com


class CommitteeList(HtmlListPage):
    source = URL("https://dccouncil.us/committees-for-council-period-23/")
    selector = CSS("div ul li div")
    chamber = "legislature"

    def process_item(self, item):
        com_link = CSS("a").match(item)[0]
        name = com_link.text_content()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = com_link.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")
        return CommitteeDetail(com, source=detail_link)
