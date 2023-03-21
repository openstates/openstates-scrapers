from spatula import HtmlPage, HtmlListPage, CSS, XPath, SkipItem, URL, SelectorError
from openstates.models import ScrapeCommittee


class SenateCommitteeTitleMissingSuffix(Exception):
    def __init__(self, title):
        super().__init__(f"Senate committee title is missing expected suffix: {title}")


class UnknownJointCommitteeWebsite(Exception):
    def __init__(self, href):
        super().__init__(f"Unknown joint committee website: {href}")


class UnexpectedMemberTitle(Exception):
    def __init__(self, title):
        super().__init__(f"Member title does not follow expected format: {title}")


class JointCommitteeMustImplementGetMembers(Exception):
    def __init__(self, name):
        super().__init__(f"Joint committee didn't implement get_members(): {name}")


class JointCommittee(HtmlPage):
    def process_page(self):
        com = ScrapeCommittee(
            name=self.input.get("name"),
            chamber="legislature",
            classification="committee",
        )

        com.add_source(self.source.url, note="Committee details page")
        com.add_link(self.source.url, note="homepage")

        for (name, role) in self.get_members():
            com.add_member(name=remove_title_prefix(name), role=role)

        if len(com.members) == 0:
            raise SkipItem(f"No membership data found for: {com.name}")

        return com

    # get_members must be overridden by each class that extends JointCommittee
    def get_members(self):
        raise JointCommitteeMustImplementGetMembers(self.input.get("name"))

    # Two of the joint committee webpages have a very similar layout
    # and can be scraped in the same way.
    def get_members_shared(self):
        members = XPath("//div[@class='media-overlay-caption']").match(self.root)
        for m in members:
            name, role = m.text_content().strip().split("\n")
            role = role.strip()  # Role has some \t characters that need stripped

            # Unfilled positions are listed with the name is set to "Vacant"
            if name == "Vacant":
                continue

            # Members without a special role have their job title listed instead
            if role == "Representative" or role == "Senator":
                role = "Member"

            yield name, role


class CorrectionalInspection(JointCommittee):
    source = "https://www.ciic.state.oh.us/members/committee-members"

    def get_members(self):
        return self.get_members_shared()


class AgencyRuleReview(JointCommittee):
    source = "https://www.jcarr.state.oh.us/about/jcarr-committee"

    def get_members(self):
        return self.get_members_shared()


# This joint committee is referenced, but the link to it returns a 404
# This class is a placeholder in case the link starts to work again.
class CongressionalRedistricting(JointCommittee):
    source = ""

    def get_members(self):
        return []


# Take in a name that may or may not have a title prefix, and return only the base name
# If given a name without a title, it will return the name as it was given
def remove_title_prefix(title):
    prefixes_to_remove = [
        "President ",
        "Speaker ",
        "Minority Leader ",
        "Senator ",
        "Representative ",
    ]

    # Remove the matching prefix
    for prefix in prefixes_to_remove:
        if title.startswith(prefix):
            return title[len(prefix) :]
    return title


class Ethics(JointCommittee):
    source = "http://www.jlec-olig.state.oh.us/?page_id=1254"

    def get_members(self):
        member_selector = XPath(
            "//figure[@class='wp-block-table aligncenter']//a/text()"
        )
        member_titles = member_selector.match(self.root)
        # Member titles are in this format: "Senator/Representative <name>, <role>"
        # Roles (and the comma before them) may be omitted
        for title in member_titles:

            unprefixed_title = remove_title_prefix(title)
            # Every name is prefixed with a title
            # If nothing changed after trying to remove the prefix then
            # the data is invalid
            if title == unprefixed_title:
                raise UnexpectedMemberTitle(title)

            # If the member has a role, it will be comma separated
            title_parts = unprefixed_title.rsplit(", ", 1)
            name, role = None, None

            # No role, usedefault role of "Member"
            if len(title_parts) == 1:
                name = title_parts[0]
                role = "Member"

            # Role found
            elif len(title_parts) == 2:
                name = title_parts[0]
                role = title_parts[1]

            yield name, role


