from spatula import HtmlListPage, CSS


class CommitteeMembers(HtmlListPage):
    # selector = CSS('ul .list-unstyled')[0]

    def process_page(self, item):
        return None


class CommitteeScraper(HtmlListPage):
    selector = CSS("ul .list-unstyled")[0]

    def process_page(self, item):
        return None


class HouseCommitteeScraper(CommitteeScraper):
    source = "https://www.legis.ga.gov/committees/house"
    chamber = "lower"


class SenateCommitteeScraper(CommitteeScraper):
    source = "https://www.legis.ga.gov/committees/senate"
    chamber = "upper"
