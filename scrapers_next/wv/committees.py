from re import sub
from spatula import HtmlPage, HtmlListPage, CSS, URL, Source, SkipItem
from openstates.models import ScrapeCommittee


class CommitteeMember(HtmlPage):
    position: str

    def __init__(self, input_val, source: Source, position: str):
        super(CommitteeMember, self).__init__(input_val, source=source)
        self.position = position

    def process_page(self):
        name = CSS("#wrapleftcolr > h2:nth-child(1)").match_one(self.root).text
        if name is not None:
            self.input.add_source(self.source.url, f"{name} url")
            self.input.add_member(sub(r"\(.*\)", "", name), self.position)
        return self.input

    def get_source_from_input(self):
        pass


class CommitteeDetail(HtmlListPage):
    selector: CSS
    url_signifier: str

    def __init__(
        self,
        input_val: ScrapeCommittee,
        source: Source,
        selector: CSS,
        url_signifier: str,
    ):
        super(CommitteeDetail, self).__init__(input_val, source=source)
        self.selector = selector
        self.url_signifier = url_signifier

    def process_item(self, item):
        if self.url_signifier in item.get("href"):
            next_elem = item.getnext().text
            position = next_elem if isinstance(next_elem, str) else "member"
            return CommitteeMember(
                self.input, source=URL(item.get("href")), position=position
            )
        else:
            raise SkipItem("not a committee member url")

    def get_source_from_input(self):
        pass


class CommitteeList(HtmlListPage):
    selector: CSS
    member_selector: CSS
    cmte_url_signifier: str
    member_url_signifier: str
    chamber: str

    def process_item(self, item):
        if self.cmte_url_signifier in item.get("href"):
            cmte = ScrapeCommittee(
                name=item.text,
                chamber=self.chamber,
                classification="subcommittee"
                if "subcommittee" in item.text.lower()
                else "committee",
            )
            cmte.add_source(item.get("href"), f"{item.text} committee url")
            return CommitteeDetail(
                input_val=cmte,
                source=URL(item.get("href")),
                selector=self.member_selector,
                url_signifier=self.member_url_signifier,
            )
        else:
            raise SkipItem("not a committee url")

    def get_source_from_input(self):
        pass


class SenateCommittees(CommitteeList):
    source = "https://www.wvlegislature.gov/committees/senate/main.cfm"
    selector = CSS("#wrapleftcolr a")
    member_selector = CSS("#wrapleftcol a")
    cmte_url_signifier = "SenateCommittee.cfm"
    member_url_signifier = "Senate1/lawmaker.cfm"
    chamber = "upper"


class HouseCommittees(CommitteeList):
    source = "https://www.wvlegislature.gov/committees/house/main.cfm"
    selector = CSS("#wrapleftcol a")
    member_selector = CSS("#wrapleftcol a")
    cmte_url_signifier = "HouseCommittee.cfm"
    member_url_signifier = "House/lawmaker.cfm"
    chamber = "lower"


# class JointCommittees(CommitteeList):
#     cmte_selector = CSS("wrapleftcol a")
#     source = "https://www.wvlegislature.gov/committees/interims/interims.cfm"
#     cmte_url_signifier = "interims/committee.cfm"
#     chamber = "legislature"