class MedicaidOversight(JointCommittee):
    source = "https://www.jmoc.state.oh.us/committee"

    def get_members(self):
        # Staff are also listed on this page, but only members have images
        member_selector = XPath("//table//tr/td/a/img/../..")
        member_elements = member_selector.match(self.root)
        for member_element in member_elements:

            # Title contains name and role like: "<name><role>" with no space between
            title = member_element.text_content().strip()

            # Name contains just the member's name
            name = XPath("a/strong/text()").match_one(member_element).strip()

            # Extract the role from the title by removing the name
            role = title[len(name) :]

            # Finally, set the role to "Member" if their job title was used
            if role == "Senator" or role == "Representative":
                role = "Member"

            yield name, role


class ServiceCommission(JointCommittee):
    source = "https://www.lsc.ohio.gov/pages/general/aboutus.aspx?active=idB"

    def get_members(self):
        selector = XPath("//div[@data-name='Commission Members']//ul/li")
        titles = selector.match(self.root)
        for title in titles:

            # Remove whitespace
            title = title.text_content().strip()

            # title is now either "<name>" or "<name>, <role>"
            title_parts = title.rsplit(", ", 1)
            name = None
            role = None

            # Title only had a name, provide a default role of "Member"
            if len(title_parts) == 1:
                name = title_parts[0]
                role = "Member"

            # Title has a name and a role
            elif len(title_parts) == 2:
                name = title_parts[0]
                role = title_parts[1]

            yield name, role


class StateControllingBoard(JointCommittee):
    source = "https://obm.ohio.gov/areas-of-interest/controlling-board/Members"

    def get_members(self):
        selector = XPath("//table[@class='ecbMemberTable']//tr/td//strong/text()")
        member_titles = selector.match(self.root)
        for title in member_titles:
            # Member title either:
            # 1) Starts with "Rep. " or "Sen. "
            # 2) Ends with ", <role>"
            name = None
            role = None

            # Check if the title has a prefix
            # If it does, remove it to get their name and supply a
            # default role of "Member"
            rep_prefix = "Rep. "
            sen_prefix = "Sen. "
            if title.startswith(rep_prefix):
                name = title[len(rep_prefix) :]
                yield name, "Member"
                continue
            elif title.startswith(sen_prefix):
                name = title[len(sen_prefix) :]
                yield name, "Member"
                continue

            # No prefix, so this must be a member with a role
            title_parts = title.rsplit(", ", 1)

            # Double check to make sure there is a single comma
            # If there isn't, then we're working with unexpected data
            if len(title_parts) != 2:
                raise UnexpectedMemberTitle(title)
            name = title_parts[0].strip()
            role = title_parts[1].strip()

            yield name, role


class CommitteeList(HtmlListPage):
    def process_item(self, item):
        committee_details_href = item.get("href")

        # Each joint committee detail page is a different website
        # an needs a unique scraper
        if self.chamber == "legislature":
            committee_name = item.text_content().strip()
            # Joint committee_names may be in any of these formats:
            # "<name> Committee"
            # "Joint Committee on <name>"
            # "Joint <name> Committee"
            # This logic should be flexible enough to work with new
            # committee names
            committee_name = (
                committee_name.replace("Joint Committee on", "")
                .replace("Committee", "")
                .replace("Joint", "")
                .strip()
            )
            return joint_committee_scraper(committee_details_href, committee_name)

        # House and Senate committee detail pages use a nearly identical format
        elif self.chamber == "upper":
            return SenateCommitteeDetail(
                dict(chamber=self.chamber),
                source=URL(committee_details_href, timeout=30),
            )
        elif self.chamber == "lower":
            return HouseCommitteeDetail(
                dict(chamber=self.chamber),
                source=URL(committee_details_href, timeout=30),
            )


