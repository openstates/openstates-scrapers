from spatula import HtmlListPage, HtmlPage, CSS, XPath
from openstates.models import ScrapeCommittee


class HouseCommitteeDetail(HtmlPage):
    example_source = (
        "http://www.gencourt.state.nh.us/house/committees/committeedetails.aspx?id=12"
    )
    example_input = "Public Works and Highways"

    def process_page(self):
        com = self.input
        Rolez = XPath("//*[@id='form1']/div/div/div/div/div[1]/text()").match(self.root)
        Chair_mem = (
            CSS("#form1 div div div div div a")
            .match(self.root)[0]
            .text_content()
            .strip()
        )
        Chair_role = Rolez[0].replace(":", "").strip()
        com.add_member(Chair_mem, Chair_role)
        VChair_mem = (
            CSS("#form1 div div div div div a")
            .match(self.root)[1]
            .text_content()
            .strip()
        )
        VChair_role = Rolez[1].replace(":", "").strip()
        com.add_member(VChair_mem, VChair_role)

        members = CSS("#form1 div div.card-body div a").match(self.root)[7:]
        for mem in members:
            member = mem.text_content().strip()
            role_mem = "Member"
            com.add_member(member, role_mem)
        return com


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "http://www.gencourt.state.nh.us/Senate/committees/committee_details.aspx?cc=30"
    )
    example_input = "Capital Budget"

    def process_page(self):
        com = self.input
        Memberz = CSS("#form1 div div.card-body div a").match(self.root)
        rolez = CSS("#form1 div div div div div a").match(self.root)[0:2]
        Chair = Memberz[0].text
        Chair_name = Chair[9:].strip()
        Chair_rolez = rolez[0].text
        Chair_role = Chair_rolez[:9].strip()
        com.add_member(Chair_name, Chair_role)
        V_Chair = Memberz[1].text
        V_Chair_name = V_Chair[11:].strip()
        V_Chair_rolez = rolez[1].text
        V_Chair_role = V_Chair_rolez[:11].strip()
        com.add_member(V_Chair_name, V_Chair_role)
        Mem_mem = Memberz[3:]
        for mem in Mem_mem:
            Mem_name = mem.text
            role = "Member"
            com.add_member(Mem_name, role)
        return com


class SenateCommittee(HtmlListPage):
    source = "http://www.gencourt.state.nh.us/Senate/committees/senate_committees.aspx"
    chamber = "upper"
    selector = CSS("#form1 div h5")

    def process_item(self, item):
        com_link = CSS("a").match(item)[0]
        name = com_link.text_content()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = com_link.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        return SenateCommitteeDetail(com, source=detail_link)


class HouseCommittee(HtmlListPage):
    source = "http://www.gencourt.state.nh.us/house/committees/standingcommittees.aspx"
    chamber = "lower"
    selector = CSS("#form1 div h5")

    def process_item(self, item):
        com_link = CSS("a").match(item)[0]
        name = com_link.text_content()
        com = ScrapeCommittee(
            name=name, classification="committee", chamber=self.chamber
        )
        detail_link = com_link.get("href")
        com.add_source(detail_link)
        com.add_link(detail_link, "homepage")
        return HouseCommitteeDetail(com, source=detail_link)


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])
