from spatula import HtmlListPage, CSS, URL, HtmlPage, SkipItem
from openstates.models import ScrapeCommittee
import re


class DetailCommitteePage(HtmlPage):
    def process_page(self):
        com = self.input

        members = CSS(
            "div .wpb_column.vc_column_container.col-xs-mobile-fullwidth.col-sm-6 div .row-equal-height.hcode-inner-row"
        ).match(self.root)

        if not members:
            raise SkipItem("empty committee")

        for member in members:
            name = CSS("strong").match_one(member).text_content().strip()
            name = re.search(r"(Sen\.|Rep\.)\s(.+)", name).groups()[1]

            if re.search(r"Ad\sHoc", name):
                name, _, role = re.search(r"(.+)(\s–\s|\()(Ad\sHoc)\)?", name).groups()

            if re.search(r",\s", name):
                name, role = re.search(r"(.+),\s(.+)", name).groups()

            com.add_member(name, role if role else "member")

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

        # this link has broken html (not able to grab member info)
        # just returning name, chamber, and link
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

        all_text = CSS("p").match(item)[0].text_content().strip()
        secretary, email, phone = re.search(
            r"\n?Secretary:(.+)\n?Email:(.+)\n?Phone:(.+)", all_text
        ).groups()
        com.extras["secretary"] = secretary.strip()
        com.extras["email"] = email.strip()
        com.extras["phone"] = phone.strip()

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
