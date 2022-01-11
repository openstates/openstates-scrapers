from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, URL, SkipItem
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.nysenate.gov/committees/housing-construction-and-community-development"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        # a few committees don't have chair positions
        try:
            chair_role = (
                CSS(".c-chair-block--position")
                .match_one(self.root)
                .text_content()
                .lower()
            )
            chair_name = CSS(".c-chair--title").match_one(self.root).text_content()
            com.add_member(chair_name, chair_role)

        except SelectorError:
            pass
        try:
            for p in XPath(
                "//div[contains(@class, 'c-senators-container')]//div[@class='view-content']/div[contains(@class, 'odd') or contains(@class, 'even')]"
            ).match(self.root):
                name = CSS(".nys-senator--name").match_one(p).text_content()

                role = CSS(".nys-senator--position").match_one(p).text_content().lower()
                if role == "":
                    role = "member"

                com.add_member(name, role)
        except SelectorError:
            pass

        return com


class HouseCommitteeDetail(HtmlPage):
    example_source = "https://assembly.state.ny.us/comm/?id=1"

    def process_page(self):
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url, note="homepage")

        try:
            chairs = CSS(".chair-info").match(self.root)
        except SelectorError:
            raise SkipItem("skipping committee without full information")

        # in case there are co-chairs
        num_chairs = len(chairs)

        for chair in chairs:
            chair_name = CSS(".comm-chair-name").match_one(chair).text_content().strip()
            chair_role = (
                XPath(f"..//preceding-sibling::header[{num_chairs}]")
                .match_one(chair)
                .text_content()
                .strip()
                .lower()
            )
            com.add_member(chair_name, chair_role)

        # some committees only have chairs and no members list
        try:
            for p in CSS("#comm-membership ul li").match(self.root):
                name = p.text_content().strip()
                role = "member"
                com.add_member(name, role)
        except SelectorError:
            pass

        # some committees have temporary addresses, others have permanent ones
        try:
            temp, room, zip = XPath(
                "//section[@id='comm-addr']/div[@class='mod-inner']//text()"
            ).match(self.root)
            com.extras["address"] = f"{temp}: {room}; {zip}"
        except ValueError:
            room, zip = XPath(
                "//section[@id='comm-addr']/div[@class='mod-inner']//text()"
            ).match(self.root)
            com.extras["address"] = f"{room}; {zip}"

        # some committees have press releases
        try:
            news_link = CSS("#page-content .read-more").match(self.root)[0].get("href")
            com.add_link(news_link)
        except SelectorError:
            pass

        return com


class SenateCommitteeList(HtmlListPage):
    source = "https://www.nysenate.gov/senators-committees"
    selector = CSS("#c-committees-container table tr td a")
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content().strip()
        com = ScrapeCommittee(name=name, chamber=self.chamber)
        com.add_source(self.source.url)
        return SenateCommitteeDetail(com, source=URL(item.get("href"), timeout=30))


class HouseCommitteeList(HtmlListPage):
    source = "https://assembly.state.ny.us/comm/"
    selector = CSS(".comm-row .comm-item .comm-title a")
    chamber = "lower"

    def process_item(self, item):
        name = item.text_content()
        com = ScrapeCommittee(name=name, chamber=self.chamber)
        com.add_source(self.source.url)
        return HouseCommitteeDetail(com, source=URL(item.get("href"), timeout=30))
