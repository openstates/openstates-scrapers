import re
from spatula import HtmlPage, HtmlListPage, XPath, CSS, URL, SkipItem
from openstates.models import ScrapeCommittee
import lxml.html


class CommitteeList(HtmlListPage):
    selector = XPath("//div[@id='ctl00_ctl00_PageBody_PageContent_PanelHouseOrSenate']")
    classification = "committee"
    parent = None

    def process_item(self, item):
        # get content of each link item - committee name
        comm_name = item.text_content()
        comm_name = comm_name.strip()
        childs = item.getchildren()
        comm_url = item.get("href")

        print(f"Comm Name: \n{comm_name}")
        print(f"Children: \n{childs}")
        print(f"URL: \n{comm_url}")
        return


class CommitteeDetail(HtmlPage):
    def process_page(self):
        mem = CSS("card-R22").match_one(self.root)
        # hired = CSS("#hired").match_one(self.root)
        return dict(
            mem_str=mem.text,
            # self.input is the data passed in from the prior scrape,
            # in this case a dict we can expand here
            **self.input,
        )


class Senate(CommitteeList):
    source = URL(
        "https://www.legis.la.gov/legis/Committees.aspx?c=S",
        timeout=30,
    )
    chamber = "upper"


# class House(CommitteeList):
#     source = URL(
#         "https://www.legis.la.gov/legis/Committees.aspx?c=H",
#         timeout=30)
#     chamber = "lower"

# class Misc(CommitteeList):
#     source = URL(
#         "https://www.legis.la.gov/legis/Committees.aspx?c=M",
#         timeout=30,
#     )
#     chamber = "legislature"
