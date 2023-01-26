from re import sub, search
from spatula import HtmlPage, HtmlListPage, CSS, URL, Source, SkipItem
from openstates.models import ScrapeCommittee


class CommitteeMember(HtmlPage):
    """
    Scrape a committee member profile, if existing.

    Position is scraped from the directory page and passed directly to this class.

    If a member does not have a profile or their name cannot be gleaned using a
    css selector, use fallback_name.

    :param position: Rank of the member in the committee currently being scraped.
    e.g. "Chair"
    :param fallback_name: The name to use if the legislator's full name cannot be
    determined from their profile. e.g. "Senator Burns"
    """

    position: str
    fallback_name: str

    def __init__(self, input_val, source: Source, position: str, fallback_name: str):
        super(CommitteeMember, self).__init__(input_val, source=source)
        self.position = position
        self.fallback_name = fallback_name

    def process_page(self):
        # min_items set to zero because not all members have a profile
        # page instead shows a list of media releases
        name_match = CSS("#wrapleftcolr > h2:nth-child(1)", min_items=0).match(
            self.root
        )
        name = name_match[0].text if len(name_match) == 1 else self.fallback_name
        self.input.add_source(self.source.url, f"{name} url")
        self.input.add_member(sub(r"\(.*\)", "", name), self.position)
        return self.input


class CommitteeDetail(HtmlListPage):
    """
    Scrape a list of committee members.

    :param selector: CSS matcher for each legislator url, according to chamber.
    :param url_signifier: Part of each matched element's href that should exist
    in a valid member profile url.
    """

    selector: CSS
    url_signifier: str
    chamber: str

    def __init__(
        self,
        input_val: ScrapeCommittee,
        source: Source,
        selector: CSS,
        chamber: str,
        url_signifier: str,
    ):
        super(CommitteeDetail, self).__init__(input_val, source=source)
        self.selector = selector
        self.url_signifier = url_signifier
        self.chamber = chamber

    def process_item(self, item):
        if self.url_signifier in item.get("href"):
            fallback_name = item.get("href").split("member=", 1)[1]
            if self.chamber == "legislature":
                match = search(
                    rf"({fallback_name})\s+-\s+(.+)", item.getparent().text_content()
                )
                position = (
                    match.groups()[1]
                    if match is not None and len(match.groups()) == 2
                    else "Member"
                )
            else:
                next_elem = item.getnext().text
                position = next_elem if isinstance(next_elem, str) else "Member"
            return CommitteeMember(
                self.input,
                source=URL(item.get("href")),
                position=position,
                fallback_name=fallback_name,
            )
        else:
            raise SkipItem("not a committee member url")


class CommitteeList(HtmlListPage):
    """
    Scrape a list of committees.

    :param selector: CSS matcher for each committee url, according to chamber.
    :param member_selector: CSS matcher for each member within a committee -
    passed directly to CommitteeDetail.
    :param cmte_url_signifier: Part of each matched element's href that should exist
    in a valid committee directory url.
    :param member_url_signifier: Part of each matched element's href that should exist
    in a valid member profile url.
    :param chamber: Chamber of this group of committees. e.g. "upper" "lower" "legislature"
    """

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
                # WV subcommittees do not explicitly list parent committees
                classification="committee",
            )
            cmte.add_source(item.get("href"), f"{item.text} committee url")
            return CommitteeDetail(
                input_val=cmte,
                source=URL(item.get("href")),
                selector=self.member_selector,
                chamber=self.chamber,
                url_signifier=self.member_url_signifier,
            )
        else:
            raise SkipItem("not a committee url")


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


class JointCommittees(CommitteeList):
    source = "https://www.wvlegislature.gov/committees/interims/interims.cfm"
    selector = CSS("#wrapleftcol a")
    # min_items set to zero because not all joint committees have appointed members
    member_selector = CSS(".tabborder a", min_items=0)
    cmte_url_signifier = "committee.cfm"
    member_url_signifier = "lawmaker.cfm"
    chamber = "legislature"
