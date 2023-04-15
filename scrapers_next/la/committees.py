import re

import requests
from lxml.html import Element, fromstring
from openstates.models import ScrapeCommittee
from spatula import URL, HtmlListPage, HtmlPage, SkipItem, XPath

from utils import (_identify_member_role, _manually_fix_broken_links,
                   remove_title_reorder_name, select_chamber)


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

        members = self.root.xpath("//div[@class='card-R22']/a[@class='memlink22']")
        for member in members:
            name, role, *_ = member.xpath(".//span/text()")
            clean_name = remove_title_reorder_name(name)
            if not clean_name.strip():
                continue
            role = _identify_member_role(role)
            com.add_member(clean_name, role)

        com.add_source(self.source.url, note="Committee Detail Page")
        com.add_link(self.source.url, note="homepage")

        if not com.members:
            raise SkipItem("empty committee")

        return com


class MiscellaneousCommitteeList(HtmlListPage):

    def process_page(self):
        """Process page - find and scrape committees

        This was setup to handle the regular misc committees and the
        subcommittees of the joint budget committee

        :return: committee data
        """
        for link in self.root.xpath(
            "//div[@id='ctl00_ctl00_PageBody_PageContent_PanelMiscellaneous']//a"
        ):
            link = _manually_fix_broken_links(link)
            self.classification = "committee"
            self.parent = None
            yield self.process_item(link)

        # Manually download and identify subcommittees
        response = requests.get("https://jlcb.legis.la.gov", timeout=30)
        subcommittees = fromstring(response.content).xpath(
            '//li/a[contains(text(),"Sub Committees")]/../ul/li/a'
        )

        # Process budget subcommittees
        for link in subcommittees:
            link.set("href", f"https://jlcb.legis.la.gov{link.get('href')}")
            self.parent = "Joint Legislative Committee on the Budget"
            self.classification = "subcommittee"
            yield self.process_item(link)

    def process_item(self, item: Element) -> HtmlPage:
        """Process committee data

        :param item: Page to process
        :return: Committee Detail data
        """
        comm_name, comm_url = item.text_content(), item.get("href")
        self.chamber = select_chamber(comm_url, comm_name)

        com = ScrapeCommittee(
            name=comm_name.strip(),
            chamber=self.chamber,
            classification=self.classification,
            parent=self.parent,
        )
        com.add_source(self.source.url, note="Committees List Page")
        return MiscellaneousCommitteeDetail(com, source=URL(comm_url, timeout=30))


class MiscellaneousCommitteeDetail(HtmlPage):
    def process_page(self) -> CommitteeDetail:
        """Process miscellaneous committee pages

        Because of the various types of pages exhibited in Louisiana
        The simplest method across them all was to identify language found
        inside tables and then to reverse engineer the table data and extract
        In once case the page did not contain tables

        return: committee details
        """
        com = self.input

        tables = self.root.xpath(
            "//table[.//*["
            'contains(text(),"Chairman") or '
            'contains(text(),"Vice") or '
            'contains(text(),"Ex-O") or '
            'contains(text(),"Senator")'
            "]][1]"
        )
        divs = self.root.xpath(
            "//div[.//*["
            'contains(text(),"Chairman") or '
            'contains(text(),"Vice")'
            ']][1]'
        )

        if tables:
            if com.name in [
                "Joint Legislative Committee on the Budget",
                "Litigation Sub",
            ]:
                tables = [tables[1], tables[3]]
            else:
                tables = [tables[-1]]

            for table in tables:
                rows = table.xpath(".//tr")
                for row in rows:
                    c = row.xpath(".//td/text()")
                    if not c:
                        continue
                    opt = row.xpath(".//td")
                    name, _ = opt[0].text_content(), opt[-1].text_content()
                    clean_name = remove_title_reorder_name(name)
                    if not clean_name.strip():
                        continue
                    role = _identify_member_role(
                        " ".join([x.text_content() for x in opt])
                    )
                    com.add_member(clean_name, role)
        elif divs:
            if divs:
                rows = divs[-1].xpath(".//span")
                members = set()
                for row in rows:
                    members.update(row.text_content().split("\n"))
                for member in members:
                    row_text = re.sub(r"\s+", " ", member.strip()).strip()
                    clean_name = remove_title_reorder_name(row_text)
                    if not clean_name:
                        continue
                    role = _identify_member_role(row_text)
                    com.add_member(clean_name, role)
        else:
            rows = self.root.xpath('.//div[@id="links"]/text()')
            for row in rows:
                row_text = re.sub("\s+", " ", row).strip()
                if not row_text:
                    continue
                clean_name = remove_title_reorder_name(row_text)
                com.add_member(clean_name, "member")

        com.add_source(self.source.url, note="Committee Detail Page")
        com.add_link(self.source.url, note="homepage")

        if not com.members:
            raise SkipItem("Empty committee")
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


class Miscellaneous(MiscellaneousCommitteeList):
    source = URL(
        "https://www.legis.la.gov/legis/Committees.aspx?c=M",
        timeout=30,
    )