# Maps joint committee urls to scrapers
# If more joint committees are added, more scrapers need to be added also
def joint_committee_scraper(href, name):
    if href == "http://www.ciic.state.oh.us":
        return CorrectionalInspection({"name": name})
    elif href == "http://www.jcarr.state.oh.us":
        return AgencyRuleReview({"name": name})
    elif (
        href
        == "https://www.legislature.ohio.gov/committees/joint-legislative-committees/joint-committee-on-congressional-redistricting"
    ):
        # This committee's website doesn't work. It returns a 404
        # If it did work, this scraper would be used
        # return CongressionalRedistricting({"name":name})
        raise SkipItem(
            f"Congressional Redistricting committee's website is broken as of (2023-01-27): {href}"
        )
    elif href == "http://www.jlec.state.oh.us":
        return Ethics({"name": name})
    elif href == "http://www.jmoc.state.oh.us":
        return MedicaidOversight({"name": name})
    elif href == "http://www.lsc.state.oh.us":
        return ServiceCommission({"name": name})
    elif (
        href
        == "https://obm.ohio.gov/wps/portal/gov/obm/areas-of-interest/controlling-board/controlling-board"
    ):
        return StateControllingBoard({"name": name})
    else:
        raise UnknownJointCommitteeWebsite(href)


class Senate(CommitteeList):
    source = "https://www.legislature.ohio.gov/committees/senate-committees"
    selector = CSS(".media-container > a")
    chamber = "upper"


# House and Joint committees are listed on the same page, but have different selectors
class House(CommitteeList):
    source = "https://ohiohouse.gov/committees"
    selector = XPath(
        "//section[@class='gray-block']/h2[contains(text(),'Standing Committees')]/..//a"
    )
    chamber = "lower"


class Joint(CommitteeList):
    source = "https://ohiohouse.gov/committees"
    selector = XPath(
        "//section[@class='gray-block']/h2[contains(text(),'Joint Legislative Committees')]/..//a"
    )
    chamber = "legislature"


class SenateCommitteeDetail(HtmlPage):
    def process_page(self):

        title_element = CSS(".content-container > h1").match_one(self.root)
        committee_title = title_element.text_content().strip()

        # Senate committee titles should have a suffix
        title_suffix = " Committee"

        # Raise an error if suffix isn't found
        if not committee_title.endswith(title_suffix):
            raise SenateCommitteeTitleMissingSuffix(committee_title)

        # Remove the suffix from title to get just the committee name
        committee_name = committee_title[: -len(title_suffix)]

        com = ScrapeCommittee(
            name=committee_name,
            chamber="upper",
            classification="committee",  # No subcommittes as of 2023-01-27
        )
        com.add_source(self.source.url, note="Committee details page")
        com.add_link(self.source.url, note="homepage")
        build_house_or_senate_membership(com, self.root)
        return com


class HouseCommitteeDetail(HtmlPage):
    def process_page(self):
        title_element = CSS(".section-title > h1").match_one(self.root)
        committee_name = title_element.text_content().strip()

        com = ScrapeCommittee(
            name=committee_name,
            chamber="lower",
            classification="committee",  # No subcommittes as of 2023-01-27
        )
        com.add_source(self.source.url, note="Committee details page")
        com.add_link(self.source.url, note="homepage")
        build_house_or_senate_membership(com, self.root)
        return com


def build_house_or_senate_membership(com, root):
    # Membership info on house and senate pages are contained within portraits
    # The pages are slightly different, but they share enough similarities to
    # be scraped by the same logic
    member_portraits = None
    try:
        member_portraits = CSS(".media-container-portrait > a").match(root)
    except SelectorError:
        raise SkipItem(f"No membership data found for: {com.name}")

    name_selector = CSS(".media-overlay-caption-text-line-1")
    role_selector = CSS(".media-caption")

    for portrait in member_portraits:
        name = name_selector.match_one(portrait).text_content()
        role = "Member"  # Default if no role is found in next step
        try:
            role = role_selector.match_one(portrait).text_content()
        except SelectorError:
            pass

        com.add_member(name=remove_title_prefix(name), role=role)

    return com
