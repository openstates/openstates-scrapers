from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.nysenate.gov/committees/housing-construction-and-community-development"
    # example_source = ("https://www.nysenate.gov/committees/administrative-regulations-review-commission-arrc")

    def process_page(self):
        # *scrape
        com = self.input
        com.add_source(self.source.url)

        chair_role = (
            CSS(".c-chair-block--position").match_one(self.root).text_content().lower()
        )
        chair_name = CSS(".c-chair--title").match_one(self.root).text_content()
        # print(chair_name, chair_role)

        # *
        com.add_member(chair_name, chair_role)

        # print(XPath("//div[contains(@class, 'c-senators-container')]").match(self.root))
        try:
            for p in XPath(
                "//div[contains(@class, 'c-senators-container')]//div[@class='view-content']/div[contains(@class, 'odd') or contains(@class, 'even')]"
            ).match(self.root):
                name = CSS(".nys-senator--name").match_one(p).text_content()

                role = CSS(".nys-senator--position").match_one(p).text_content().lower()
                if role == "":
                    role = "member"
                    # print('hello')

                com.add_member(name, role)
                # print(name, role)
        except SelectorError:
            pass

        return com


class HouseCommitteeDetail(HtmlPage):
    example_source = "https://assembly.state.ny.us/comm/?id=1"
    # example_source = "https://assembly.state.ny.us/comm/?id=94"
    # example_source = "https://assembly.state.ny.us/comm/?id=149"

    # check out "intergenerational care"--is a subcommittee...smh but it's not listed on the list page
    def process_page(self):
        # *scrape
        # com = self.input
        # com.add_source(self.source.url)

        # chair_role = CSS("#comm-chair h2").match_one(self.root).text_content().lower()
        # chair_name = CSS(".comm-chair-name").match_one(self.root).text_content().strip()
        # print(chair_name, chair_role)

        # com.add_member(chair_name, chair_role)

        # in case there are multiple chairs:
        chairs = CSS(".chair-info").match(self.root)

        # in case there are co-chairs
        num_chairs = len(chairs)
        # print("num chairs: ", num_chairs)

        for chair in chairs:
            # chair_role = CSS("h2").match_one(chair).text_content().lower()
            # chair_role is preceding sibling header
            chair_name = CSS(".comm-chair-name").match_one(chair).text_content().strip()
            # problem: there are multiple chairs sometimes, the bottom returns multiple chair positions instead of just one
            chair_role = (
                XPath(f"..//preceding-sibling::header[{num_chairs}]")
                .match_one(chair)
                .text_content()
                .strip()
                .lower()
            )

            print(chair_name, chair_role)
            # com.add_member(chair_name, chair_role)
        for p in CSS("#comm-membership ul li").match(self.root):
            name = p.text_content().strip()
            # hard-code "member"?
            role = "member"

            print(name, role)

        # extra info
        address = CSS("#comm-addr .mod-inner").match_one(self.root).text_content()
        print("address", address)


class SenateCommitteeList(HtmlListPage):
    source = "https://www.nysenate.gov/senators-committees"
    selector = CSS("#c-committees-container table tr td a")
    chamber = "upper"

    def process_item(self, item):
        name = item.text_content().strip()
        # print(item.get("href"))
        # print(name)
        com = ScrapeCommittee(name=name, parent=self.chamber)
        com.add_source(self.source.url)
        return SenateCommitteeDetail(com, source=item.get("href"))


# add address for indiv committees
class HouseCommitteeList(HtmlListPage):
    source = "https://assembly.state.ny.us/comm/"
    selector = CSS(".comm-row .comm-item .comm-title a")
    chamber = "lower"

    def process_item(self, item):
        name = item.text_content()
        # print(name)
        com = ScrapeCommittee(name=name, parent=self.chamber)
        com.add_source(self.source.url)
        return HouseCommitteeDetail(com, source=item.get("href"))
