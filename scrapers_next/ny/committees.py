from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeDetail(HtmlPage):
    example_source = "https://www.nysenate.gov/committees/housing-construction-and-community-development"
    # example_source = ("https://www.nysenate.gov/committees/administrative-regulations-review-commission-arrc")

    def process_page(self):
        # *scrape
        # com = self.input
        # com.add_source(self.source.url)

        chair_role = (
            CSS(".c-chair-block--position").match_one(self.root).text_content().lower()
        )
        chair_name = CSS(".c-chair--title").match_one(self.root).text_content()
        print(chair_name, chair_role)

        # *
        # com.add_member(chair_name, chair_role)

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

                # com.add_member(name, role)
                print(name, role)
        except SelectorError:
            pass

        # return com


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
