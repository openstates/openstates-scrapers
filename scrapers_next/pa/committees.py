from spatula import HtmlPage, SelectorError, XPath, URL, SkipItem
from openstates.models import ScrapeCommittee


"""
The classes that should be run to ensure every committee is scraped include:
- House
- Senate
- JointCommitteeList
"""


class UnhandledJointCommittee(Exception):
    def __init__(self, committee_name):
        super().__init__(f"Unhandled joint committee: {committee_name}")


class CommitteeList(HtmlPage):
    def process_page(self):
        committee_selector = XPath("//table[@class='DataTable-Grid']/tbody/tr/td[1]/a")
        items = None
        try:
            items = committee_selector.match(self.root)
        except SelectorError:
            # There are no committees listed yet, info for the current year
            # is not yet available
            years = (
                XPath("//select/option[@selected='selected']/text()")
                .match_one(self.root)
                .strip()
            )
            self.logger.warning(
                f"Committee info for {years} {self.chamber} committees is not yet available."
            )
            return None

        for item in items:
            href = item.get("href")
            committee_name = item.text_content()

            possible_prefix = "Committee On "
            if committee_name.startswith(possible_prefix):
                committee_name = committee_name[len(possible_prefix) :]

            # CommitteeDetail will yield a committee and its subcommittees
            yield CommitteeDetail(
                {
                    "listpage": self.source.url,
                    "name": committee_name,
                    "chamber": self.chamber,
                },
                source=URL(href, timeout=30),
            )


class House(CommitteeList):
    chamber = "lower"
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=H"

    # As of 2023-02-06, Updated house info for 2023 isn't yet posted
    # To test with 2021-2022 data, use the following source instead
    # source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=H&SessYear=2021"


class Senate(CommitteeList):
    chamber = "upper"
    source = "https://www.legis.state.pa.us/cfdocs/CteeInfo/StandingCommittees.cfm?CteeBody=S"


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = ScrapeCommittee(
            name=self.input.get("name"), chamber=self.input.get("chamber")
        )

        # Add sources and links
        com.add_source(self.input.get("listpage"), note="Committee list page")
        com.add_source(self.source.url, note="Committee homepage")
        com.add_link(self.source.url, note="homepage")

        # Chair people are listed apart from the rest of the member list
        chair_members = XPath("//div[@class='ChairNameText']").match(self.root)
        for chair_member in chair_members:
            name, role = extract_member_data(chair_member)
            com.add_member(name=name, role=role)

        # The rest of the member list
        members = XPath(
            "//div[contains(@class,'Column-Full')]//div[contains(@class,'MemberNameText')]/.."
        ).match(self.root)
        for member in members:
            name, role = extract_member_data(member)
            com.add_member(name=name, role=role)

        yield check_enough_members(com)

        # Discover subcommittees by checking the roles of every
        # committee member to see who the subcommitee chairs are.
        subcoms = {}
        for member in com.members:
            subcom_prefix = "Subcommittee Chair on "
            if not member.role.startswith(subcom_prefix):
                continue

            # Extract the subcommittee name from the role
            subcom_name = member.role[len(subcom_prefix) :]

            # Helper function, may be called more than once
            def build_committee(name, role):
                subcom = None
                if name in subcoms:
                    subcom = subcoms[name]
                else:
                    subcom = ScrapeCommittee(
                        name=name,
                        chamber=self.input.get("chamber"),
                        classification="subcommittee",
                        parent=self.input.get("name"),
                    )
                    # Add sources and links
                    subcom.add_source(
                        self.input.get("listpage"), note="Committee list page"
                    )
                    subcom.add_source(self.source.url, note="Parent committee homepage")
                    subcom.add_link(self.source.url, note="homepage")
                    subcoms[name] = subcom

                # Only the chair member is known for subcommittees
                subcom.add_member(name=member.name, role=role)

            # There are two outliers for subcommittee roles in the 2021-2022
            # lower committees, They need to be hardcoded because the format is
            # ambiguous. 2023-2024 committiees are not yet posted (as of 2023-02-05)
            # and may not have these outliers, or they may have more outliers
            # that need to be added here.
            if subcom_name == "Cities, Counties - Second Class":
                build_committee("Cities", "Chair")
                build_committee("Counties", "Chair, Second Class")
            elif subcom_name == "Cities, Third Class":
                build_committee("Cities", "Chair, Third Class")
            else:
                build_committee(subcom_name, "Chair")

        yield from subcoms.values()


