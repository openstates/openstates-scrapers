import re
from spatula import HtmlPage, HtmlListPage, CSS, URL, SkipItem
from openstates.models import ScrapeCommittee
import requests
import lxml.html


class UnknownSubCommFound(BaseException):
    def __init__(self, chamber_indicator):
        super().__init__(f"No protocol for subcommittee in {chamber_indicator} chamber")


def get_member_full_name(url, fallback_name):
    response = requests.get(url)
    content = lxml.html.fromstring(response.content)
    name_match = CSS("#wrapleftcolr > h2:nth-child(1)", min_items=0).match(content)
    fallback_name = " ".join(fallback_name.split()[1:])
    name = name_match[0].text if len(name_match) == 1 else fallback_name
    if "(" in name:
        name = name.split("(")[0].strip()
    return name


class CommitteeDetail(HtmlPage):
    def process_page(self):
        comm, member_dict, selector, url_signifier = self.input

        comm.add_source(self.source.url, note="Committee detail page")
        comm.add_link(self.source.url, note="homepage")

        details = selector.match(self.root)
        for detail_item in details:
            item_href = detail_item.get("href")
            if url_signifier in item_href:
                fallback_name = item_href.split("member=", 1)[1]
                if member_dict.get(item_href):
                    name = member_dict[item_href]
                else:
                    name = get_member_full_name(item_href, fallback_name)
                    member_dict[item_href] = name
                if comm.chamber == "legislature":
                    match = re.search(
                        rf"({fallback_name})\s+-\s+(.+)",
                        detail_item.getparent().text_content(),
                    )
                    role = (
                        match.groups()[1]
                        if match and len(match.groups()) == 2
                        else "Member"
                    )
                else:
                    next_elem = detail_item.getnext().text
                    role = next_elem if isinstance(next_elem, str) else "Member"
                comm.add_member(name=re.sub(r"\(.*\)", "", name), role=role)

        if not comm.members:
            raise SkipItem("empty committee")

        return comm


class CommitteeList(HtmlListPage):
    """
    Scrape a list of committees.
    :param selector: CSS matcher for each committee url, according to chamber.
    :param member_selector: CSS matcher for each member within a committee -
    passed directly to CommitteeDetail.
    :param comm_url_signifier: Part of each matched element's href that should
    exist in a valid committee directory url.
    :param member_url_signifier: Part of each matched element's href
    that should exist in a valid member profile url.
    :param chamber: Chamber of this group of committees. e.g. "upper",
    "lower", "legislature"
    :param members_urls_and_names: Collection built throughout run that
    eliminates duplicate HTTP requests of member urls for name retrieval
    """

    selector: CSS
    member_selector: CSS
    comm_url_signifier: str
    member_url_signifier: str
    chamber: str
    members_urls_and_names = {}

    def process_item(self, item):
        if self.comm_url_signifier in item.get("href"):

            # As of last scrape, no subcommittees were found in upper or lower
            # chambers, but the custom exception should be raised if they are.
            if "Subcommittee" in item.text:
                if not self.chamber == "legislature":
                    raise UnknownSubCommFound(self.chamber)

            comm = ScrapeCommittee(
                name=item.text,
                chamber=self.chamber,
                # WV subcommittees do not explicitly list parent committees
                classification="committee",
            )

            comm.add_source(item.get("href"), f"{item.text} committee url")

            return CommitteeDetail(
                [
                    comm,
                    self.members_urls_and_names,
                    self.member_selector,
                    self.member_url_signifier,
                ],
                source=URL(item.get("href"), timeout=20),
            )
        else:
            raise SkipItem("not a committee url")


class Senate(CommitteeList):
    source = "https://www.wvlegislature.gov/committees/senate/main.cfm"
    selector = CSS("#wrapleftcolr a")
    member_selector = CSS("#wrapleftcol a")
    comm_url_signifier = "SenateCommittee.cfm"
    member_url_signifier = "Senate1/lawmaker.cfm"
    chamber = "upper"


class House(CommitteeList):
    source = "https://www.wvlegislature.gov/committees/house/main.cfm"
    selector = CSS("#wrapleftcol a")
    member_selector = CSS("#wrapleftcol a")
    comm_url_signifier = "HouseCommittee.cfm"
    member_url_signifier = "House/lawmaker.cfm"
    chamber = "lower"


class Joint(CommitteeList):
    source = "https://www.wvlegislature.gov/committees/interims/interims.cfm"
    selector = CSS("#wrapleftcol a")
    # min_items set to zero because not all joint committees have appointed members
    member_selector = CSS(".tabborder a", min_items=0)
    comm_url_signifier = "committee.cfm"
    member_url_signifier = "lawmaker.cfm"
    chamber = "legislature"
