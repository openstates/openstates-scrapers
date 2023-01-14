from spatula import JsonListPage, CSS, XPath, SelectorError, SkipItem, URL
from openstates.models import ScrapeCommittee


class CommitteeList(JsonListPage):

    source = URL("https://sdlegislature.gov/api/SessionCommittees/Committees/68")

    def standardize_chamber(self, original_chamber_text):
        match original_chamber_text:
            case "H":
                return "lower"
            case "S":
                return "upper"
            case "J":
                return "legislature"
            case _:
                self.skip()


    def process_item(self, item):
        committee_json = item["Committee"]
        print(committee_json)
        # try:
        #     title_div = (
        #         item.getchildren()[0]
        #         .getchildren()[0]
        #     )
        # except:
        #     self.skip()

        # try:
        #     chamber = title_div.getchildren()[0].text_content()
        # except:
        #     self.skip()

        # committee_name = item.text_content()

        com = ScrapeCommittee(
            name="test",
            chamber="upper"
        )

        return com