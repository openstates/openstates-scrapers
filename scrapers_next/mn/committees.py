import re
from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = (
        "https://www.senate.mn/committees/committee_bio.html?cmte_id=3087&ls=92"
    )

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        room, time = XPath("//div[@class='col-sm-12 pb-2']//p[2]/text()").match(
            self.root
        )
        if re.search("On Call", time):
            time = time.split(" -")[0]
        com.extras["room"] = room.strip()
        com.extras["meeting schedule"] = time.strip()

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
    example_source = "https://www.house.leg.state.mn.us/Committees/members/92006"

    def process_page(self):

        com = self.input
        com.add_source(self.source.url)

        time, room = (
            CSS(".border-0 .pl-2").match(self.root)[0].text_content().split("in ")
        )
        time = time.split("Meets:")[1]

        com.extras["room"] = room.strip()
        com.extras["meeting schedule"] = time.strip()

        for p in XPath('//div[@class="media pl-2 py-4"]').match(self.root):

            name = (
                XPath(".//div[@class='media-body']/span/b/text()")
                .match(p)[0]
                .replace("Rep.", "")
                .split("(R)")[0]
                .split("(DFL")[0]
                .strip()
            )

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


class SenateCommitteeList(HtmlListPage):
    selector = CSS(" .card .list-group-flush .d-flex a")
    source = "https://www.senate.mn/committees"
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content().strip()
        if re.search(" - ", name):
            parent, com_name = name.split(" - Subcommittee on ")
            com = ScrapeCommittee(
                name=com_name, classification="subcommittee", parent=parent
            )
        else:
            com = ScrapeCommittee(name=name, parent=self.chamber)

        com.add_source(self.source.url)
        return SenateCommitteeDetail(com, source=item.get("href"))


class HouseCommitteeList(HtmlListPage):
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

        for links in XPath(".//div[contains(@class, 'container')]//a").match(item):
            url = links.get("href")
            if url == link:
                continue
            else:
                if links == XPath(
                    ".//div[contains(@class, 'container')]//a[contains(@href, 'home')]"
                ).match_one(item):
                    com.add_link(url, note="homepage")
                    homepage = True
                else:
                    com.add_link(url)
        if not homepage:
            self.warn("no homepage found")

        com.add_source(self.source.url)
        return HouseCommitteeDetail(com, source=link)
