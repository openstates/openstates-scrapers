from spatula import HtmlListPage, HtmlPage, CSS, URL, SelectorError
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        members = CSS("div#CommitteeMembers tbody tr").match(self.root)
        # members = CSS("td a.ui-link").match(self.root)
        for member in members:
            dirty_name = CSS("a").match_one(member).text_content().strip().split(", ")
            # dirty_name = member.get("a").text_content().strip().split(", ")
            # dirty_name = member.text_content().strip().split(", ")
            last_name = dirty_name[0]
            first_name = dirty_name[1]
            name = first_name + " " + last_name

            try:
                role = CSS("td").match(member)[0].get("text()")[-1].strip()
                # role = member.get("td").get("text()")[-1].strip()
            except SelectorError:
                role = "member"
            # role = member.getnext().getnext().getnext()
            # .getnext().getnext().getnext()
            # .tail()

            com.add_member(name, role)

        return com


class CommitteeList(HtmlListPage):
    source = URL("https://app.leg.wa.gov/ContentParts/LegislativeCommittees/Index")
    selector = CSS("div ul li span a.ms-srch-item-link", num_items=57)

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
            chamber = "legislative"
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
        print(href)
        href_lst = href.split("/")
        print(href_lst)
        new_source = f"https://app.leg.wa.gov/ContentParts/CommitteeMembers/?agency={href_lst[-3]}&committee={href_lst[-1]}"

        com.add_source(new_source)
        com.add_link(href, note="homepage")

        return CommitteeDetail(com, source=new_source)
