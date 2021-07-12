from spatula import HtmlListPage  # , CSS, XPath, URL
from openstates.models import ScrapePerson


class LegList(HtmlListPage):
    def process_item(self, item):
        return ScrapePerson()


class RepList(LegList):
    source = ""
    # selector = CSS("", num_items=)
    chamber = "lower"


class SenList(LegList):
    source = ""
    # selector = CSS("", num_items=)
    chamber = "upper"
