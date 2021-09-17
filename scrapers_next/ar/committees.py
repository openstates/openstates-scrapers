from spatula import URL, CSS, HtmlListPage, HtmlPage, XPath, SelectorError
from openstates.models import ScrapeCommittee
import re


class CommDetail(HtmlPage):
    def process_page(self):
        com = self.input

        try:
            chair = (
                XPath("//h5[text()='Chair']")
                .match_one(self.root)
                .getnext()
                .text_content()
                .strip()
            )
            chair = re.search(r"(Senator|Representative)\s(.+)", chair).groups()[1]
            com.add_member(chair, "Chair")
        except SelectorError:
            pass

        try:
            vice_chair = (
                XPath("//h5[text()='Vice-Chair']")
                .match_one(self.root)
                .getnext()
                .text_content()
                .strip()
            )
            vice_chair = re.search(
                r"(Senator|Representative)\s(.+)", vice_chair
            ).groups()[1]
            com.add_member(vice_chair, "Vice-Chair")
        except SelectorError:
            pass

        try:
            additional_members = (
                XPath("//h5[text()='Additional Members']")
                .match_one(self.root)
                .getnext()
                .getchildren()
            )
            for member in additional_members:
                member = member.text_content().strip()
                member = re.search(r"(Senator|Representative)\s(.+)", member).groups()[
                    1
                ]
                com.add_member(member, "member")
        except SelectorError:
            pass

        return com


class SenSubComms(HtmlListPage):
    source = URL("https://senate.arkansas.gov/senators/committees/")
    selector = CSS("ins > ul > li > ul > li", num_items=87)

    def process_item(self, item):
        sub_name = CSS("a").match_one(item).text_content().strip()

        previous_sibs = (
            item.getparent().getparent().getparent().itersiblings(preceding=True)
        )
        for sib in previous_sibs:
            if len(sib.getchildren()) == 0:
                chamber_type = sib.text_content().strip()
                break

        if chamber_type == "Senate Committees":
            chamber = "upper"
        elif chamber_type == "Joint Committees":
            self.skip()
        elif chamber_type == "Task Forces":
            self.skip()

        comm_name = (
            CSS("a").match(item.getparent().getparent())[0].text_content().strip()
        )

        com = ScrapeCommittee(
            name=sub_name,
            classification="subcommittee",
            chamber=chamber,
            parent=comm_name,
        )

        detail_link = CSS("a").match_one(item).get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return CommDetail(com, source=detail_link)


class SenList(HtmlListPage):
    source = URL("https://senate.arkansas.gov/senators/committees/")
    selector = CSS("ins > ul > li", num_items=45)

    def process_item(self, item):
        comm_name = CSS("a").match(item)[0].text_content().strip()

        previous_sibs = item.getparent().itersiblings(preceding=True)
        for sib in previous_sibs:
            if len(sib.getchildren()) == 0:
                chamber_type = sib.text_content().strip()
                break

        if chamber_type == "Senate Committees":
            chamber = "upper"
        elif chamber_type == "Joint Committees":
            self.skip()
        elif chamber_type == "Task Forces":
            self.skip()

        com = ScrapeCommittee(
            name=comm_name,
            classification="committee",
            chamber=chamber,
        )

        detail_link = CSS("a").match(item)[0].get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return CommDetail(com, source=detail_link)


class HouseSubComms(HtmlListPage):
    source = URL("https://www.arkleg.state.ar.us/Committees/List?type=House")
    selector = CSS("div#bodyContent li a", num_items=30)

    def process_item(self, item):
        sub_name = item.text_content().strip()

        parent = (
            item.getparent()
            .getparent()
            .getparent()
            .getparent()
            .getchildren()[0]
            .text_content()
            .strip()
        )

        com = ScrapeCommittee(
            name=sub_name.title(),
            classification="subcommittee",
            chamber="lower",
            parent=parent.title(),
        )

        detail_link = item.get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return com


class HouseList(HtmlListPage):
    source = URL("https://www.arkleg.state.ar.us/Committees/List?type=House")
    selector = CSS("div#bodyContent div.row p a", num_items=16)

    def process_item(self, item):
        comm_name = item.text_content().strip()

        com = ScrapeCommittee(
            name=comm_name.title(),
            classification="committee",
            chamber="lower",
        )

        detail_link = item.get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return com


class JointSubComms(HtmlListPage):
    source = URL("https://www.arkleg.state.ar.us/Committees/List?type=Joint")
    selector = CSS("div#bodyContent li a", num_items=31)

    def process_item(self, item):
        sub_name = item.text_content().strip()

        parent = (
            item.getparent()
            .getparent()
            .getparent()
            .getparent()
            .getchildren()[0]
            .text_content()
            .strip()
        )

        com = ScrapeCommittee(
            name=sub_name.title(),
            classification="subcommittee",
            chamber="legislature",
            parent=parent.title(),
        )

        detail_link = item.get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return com


class Joint(HtmlListPage):
    source = URL("https://www.arkleg.state.ar.us/Committees/List?type=Joint")
    selector = CSS("div#bodyContent div.row p a", num_items=19)

    def process_item(self, item):
        comm_name = item.text_content().strip()

        com = ScrapeCommittee(
            name=comm_name.title(),
            classification="committee",
            chamber="legislature",
        )

        detail_link = item.get("href")

        com.add_source(self.source.url)
        com.add_source(detail_link)
        com.add_link(detail_link, note="homepage")

        return com