# Helper function for CommitteeDetail, gets name and role from a member element
def extract_member_data(base_element):

    name = XPath(".//a/text()").match_one(base_element)
    role = None
    try:
        role = XPath("./div[@class='position']/text()").match_one(base_element)
    except SelectorError:
        role = "Member"

    # Convert from "lastname, firstname" to "firstname lastname"
    name = name.strip().split(", ")
    name.reverse()
    name = " ".join(name)

    # Roles need to be stripped and have a special character substituted
    role = role.strip().replace("\u2011", "-")

    return name, role


class CapitolPreservationComm(HtmlPage):
    source = "http://cpc.state.pa.us/about/capitol-preservation-committee-members.cfm"

    def process_page(self):
        com = ScrapeCommittee(
            name="Capitol Preservation",
            classification="committee",
            chamber="legislature",
        )
        com.add_link("http://cpc.state.pa.us/", note="homepage")
        com.add_source(
            self.source.url,
            note="Member list page",
        )

        members = XPath(
            "//div[@class='journal-content-article']/div[@class='member']"
        ).match(self.root)

        for member in members:
            # Skip vacant seats
            image = XPath("./img").match_one(member)
            if image.get("src").endswith("/images/about/members/Vacant.jpg"):
                continue

            # These titles are not all formatted in the same way
            title = XPath("./p/text()").match(member)

            # First line is always the title (since vacant positions are skipped already)
            name = title[0].strip()

            # If the final character of the name is a comma, remove it
            if name.endswith(","):
                name = name[:-1]

            # Join the title together, ignoring senator/representative job title
            title = [
                x for x in title if x not in "Senator" and x not in "Representative"
            ]
            title = " ".join(title[1:])

            role = None
            try:
                # Sometimes the role is listed in bold.
                role = XPath("./p/strong/text()").match_one(member).strip()

                # If member also has a title, append it to their role
                if title != "":
                    role += f", {title}"

            except SelectorError:
                # If a member has no bold role, fall back on just using their
                # title. If there also isn't a title, set role to Member
                role = title if title else "Member"

            com.add_member(name=name, role=role)

        return check_enough_members(com)


class CommissionOnSentencing(HtmlPage):
    source = "https://pcs.la.psu.edu/policy-administration/about-the-commission/members/current-commission-members/"

    def process_page(self):
        com = ScrapeCommittee(
            name="Sentencing",
            classification="committee",
            chamber="legislature",
        )
        com.add_link("https://pcs.la.psu.edu/", note="homepage")
        com.add_source(
            self.source.url,
            note="Member list page",
        )

        # Member roles are not listed directly and must be inferred from
        # the section that the member is listed in.
        member_sections = XPath(
            "//div[@data-widget_type='jet-listing-grid.default']"
        ).match(self.root)

        sections = [
            {"member_section": member_sections[0], "role": "Chair"},
            {"member_section": member_sections[1], "role": "Vice Chair"},
            {"member_section": member_sections[2], "role": None},
            {"member_section": member_sections[3], "role": "Ex-officio"},
        ]
        for section in sections:
            members = XPath("./div//h4/a").match(section["member_section"])
            for member in members:
                name = member.text_content()
                # Use role from position, may be overidden later
                role = section["role"]
                # Name may start with a title prefix
                name, role = parse_name_and_role(name, role)

                com.add_member(name, role)

        # This commission has subcommittees
        yield CommissionOnSentencingSubcommList({"com": com})

        yield check_enough_members(com)


class CommissionOnSentencingSubcommList(HtmlPage):
    source = "https://pcs.la.psu.edu/policy-administration/about-the-commission/standing-committees/"

    def process_page(self):

        subcoms = XPath(
            "//div[@data-widget_type='text-editor.default'][position()>1]"
        ).match(self.root)
        for subcom in subcoms:

            # Extract committee name and member lists
            name = XPath(".//h3/text()").match_one(subcom)
            chairs = XPath(".//ul[1]/li/text()").match(subcom)
            members = XPath(".//ul[2]/li/text()").match(subcom)

            # Remove committee suffix from title
            committee_suffix = " Committee"
            if name.endswith(committee_suffix):
                name = name[: -len(committee_suffix)]

            com = ScrapeCommittee(
                name=name,
                classification="subcommittee",
                chamber="legislature",
                parent=self.input.get("com").name,
            )
            com.add_link("https://pcs.la.psu.edu/", note="homepage")
            com.add_source(
                self.source.url,
                note="Member list page",
            )

            for chair in chairs:
                memname, role = parse_name_and_role(chair, "Chair")
                com.add_member(name=memname, role=role)
            for member in members:
                # In some cases, the member list is not a list of members, and
                # is instead a reference to all members of the parent committee
                if member == "All Commission Members (appointed and ex officio)":
                    # Add all non-(vice)chair members from parent committee
                    for parent_member in self.input.get("com").members:
                        if parent_member.role in [
                            "Member",
                            "Public Member",
                            "Ex-officio",
                        ]:
                            com.add_member(
                                name=parent_member.name, role=parent_member.role
                            )
                else:
                    # Add member based on the text
                    memname, role = parse_name_and_role(member, None)
                    com.add_member(name=memname, role=role)
            yield check_enough_members(com)


