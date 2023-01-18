from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, SkipItem, URL, ListPage
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://wapp.capitol.tn.gov/apps/CommitteeInfo/SenateComm.aspx?ga=113&committeeKey=620000"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")
        
        class_officers = self.root.xpath(".//ul[@class='no-list members large small-block-grid-3']//a")
        for officer in class_officers:
            name_and_title = [x.strip() for x in officer.text_content().split("\r\n") if len(x)]
            name, title = name_and_title
            com.add_member(name, title)
    
        try:
            class_normal = self.root.xpath(".//ul[@class='members small-block-grid-4 no-list']")[0].text_content()
            class_normal = [x.strip().replace("  ", " ") for x in class_normal.split("\r\n") if len(x.strip())]
        except Exception:
            class_normal = []
            pass
        
        if class_normal:
            for person in class_normal:
                com.add_member(person, "member")

        return com


class SenateTypeAllCommitteeList(HtmlListPage):
    example_source = "https://wapp.capitol.tn.gov/apps/CommitteeInfo/AllSenate.aspx"
    selector = XPath("/html/body/div[1]/div/div/div/div[1]/div[*]/div/div[*]/dl/dt[*]/a")
    chamber = "upper"

    def process_item(self, item):

        comm_name = item.text_content()
        com = ScrapeCommittee(name=comm_name.strip(), chamber=self.chamber)

        return SenateCommitteeDetail(com, source=URL(item.get("href"), timeout=30))

