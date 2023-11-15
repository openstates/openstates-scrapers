from spatula import HtmlPage, HtmlListPage, CSS, XPath, SkipItem, URL, SelectorError
from openstates.models import ScrapeCommittee


class ChamberException(Exception):
    def __init__(self, com_name):
        super().__init__(f"Unexpected chamber for: {com_name}.")


class CommitteeList(HtmlListPage):
    selector = CSS("[data-committeersn]")

    def process_item(self, item):
        href = item.find("a").get("href")
        parent = get_parent(self.root, item)
        return CommitteeDetail(
            {"parent": parent, "chamber": self.chamber},
            source=URL(href, timeout=30),
        )


class Senate(CommitteeList):
    source = "https://legislature.ky.gov/Committees/senate-standing-committee"
    chamber = "upper"


class House(CommitteeList):
    source = "https://legislature.ky.gov/Committees/house-standing-committee"
    chamber = "lower"


class Joint(CommitteeList):
    source = "https://legislature.ky.gov/Committees/interim-joint-committee"
    chamber = "legislature"


class Statutory(CommitteeList):
    source = "https://legislature.ky.gov/Committees/statutory-committee"
    chamber = "legislature"


class Special(CommitteeList):
    source = "https://legislature.ky.gov/Committees/special-committee"
    chamber = "legislature"


# Used by CommitteeList classes to get an item's parent committee name
# Returns None if the item is not a subcommittee
def get_parent(root, item):
    parent_committee_id = item.get("data-parentcommitteersn")
    parent = None
    if parent_committee_id != "":
        parent = XPath(
            "//li[@data-committeersn='{id}']/a".format(id=parent_committee_id)
        ).match(root)[0]
        parent = strip_committee_name(parent.text_content())
    return parent


class CommitteeDetail(HtmlPage):
    def process_page(self):
        title = CSS(".committee-title > h2").match(self.root)[0].text_content()
        parent_committee = self.input.get("parent")
        com = get_committee_info(title, parent_committee)
        com.add_source(self.source.url, note="committee details page")
        com.add_link(self.source.url, note="homepage")

        # Make the scraper more fragile by doing an extra check to
        # make sure expected chamber and detected chamber are the same
        expected_chamber = self.input.get("chamber")
        if com.chamber != expected_chamber:
            raise ChamberException(com.name)

        # Add members, skipping the committee if no members are found
        members = []
        try:
            members = XPath("//ul[@class='member-list']/li/a").match(self.root)
        except SelectorError:
            raise SkipItem(f"No membership data found for: {com.name}")
        for member in members:
            add_member(com, member.text_content())

        return com


# Senate and House committee names end with " (S)" or " (H)"
# Other committee names have no suffix
def strip_committee_name(committee_name):
    is_house_committee = committee_name.endswith(" (H)")
    is_senate_committee = committee_name.endswith(" (S)")
    if is_house_committee or is_senate_committee:
        # Remove the " (H)" or " (S)" suffixes
        # They are are both 4 characters long
        return committee_name[0:-4]
    return committee_name


def get_committee_info(title, parent):
    committee_types = {
        "Senate Standing Committee": "upper",
        "House Standing Committee": "lower",
        "Interim Joint Committee": "legislature",
        "Statutory Committee": "legislature",
        "Special Committee": "legislature",
    }
    subcommittee_prefix = "BR Sub. on "

    for committee_type in committee_types.keys():
        if not title.startswith(committee_type):
            continue

        chamber = committee_types[committee_type]
        has_parent = parent is not None

        name = strip_committee_name(title[len(committee_type) :])
        has_subcommittee_prefix = name.startswith(subcommittee_prefix)
        if has_subcommittee_prefix:
            name = name[len(subcommittee_prefix) :]

        return ScrapeCommittee(
            name=name,
            chamber=chamber,
            classification="subcommittee" if has_parent else "committee",
            parent=parent,
        )


# Member strings are formatted like: "name - (Party) - Role" or "name - (Party)"
def add_member(com, member):
    title = member.split(" - ")
    name = title[0].strip()
    role = "Member"
    if len(title) == 3:
        role = title[2].strip()
    com.add_member(name=name, role=role)
