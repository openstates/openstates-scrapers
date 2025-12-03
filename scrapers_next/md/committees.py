import re

from spatula import HtmlPage, HtmlListPage, XPath, SelectorError, URL
from openstates.models import ScrapeCommittee


class UnknownRole(Exception):
    def __init__(self, role):
        super().__init__(f"Unknown role: {role}")


class CommitteeList(HtmlListPage):
    selector = XPath("//div[@class='hide-on-mobile']//tr/td[1]/a")

    def process_item(self, item):
        return CommitteeDetails(
            {"chamber": self.chamber, "listpage": self.source.url},
            source=URL(item.get("href"), timeout=30),
        )


class CommitteeDetails(HtmlPage):
    def process_page(self):

        self.chamber = self.input.get("chamber")

        # Only one h2 on the page, should contain committee name
        name = XPath("//h2/text()").match_one(self.root).strip()

        # Remove " Committee" suffix from committee names
        comm_suffix = " Committee"
        if name.endswith(comm_suffix):
            name = name[: -len(comm_suffix)]

        # Remove prefix from joint committees
        joint_prefixes = [
            "Joint Committee on the ",
            "Joint Committee on ",
            "Joint Subcommittee on ",
            "Joint ",
        ]
        for prefix in joint_prefixes:
            if name.startswith(prefix):
                name = name.replace(prefix, "")

        # Remove prefix from numbered committees
        if name.startswith("No. "):
            name = re.sub(r"No\. \d+ - ", "", name).strip()

        self.com = ScrapeCommittee(
            name=name,
            classification="committee",
            chamber=self.chamber,
        )
        self.com.add_source(self.input.get("listpage"), note="committee list page")
        self.com.add_source(self.source.url, note="committee details page")
        self.com.add_link(self.source.url, note="homepage")

        if self.chamber == "legislature":
            # Joint committees have no subcommittees, and display members
            # in a different table than house/senate committees
            self.joint_members()
        else:
            member_list = []
            try:
                member_list = XPath("//div[@id='divMembership']").match_one(self.root)
            except SelectorError:
                # If the element wasn't found, no member data is available
                self.skip(self.com)
                return
            self.house_senate_members(self.com, member_list)
            yield from self.get_subcommittees()

        if len(self.com.members) > 0:
            yield self.com

    def get_subcommittees(self):
        divs = []
        try:
            # Each subcommittee is 3 divs. The first div contains the title,
            # the second two divs contains membership info. All subcommittees
            # are stored in one parent element.
            divs = XPath("//div[@aria-labelledby='divSubcommittees']/div").match(
                self.root
            )
        except SelectorError:
            # If the selector fails, there are no subcommittees
            return None

        for i in range(0, len(divs), 3):
            name = XPath(".//h3/text()").match_one(divs[i])
            subcom = ScrapeCommittee(
                name=name,
                chamber=self.chamber,
                classification="subcommittee",
                parent=self.com.name,
            )
            subcom.add_source(self.input.get("listpage"), note="committee list page")
            subcom.add_source(self.source.url, note="parent committee details page")
            subcom.add_link(self.source.url, note="homepage")

            # Add members from both of the member sections
            self.house_senate_members(subcom, divs[i + 1])
            self.house_senate_members(subcom, divs[i + 2])

            if len(subcom.members) > 0:
                yield subcom

    # House and senate pages have profile cards for members
    def house_senate_members(self, com, profile_element):
        members = []
        try:
            members = XPath(
                ".//div[@class='container-fluid member-index-group']/div/div[2]"
            ).match(profile_element)
        except SelectorError:
            self.skip(com)
            return

        for member in members:
            name = XPath(".//a/text()").match_one(member)
            role = None
            try:
                role = XPath(".//span[@class='bold-text']/text()").match_one(member)
            except SelectorError:
                role = "Member"
            self.attempt_add_member(com, name, role, "Member")

    # Joint committee membership data is in a table format, different from House/Senate
    def joint_members(self):
        member_lines = []
        try:
            member_lines = XPath("//div[@id='divMembership']//tbody/tr").match(
                self.root
            )
        except SelectorError:
            self.skip(self.com)
            return

        for member in member_lines:
            name = XPath("./td[1]").match_one(member).text_content()
            role = XPath("./td[2]/text()").match_one(member)
            self.attempt_add_member(self.com, name, role, "Public Member")

    # Attempt to parse a member's name and role and add them to a committee
    def attempt_add_member(self, com, name, role, default_role):

        # Special case
        if name == "To be announced":
            return

        name = transform_name(name)
        role = transform_role(role, default_role)

        # If a name contains ex officio marker, append that to their role
        ex_officio = "(ex officio)"
        if ex_officio in name:
            # Replace with and without space before, ensures that extra spacing
            # isn't added to the name.
            name = name.replace(f" {ex_officio}", "").replace(ex_officio, "")
            role += ex_officio

        com.add_member(name=name, role=role)

    def skip(self, com):
        self.logger.warning(f"No membership data for: {com.name}")


def transform_name(name):

    # Fix a name type found on website
    name = name.replace('Isaiah "Ike "Leggett', 'Isaiah "Ike" Leggett')

    # Change "<lastname>, <firstname>, <etc>" to "<firstname> <lastname> <etc>"
    name = name.split(", ")
    if len(name) > 1:
        name[0], name[1] = name[1], name[0]
    name = " ".join(name)

    # Make sure none of these have been moved to the start of the name in the
    # previous step.
    titles = [
        "Sr. ",
        "Jr. ",
        "II ",
        "III ",
        "VI ",
        "V ",
        "VI ",
        "VII ",
        "VIII ",
        "IX ",
        "X ",
    ]
    for title in titles:
        if name.startswith(title):
            name = name[len(title) :] + " " + title.strip()

    return name


# Detect the longest role present in the text, and return a matching role.
# The role "Member" is context-specific and may mean "Member" or "Public Member"
# default_role must be supplied to indicate which one it means.
def transform_role(role, default_role):
    role = role.strip()
    roles = {
        "Senate Chair": "Chair",
        "House Chair": "Chair",
        "Senate Co-chair": "Co-chair",
        "House Co-chair": "Co-chair",
        "Chair": "Chair",
        "Vice Chair": "Vice Chair",
        "Senate Member": "Member",
        "House Member": "Member",
        "Member": default_role,
    }

    longest_match = 0
    best_match = None
    for detect, value in roles.items():
        if detect in role:
            if longest_match < len(detect):
                longest_match = len(detect)
                best_match = value

    if best_match:
        return best_match
    else:
        raise UnknownRole(role)


class Senate(CommitteeList):
    source = "https://mgaleg.maryland.gov/mgawebsite/Committees/Index/senate"
    chamber = "upper"


class House(CommitteeList):
    source = "https://mgaleg.maryland.gov/mgawebsite/Committees/Index/house"
    chamber = "lower"


class Joint(CommitteeList):
    source = "https://mgaleg.maryland.gov/mgawebsite/Committees/Index/other"
    chamber = "legislature"
