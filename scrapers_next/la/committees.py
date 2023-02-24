from spatula import HtmlPage, HtmlListPage, XPath, CSS, URL, SkipItem
from openstates.models import ScrapeCommittee


def extract_info(name_list):
    """
    Helper function called in `CommitteeDetail()` class,
    extracts full name and role of each member.
    """
    last_name, *first_name = name_list[0].split(", ")
    first_name = ", ".join(first_name)
    role = name_list[1].split("|")[0]

    return last_name, first_name, role


class CommitteeList(HtmlListPage):
    selector = XPath(
        "//div[@id='ctl00_ctl00_PageBody_PageContent_PanelHouseOrSenate']//a"
    )
    classification = "committee"
    parent = None

    def process_item(self, item):
        # get content of each link item - committee name
        comm_name = item.text_content()
        comm_url = item.get("href")

        if "Joint" in comm_name or "Legislative" in comm_name:
            self.chamber = "legislature"

        #TODO - skip if empty committee

        com = ScrapeCommittee(
            name=comm_name.strip(),
            chamber=self.chamber,
            classification=self.classification,
            parent=self.parent,
        )
        com.add_source(self.source.url, note="Committees List Page")

        return CommitteeDetail(com, source=URL(comm_url, timeout=30))


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        officers = self.root.xpath("//div[@class='card-R22']/a[@class='memlink22']")
        for officer in officers:
            name_and_title = [
                x.strip()
                for x in officer.text_content().split("\r\n")
                if len(x.strip())
            ]
            last_name, first_name, role = extract_info(name_and_title)
            com.add_member(first_name + " " + last_name, role)

        com.add_source(self.source.url, note="Committee Detail Page")
        com.add_link(self.source.url, note="homepage")

        return com

class Senate(CommitteeList):
    source = URL(
        "https://www.legis.la.gov/legis/Committees.aspx?c=S",
        timeout=30,
    )
    chamber = "upper"


class House(CommitteeList):
    source = URL("https://www.legis.la.gov/legis/Committees.aspx?c=H", timeout=30)
    chamber = "lower"


#TODO - complete Miscellaneous class 
# class Miscellaneous(CommitteeList):
#     source = URL(
#         "https://www.legis.la.gov/legis/Committees.aspx?c=M",
#         timeout=30,
#     )
#     selector = XPath("//div[@id='ctl00_ctl00_PageBody_PageContent_PanelMiscellaneous']//a")
#     chamber = "legislature"
