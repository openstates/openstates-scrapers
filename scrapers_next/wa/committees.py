from spatula import HtmlListPage, HtmlPage, CSS, URL, SelectorError, XPath, SkipItem
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        try:
            members = CSS("div#CommitteeMembers tbody tr").match(self.root)
        except SelectorError:
            self.logger.warning(f"skipping members for {self.source.url}")
            raise SkipItem("empty")
        for member in members:
            dirty_name = CSS("a").match_one(member).text_content().strip().split(", ")
            last_name = dirty_name[0]
            first_name = dirty_name[1]
            name = first_name + " " + last_name

            try:
                role = XPath("//td/text()[3]").match(member)[0].strip()
            except SelectorError:
                role = "member"

            com.add_member(name, role)

        return com


class CommitteeList(HtmlListPage):
    source = URL("https://app.leg.wa.gov/ContentParts/LegislativeCommittees/Index")
    selector = CSS("div ul li span a.ms-srch-item-link", min_items=50)

    def process_item(self, item):

        name = item.text_content().strip()

        chamber = (
            item.getparent()
            .getparent()
            .getparent()
            .getprevious()
            .text_content()
            .strip()
            .split()[0]
        )
        if chamber == "House":
            chamber = "lower"
        elif chamber == "Senate":
            chamber = "upper"
        elif chamber == "Joint":
            chamber = "legislature"
        elif chamber == "Legislative":
            self.skip()
            # skipping Legislative Agencies

        com = ScrapeCommittee(
            name=name,
            chamber=chamber,
        )

        com.add_source(self.source.url)

        # new source
        href = item.get("href")
        href_lst = href.split("/")
        new_source = f"https://app.leg.wa.gov/ContentParts/CommitteeMembers/?agency={href_lst[-3]}&committee={href_lst[-1]}"

        com.add_source(new_source)
        com.add_link(href, note="homepage")

        return CommitteeDetail(com, source=new_source)
