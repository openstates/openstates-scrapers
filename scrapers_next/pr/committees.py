from spatula import HtmlPage, HtmlListPage, CSS, SelectorError, URL
from openstates.models import ScrapeCommittee
import re


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://senado.pr.gov/comisiones/comisión-de-asuntos-de-vida-y-familia"
    )

    def process_page(self):
        com = self.input
        com.add_source(self.source.url, note="Committee Detail Page")
        com.add_link(self.source.url, note="homepage")

        members = CSS("div.panel-body div.senator_cont a").match(self.root)

        for member in members:
            name = CSS("span.name").match_one(member).text_content()
            role = CSS("span.position").match_one(member).text_content()
            if not role:
                role = "member"

            com.add_member(re.sub("Hon. ", "", name), role)

        return com


class HouseCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.camara.pr.gov/ova_dep/comision-conjunta-pa"
        "ra-la-revision-y-reforma-del-codigo-civil-de-puerto-rico/"
    )

    def process_page(self):
        com = self.input
        com.add_source(self.source.url, note="Committee Detail Page")
        com.add_link(self.source.url, note="homepage")

        # Some House committees have different site formats
        try:
            members = CSS("div.mc-title-container").match(self.root)
        except SelectorError:
            members = []

        if members:
            for member in members:
                full_title = member.getchildren()
                name = full_title[0].text_content()
                role = full_title[1].text_content()
                if not role:
                    role = "member"

                com.add_member(name, role)
        else:
            members = CSS("div.elementor-widget-container ul li.p1").match(self.root)
            for member in members:
                role = "member"
                title = re.findall(
                    "Presidente|Secretari[ao]|Vice.*", member.text_content()
                )
                name = re.sub("Hon. |,.*", "", member.text_content())
                if title:
                    role = title[0]
                com.add_member(name, role)

        return com


class SenateCommitteeList(HtmlListPage):
    source = "https://senado.pr.gov/index.cfm?module=comisiones"
    selector = CSS("table.table.table-striped tbody tr td a")
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content()
        com = ScrapeCommittee(name=name, chamber=self.chamber)
        com.add_source(self.source.url, note="Committee List Page")
        return SenateCommitteeDetail(com, source=URL(item.get("href")))


class HouseCommitteeList(HtmlListPage):
    source = "https://www.camara.pr.gov/comisiones/"
    selector = CSS(
        "div.col-md-12.col-sm-12.col-xs-12.pt-cv-content-item.pt-cv-1-col div.pt-cv-ifield"
    )

    def process_item(self, item):
        chamber = "lower"

        title, item_type = item.getchildren()
        name = title.text_content()

        if item_type.text_content().strip() == "Conjuntas":
            chamber = "legislature"

        com = ScrapeCommittee(name=name, chamber=chamber)
        com.add_source(self.source.url, note="Committee List Page")
        return HouseCommitteeDetail(com, source=URL(title.getchildren()[0].get("href")))
