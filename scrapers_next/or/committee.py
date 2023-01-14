from spatula import XPath, URL, HtmlListPage, HtmlPage, CSS
from openstates.models import ScrapeCommittee
import re

class CommitteeDetail(HtmlListPage):
    source = URL("https://olis.oregonlegislature.gov/liz/2023R1/Committees/JCT/CommitteeMembers")
    selector = CSS('tbody tr')

    def process_item(self, item):
        com = self.input
        position, name = item.getchildren()
        name = re.sub(r"Senator |Representative ", "", name.text_content().strip())
        position = position.text_content().strip()
        com.add_member(name, position)

        return com


class CommitteeList(HtmlListPage):
    source = "https://olis.oregonlegislature.gov/liz/Committees/list/"

    def process_item(self, item):
        link = item.get("href").split('/')
        link = 'https://olis.oregonlegislature.gov/liz/' + link[4] +\
                "/Committees/" + link[6] + "/CommitteeMembers"

        try:
            parent = self.parent
        except:
            parent = None

        com = ScrapeCommittee(
                name=item.text_content(),
                chamber=self.chamber,
                classification=self.classification,
                parent=parent,
            )
        com.add_source(link)

        return CommitteeDetail(com, source=link,)


class HouseCommitteeList(CommitteeList):
    selector = CSS("#HouseCommittees_search li a")
    chamber = "lower"
    classification = "committee"

class SenateCommitteeList(CommitteeList):
    selector = CSS("#SenateCommittees_search li a")
    chamber = "upper"

class JointCommitteeList(CommitteeList):
    selector = CSS("#SenateCommittees_search > li > a")
    chamber = "legislature"

class WayMeansCommitteeList(CommitteeList):
    selector = CSS("#JointCommittees_search > li > ul > li > a")
    chamber = "legislature"
    parent = "Ways and Means"
    classification = "subcommittee"

