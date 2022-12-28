from spatula import HtmlListPage, HtmlPage, CSS, XPath, URL, SelectorError, SkipItem
from openstates.models import ScrapeCommittee


class HouseCommitteeDetail(HtmlPage):
    example_source = (
        "http://www.gencourt.state.nh.us/house/committees/committeedetails.aspx?id=12"
    )
    example_input = "Public Works and Highways"

    def process_page(self):
        try:
            com = self.input
            roles = XPath("//*[@id='form1']/div/div/div/div/div[1]/text()").match(
                self.root
            )
            chair_mem = (
                CSS("#form1 div div div div div a")
                .match(self.root)[0]
                .text_content()
                .strip()
            )
            chair_role = roles[0].replace(":", "").strip()
            # Some committees do not have a member assigned to Chair, so we do not add them
            if "n/a" not in chair_role:
                com.add_member(chair_mem, chair_role)

            VChair_mem = (
                CSS("#form1 div div div div div a")
                .match(self.root)[1]
                .text_content()
                .strip()
            )
            VChair_role = roles[1].replace(":", "").strip()
            # Some committees do not have a member assigned to Vice Chair, so we do not add them
            if "n/a" not in VChair_role:
                com.add_member(VChair_mem, VChair_role)

        # there is an issue with certain committees redirecting back to the general list of standing committees
        # instead of its appropriate committee page
        except SelectorError:
            raise SkipItem("does not redirect to appropriate committee page")

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
        members = CSS("#form1 div div.card-body div a").match(self.root)
        roles = CSS("#form1 div div div div div a").match(self.root)[0:2]
        chair = members[0].text
        chair_name = chair[9:].strip()
        chair_roles = roles[0].text
        chair_role = chair_roles[:9].strip()
        com.add_member(chair_name, chair_role)
        v_chair = members[1].text
        v_chair_name = v_chair[11:].strip()
        v_chair_roles = roles[1].text
        v_chair_role = v_chair_roles[:11].strip()
        com.add_member(v_chair_name, v_chair_role)
        this_member = members[3:]
        for mem in this_member:
            mem_name = mem.text
            role = "Member"
            com.add_member(mem_name, role)
        return com


class SenateCommittee(HtmlListPage):
    source = URL(
        "http://www.gencourt.state.nh.us/Senate/committees/senate_committees.aspx",
        timeout=30,
    )
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
        return SenateCommitteeDetail(com, source=URL(detail_link, timeout=30))


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
        return HouseCommitteeDetail(com, source=URL(detail_link, timeout=30))


if __name__ == "__main__":
    from spatula.cli import scrape

    scrape(["committee"])
