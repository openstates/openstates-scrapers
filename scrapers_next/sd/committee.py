from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, SkipItem, URL
from openstates.models import ScrapeCommittee


class CommitteeList(HtmlListPage):
    """
    As of review 1/14/2023, SD Leg committes page had a sidebar nav with all the committees listed.
      There's an anchor tag with classes of v-list-item, v-list-item--link, role="listitem" that contains a href
    to the committee detail path (not fully qualified)
      Then there's a div child of a div child with class v-list-item__title that contains a span element with the committee type
    (if it's one we want - there are also such structures that are the full house & senate that do not have the span elements)
    The div itself has the text name of the committee.
    """
    source = "https://sdlegislature.gov/Session/Committees/68"
    selector = CSS("a.v-list-item--link")

    def standardize_chamber(self, original_chamber_text):
        match original_chamber_text:
            case "House":
                return "lower"
            case "Senate":
                return "upper"
            case "Joint":
                return "legislature"
            case _:
                self.skip()


    def process_item(self, item):
        detail_path = item.get("href")
        title_div = (
            item.getchildren()[0]
            .getchildren()[0]
        )
        try:
            chamber = title_div.getchildren()[0].text_content()
        except:
            self.skip()

        committee_name = item.text_content()

        com = ScrapeCommittee(
            name=committee_name,
            chamber=self.standardize_chamber(chamber)
        )