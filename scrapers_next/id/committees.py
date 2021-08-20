from spatula import HtmlListPage, CSS, URL, HtmlPage
from openstates.models import ScrapeCommittee
import re


# "html body section.parent-section.no-padding div.container-fluid div.row section.parallax-fix div.container div.row div div div div.tab-content div div div div.insert-page.insert-page-522202 div.hidden-print section.row-equal-height.no-padding div"
# "html body section.parent-section.no-padding div.container-fluid div.row div"
# "https://legislature.idaho.gov/sessioninfo/2021/joint/cec/"
# this link might have broken html

# https://legislature.idaho.gov/lso/bpa/eora/
# https://legislature.idaho.gov/sessioninfo/2021/standingcommittees/HETH/
# these links have 'Ad Hoc' in names


class DetailCommitteePage(HtmlPage):
    def process_page(self):
        com = self.input

        members = CSS(
            "div .wpb_column.vc_column_container.col-xs-mobile-fullwidth.col-sm-6 div .row-equal-height.hcode-inner-row"
        ).match(self.root)
        for member in members:
            name = CSS("strong").match_one(member).text_content().strip()
            name = re.search(r"(Sen\.|Rep\.)\s(.+)", name).groups()[1]
            if re.search(r",\s", name):
                name, role = re.search(r"(.+),\s(.+)", name).groups()
            else:
                role = "member"
            print(name, role)

        return com


class JointCommitteeList(HtmlListPage):
    selector = CSS("div .vc-column-innner-wrapper ul li", num_items=5)

    def process_item(self, item):
        com_link = CSS("a").match_one(item)
        name = com_link.text_content()

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
        )

        detail_link = com_link.get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        if detail_link == "https://legislature.idaho.gov/sessioninfo/2021/joint/cec/":
            return com

        return DetailCommitteePage(com, source=detail_link)


class CommitteeList(HtmlListPage):
    selector = CSS("div .padding-one-top.hcode-inner-row")

    def process_item(self, item):
        name = CSS("strong").match(item)[0].text_content()

        # skip header row
        if name == "Committees":
            self.skip()

        com = ScrapeCommittee(
            name=name,
            chamber=self.chamber,
        )

        detail_link = CSS("a").match(item)[0].get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return DetailCommitteePage(com, source=detail_link)


class Senate(CommitteeList):
    source = URL("https://legislature.idaho.gov/committees/senatecommittees/")
    chamber = "upper"


class House(CommitteeList):
    source = URL("https://legislature.idaho.gov/committees/housecommittees/")
    chamber = "lower"


class Joint(JointCommitteeList):
    source = URL("https://legislature.idaho.gov/committees/jointcommittees/")
    chamber = "legislature"