# Helper function for some of the Joint Committees that display
# member names, titles, and roles in one block of text.
# This function tries to extract the correct name and role.
# A default role can be supplied when the role is already known
def parse_name_and_role(name, role):
    prefixes = {
        "Judge ": "Public Member",
        "Representative ": "Member",
        "Senator ": "Member",
        "Attorney ": "Public Member",
        "Defense Attorney ": "Public Member",
        "District Attorney ": "Public Member",
        "Professor ": "Public Member",
    }
    # Remove any title prefixes in the name
    for prefix, prefix_role in prefixes.items():
        if name.startswith(prefix):
            name = name[len(prefix) :]
            # Override role if itbs not yet set
            if role is None:
                role = prefix_role

    # Fall back on guessing that this is a public member if they have no role
    # Normal members should always have the Senator/Representative prefix
    if role is None:
        role = "Public Member"

    # Names may have suffixes related to that person's role in the parent committee
    # These are treated like part of the name and need to be removed
    # They must be listed individually, rather than removing all text after the comma,
    # because some names contain commas like "<name>, Jr."
    suffixes = [
        ", Commission Chair (ex officio)",
        ", Commission Chair",
        ", Commission Vice Chair",
        ", Commission Vice Chair (ex offico)",
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[: -len(suffix)]

    return name, role


class StateGovernmentComm(HtmlPage):
    source = "http://jsg.legis.state.pa.us/about-us.cfm"

    def process_page(self):
        com = ScrapeCommittee(
            name="State Government Commission",
            classification="committee",
            chamber="legislature",
        )
        com.add_source(self.source.url, note="Committee member list")
        com.add_link("http://jsg.legis.state.pa.us/", note="homepage")

        # Member list can be extracted from a single table
        # Titles are listed for each member, but these titles are not roles
        # and are ignored - all members have the role of "Member" in this committee
        members = XPath("//table[@id='table-execComm']//a/text()").match(self.root)
        for member in members:
            com.add_member(name=member, role="Member")
        return check_enough_members(com)


class LegAuditAdvisoryComm(HtmlPage):
    source = "https://www.legis.state.pa.us/cfdocs/cteeInfo/laac.cfm"

    def process_page(self):
        com = ScrapeCommittee(
            name="Legislative Audit Advisory Commission",
            classification="committee",
            chamber="legislature",
        )
        com.add_source(self.source.url, note="Committee member list")
        com.add_link(self.source.url, note="homepage")

        # Membership data for officers, house, senate, and public members
        # are stored in 4 separate lists.

        # 1) Officers
        officers = XPath(
            "//h4[text()='Officers']/../div[@class='CteeInfo-OfficerContainer']"
        ).match(self.root)
        for officer in officers:
            # Extract officer name from the alt text of their image
            officer_name = XPath(".//img/@alt").match_one(officer)
            officer_role = XPath(
                ".//div[@class='CteeInfo-OfficerPosition']/text()"
            ).match_one(officer)
            com.add_member(name=officer_name, role=officer_role)

        # 2,3) House and Senate Members
        members = []
        members += XPath("//h4[text()='House Members']/..//a/text()").match(self.root)
        members += XPath("//h4[text()='Senate Members']/..//a/text()").match(self.root)
        for member in members:
            com.add_member(name=member, role="Member")

        # 4) Public Members
        public_members = XPath("//h4[text()='Public Members']/..//li/text()").match(
            self.root
        )
        for public_member in public_members:
            com.add_member(name=public_member, role="Public Member")

        return check_enough_members(com)


class LegBudgetFinanceComm(HtmlPage):
    source = "http://lbfc.legis.state.pa.us/Committee-Members.cfm"

    def process_page(self):
        com = ScrapeCommittee(
            name="Legislative Budget and Finance",
            classification="committee",
            chamber="legislature",
        )
        com.add_source(self.source.url, note="Committee member list")
        com.add_link("http://lbfc.legis.state.pa.us/ ", note="homepage")

        # All members info can be extracted from one table.
        members = XPath(
            "//div[@class='row Committee-MemberWrapper']//div[@class='col-md-6 Committee-Member']"
        ).match(self.root)
        for member in members:
            name = (
                XPath("./div[@class='Committee-Member-Name']/a/text()")
                .match_one(member)
                .strip()
                .replace("  ", " ")  # Remove double-spaces from name
            )

            # Unfilled seats are listed with the name "Vacant"
            if name == "Vacant":
                continue

            role = (
                XPath("./div[@class='Committee-Member-Position']/text()")
                .match_one(member)
                .strip()
            )

            # If the role isn't listed, the role should be "Member"
            if role == "":
                role = "Member"

            com.add_member(name=name, role=role)

        return check_enough_members(com)


class LocalGovernmentComm(HtmlPage):
    source = "http://www.lgc.state.pa.us/"

    def process_page(self):
        com = ScrapeCommittee(
            name="Local Government Commission",
            classification="committee",
            chamber="legislature",
        )
        com.add_source(self.source.url, note="Committee member list")
        com.add_link(self.source.url, note="homepage")

        # All members can be extracted from a table at the bottom of the page
        # They have prefixes that must be removed, and possible role info
        # listed after the name. Example format: "Senator <name>, <role>"
        members = XPath(
            "//div[@class='row margin-top-20 margin-bottom-20 lgc-members-box']//a/text()"
        ).match(self.root)
        for member in members:
            # Remove double spaces and non-ascii spaces from member name
            member = " ".join(member.replace("  ", " ").split())

            # Remove title prefix
            prefixes = ["Senator ", "Representative "]
            for prefix in prefixes:
                if member.startswith(prefix):
                    member = member[len(prefix) :]

            # Try to detect roles, default to "Member" if none is found
            role = "Member"
            roles = ["Chair", "Vice Chair", "Ex-Officio"]
            for role_check in roles:
                role_suffix = f", {role_check}"
                if member.endswith(role_suffix):
                    member = member[: -len(role_suffix)]
                    role = role_check

            com.add_member(name=member, role=role)

        return check_enough_members(com)


class LegReapportionmentComm(HtmlPage):
    source = "https://www.redistricting.state.pa.us/commission/"

    def process_page(self):
        com = ScrapeCommittee(
            name="Legislative Reapportionment Commission",
            classification="committee",
            chamber="legislature",
        )
        com.add_source(self.source.url, note="Committee member list")
        com.add_link("https://www.redistricting.state.pa.us/", note="homepage")

        # Members have profile cards with name and role info
        members = XPath("//span[@class='thumb-info-title']").match(self.root)
        for member in members:
            name = (
                XPath("./span[@class='thumb-info-inner']/text()")
                .match_one(member)
                .strip()
            )
            # May be an actual role, or the member's title like "SENATE MAJORITY LEADER"
            role_text = (
                XPath("./span[@class='thumb-info-type']/text()")
                .match_one(member)
                .strip()
            )
            # Use a default role of "Member", but override it if role_text is
            # an actual role. Only the role of Chair exists as of 2023-02-06, but
            # if a vice chair is added in the future it should be parsed correctly.
            role = None
            possible_roles = ["Chair", "Vice Chair"]
            if role_text in possible_roles:
                role = role_text
            else:
                role = "Member"

            com.add_member(name=name, role=role)

        return check_enough_members(com)


def check_enough_members(com):
    if len(com.members) == 0:
        raise SkipItem(f"No member data found for: {com.name}")
    return com


# There is no joint committee list page, but there are 7 joint committees listed
# in the footer of https://www.legis.state.pa.us/ (as of 2023-02-05)
# These joint committees are each on different websites and need to be scraped
# with different methods.
class JointCommitteeList(HtmlPage):
    source = "https://www.legis.state.pa.us/"

    def process_page(self):
        links = XPath(
            "//div[@class='Widget Column-OneThird Column-Last']/ul/li/a/text()"
        ).match(self.root)

        for link_text in links:
            # Handle all known committees individually
            if link_text == "Capitol Preservation Committee":
                yield CapitolPreservationComm()
            elif link_text == "Commission On Sentencing":
                yield CommissionOnSentencing()
            elif link_text == "Joint State Government Commission":
                yield StateGovernmentComm()
            elif link_text == "Legislative Audit Advisory Commission":
                yield LegAuditAdvisoryComm()
            elif link_text == "Legislative Budget and Finance Committee":
                yield LegBudgetFinanceComm()
            elif link_text == "Local Government Commission":
                yield LocalGovernmentComm()
            elif link_text == "Pennsylvania Redistricting":
                yield LegReapportionmentComm()
            elif "committee" in link_text.lower():
                # Quick check to make sure a new committee wasn't added to the footer
                # Not all committees will have "committee" in the name, so this
                # isn't a perfect solution
                raise UnhandledJointCommittee(link_text)
