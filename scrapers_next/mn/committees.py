import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.people.models.committees import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.senate.mn/committees/committee_bio.html?cmte_id=3087&ls=92"
    )

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)

        for link in XPath(
            '//div[contains(@class, "media-body")]//a[contains(@href, "member_bio")]'
        ).match(self.root):
            name = link.text_content().split(",")[0]
            if name:
                try:
                    positions = ("chair", "vice chair", "ranking minority member")
                    position = XPath("..//preceding-sibling::b/text()").match(link)
                    for role in position:
                        position_str = ""
                        position_str += role.lower()
                        if position_str not in positions:
                            raise ValueError("unknown position")
                except SelectorError:
                    position_str = "member"
            com.add_member(name, position_str)

        return com


class HouseCommitteeDetail(HtmlPage):
    example_source = "https://www.house.leg.state.mn.us/Committees/members/92002"

    def process_page(self):

        com = self.input
        com.add_source(self.source.url)

        for p in XPath('//div[@class="media pl-2 py-4"]').match(self.root):

            name = (
                XPath(".//div[@class='media-body']/span/b/text()")
                .match(p)[0]
                .split("(")[0]
                .replace("Rep.", "")
            )
            # com.add_link(CSS("a").match(p)[0].get("href"))

            # todo: should these be capitalized?
            positions = ["committee chair", "vice chair", "republican lead"]
            if name:
                try:
                    position = CSS("span b u").match(p)[0].text_content().lower()
                    if position in positions:
                        role = position
                except SelectorError:
                    role = "member"
            com.add_member(name, role)
        return com


# from NC: HouseCommitteeList(CommitteeList)
# todo: add meeting times for each committee
class SenateCommitteeList(HtmlListPage):
    selector = CSS(" .card .list-group-flush .d-flex a")
    source = "https://www.senate.mn/committees"
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content().strip()
        # print(re.search('-', name))
        if re.search(" - ", name):
            parent, com_name = name.split(" - Subcommittee on ")
            # print("name is this: ", name)
            com = ScrapeCommittee(
                name=com_name, classification="subcommittee", parent=parent
            )
        else:
            com = ScrapeCommittee(name=name, parent=self.chamber)

        com.add_source(self.source.url)
        return SenateCommitteeDetail(com, source=item.get("href"))


# todo: add meeting times, office building(?)
class HouseCommitteeList(HtmlListPage):
    # selector = CSS(".mb-3 .card-body h2 a")
    selector = CSS(".mb-3 .card-body")
    source = "https://www.house.leg.state.mn.us/committees"
    chamber = "lower"

    def process_item(self, item):
        link = (
            XPath(
                ".//div[contains(@class, 'container')]//a[contains(@href, 'members')]"
            )
            .match(item)[0]
            .get("href")
        )
        name = CSS("h2 a").match(item)[0].text_content()
        com = ScrapeCommittee(name=name, parent=self.chamber)
        return HouseCommitteeDetail(com, source=link)
