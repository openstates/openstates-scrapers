from spatula import HtmlPage, CSS, XPath, URL, SelectorError
from openstates.models import ScrapeCommittee


class InvalidCommitteeTitle(Exception):
    def __init__(self, title):
        super().__init__(f"Invalid committee title: {title}")


class InvalidMemberData(Exception):
    def __init__(self):
        super().__init__("Member information row has expected data")


class UnexpectedCommitteeName(Exception):
    def __init__(self, name):
        super().__init__(f"Table contains an unexpected committee: {name}")


class MemberDataRowInUnexpectedLocation(Exception):
    def __init__(self):
        super().__init__("Table contains a member detail row in an unexpected location")


class SenatorTitleHasMoreThanOneComma(Exception):
    def __init__(self, title):
        super().__init__(f"Senator title has more than one comma: {title}")


class SenatorTitleMissingPrefix(Exception):
    def __init__(self, title):
        super().__init__(f"Senator title did not have the expected prefix: {title}")


class SenateCommitteeList(HtmlPage):

    # This page lists committee names and members in a flat structure of
    # <p> tags. Committee names are distinguished by being further nested
    # within a <strong> tag.
    source = "https://legislature.maine.gov/standing-committees-of-the-senate"

    def process_page(self):
        committees = []
        p_tags = []
        try:
            # All relevant <p> tags are stored within #content
            p_tags = CSS("#content > p").match(self.root)
            # The first <p> tag is a page summary and should be ignored
            p_tags = p_tags[1:]
        except SelectorError:
            pass

        for p in p_tags:
            try:
                # This <p> contains a <strong> element and is a committee name
                committee_name = CSS("strong").match_one(p).text_content()
                committees.append(
                    ScrapeCommittee(
                        name=committee_name,
                        chamber="upper",
                        classification="committee",  # No senate subcommittees as of 2023-01-25
                    )
                )
                appended_comm = committees[-1]
                appended_comm.add_source(
                    self.source.url,
                    note="Committee details page",
                )
                appended_comm.add_link(self.source.url, note="homepage")
            except SelectorError:
                # This <p> only contains text and is a committee member name
                member_title = p.text_content()
                member_name, member_role = self.parse_member_title(member_title)
                committees[-1].add_member(name=member_name, role=member_role)

        for com in committees:
            # valid committee
            if len(com.members) > 0:
                yield com
            # invalid committee
            else:
                self.logger.warning(f"No membership data found for: {com.name}")

    # Senate member titles are in this format:
    # "Senator <name> (<party>-<county>), <role>"
    # Everything from the comma onwards may be omitted
    def parse_member_title(self, title):
        # Check to make sure the title has the expected prefix
        senator_prefix = "Senator "
        if not title.startswith(senator_prefix):
            raise SenatorTitleMissingPrefix(title)

        # Remove the prefix
        title = title[len(senator_prefix) :]

        # Remove portion of the title between first "(" and last ")"
        start = title.split("(")[0]
        end = title.split(")")[-1]
        title = start + end

        # At this point, title format should either be "name" or "name , role"
        title_parts = title.split(",")
        title_length = len(title_parts)

        # title format is just "name", so a default role of "Member" is given
        if title_length == 1:
            return title_parts[0].strip(), "Member"

        # title format is "name , role"
        elif title_length == 2:
            return title_parts[0].strip(), title_parts[1].strip()

        else:
            raise SenatorTitleHasMoreThanOneComma(title)


class HouseOrJointCommitteeMemberList(HtmlPage):
    # This class will scrape this page:
    # https://legislature.maine.gov/house/house/Committees/CommitteeMembersHouse?Legislature=131
    # This page contains membership information for house and joint committees
    # The Legislature parameter changes each year
    def process_page(self):
        committees = self.input.get("committees")

        # All the data we need is stored in a single table, so we extract the rows
        table_rows = []
        try:
            table_rows = XPath("//table[@class='short-table']//tr/td").match(self.root)
        except SelectorError:
            pass

        com = None

        for row in table_rows:
            # Each row in this table is one of three things:
            committee_name = None
            back_to_top = None
            member_text = None

            # 1) Committee name
            try:
                committee_name = XPath("h1/text()").match_one(row).strip()
            except SelectorError:
                pass

            # 2) Back to top link
            try:
                XPath("div/h1").match_one(row)
                back_to_top = True
            except SelectorError:
                pass

            # 3) Membership Information
            member_text = row.text_content()

            # Committee names are cross-checked to make sure they match the
            # names seen on a previous page. The scraper will break if an
            # unexpected committee is seen.
            if committee_name:
                matched_committee = None
                for c in committees:
                    if c.name == committee_name:
                        matched_committee = c
                        committees.remove(c)
                        break
                if matched_committee:
                    com = matched_committee
                    com.add_source(self.source.url, note="Committee details page")
                    com.add_link(self.source.url, note="homepage")
                else:
                    raise UnexpectedCommitteeName(com.name)

            # Back to top link means that there is no more membership data
            # for the current committee, and it can be yielded as long as
            # there is at least one member assigned to it
            elif back_to_top:
                if com:
                    if len(com.members) > 0:
                        yield com
                    else:
                        self.logger.warning(f"No membership data found for: {com.name}")

            # Member text is parsed to extract the name and role
            # After that, it is added to the current committee
            elif member_text:
                if not com:
                    raise MemberDataRowInUnexpectedLocation()
                name, role = self.parse_member_title(member_text)
                com.add_member(name=name, role=role)

        # Any committees left in this list were not seen in the committee table
        # and have no member info.
        for com in committees:
            self.logger.warning(f"No membership data found for: {com.name}")

    def parse_member_title(self, text):
        # Here's an example of the expected format of text
        # "
        #                    (Ranking Member)
        #                                        Billy Bob Faulkingham  (R -
        # Winter Harbor)
        #
        #
        #
        #                                 View Profile
        # "

        # Start by removing all newline characters and stripping whitespace
        text = text.replace("\r\n", "").strip()

        # The text now contains the following data separated with many spaces (" "):
        # - Member role (optional)
        # - Member name
        # - Party-district
        # - The string "View Profile"
        # The individual blocks of data do not contain double spaces, so we can
        # split by "  ".
        data_blocks = text.split("  ")

        # Then remove all empty strings from the list
        data_blocks = [b for b in data_blocks if b]

        # data_blocks is now a nice list containing the 3 or 4 pieces of data
        # If it does not contain a role, then it is in this format: [name,_,_]
        # If it contains a role, then it is in this format: [role,name,_,_]
        role = "Member"
        name = None
        num_data_blocks = len(data_blocks)

        # Role not included, supply a default
        if num_data_blocks == 3:
            name = data_blocks[0].strip()
            role = "Member"

        # Role and name are included in the data
        elif num_data_blocks == 4:
            name = data_blocks[1].strip()
            role = data_blocks[0].strip()[1:-1]  # Role is surrouned with ()

        # We have invalid data if there are any other number of elements
        else:
            raise InvalidMemberData()

        return name, role


# House and Joint committees are listed on the same page.
# This page is just an overview of which committees exist, and does not include
# any membership data.
class HouseAndJointCommitteeList(HtmlPage):
    source = "https://legislature.maine.gov/house/house/Committees"

    def process_page(self):
        # There are two tables, one for House and one for Joint committees
        # The required table is scraped based on self.committee_type
        committee_titles = XPath(
            f"//*[@id='content-page']//h1[text()='{self.committee_type} Committees']/../../..//td[@class='short-tabletdlf']"
        ).match(self.root)

        committees = []
        for c in committee_titles:
            committees.append(
                ScrapeCommittee(
                    name=self.parse_committee_title(c.text_content()),
                    chamber=self.chamber,
                    classification="committee",
                )
            )

        # Next, find the member list link in the quick link area
        # This link changes each year
        members_source = XPath(
            f"//ul[@id='menu-shortcodes']/li/a[text()='{self.committee_type} Committee Members']/@href"
        ).match_one(self.root)

        # Pass the committee list so it can be double checked against
        # the committee list present on the next page
        yield HouseOrJointCommitteeMemberList(
            {"committees": committees}, source=URL(members_source, timeout=30)
        )

    def parse_committee_title(self, title):
        # Title format: "<HOUSE/JOINT> - <name> (<abbr>)"
        # Titles have lots of whitespace and new lines around them, so
        # the first step is to strip those away.
        title = title.strip()

        # Check to make sure committee type matches expected type
        expected_prefix = f"{self.committee_type.upper()} - "
        if title.startswith(expected_prefix):
            # Prefix found as expected, remove it
            title = title[len(expected_prefix) :]
        else:
            # Prefix not found, something has gone wrong
            raise InvalidCommitteeTitle(title)

        # At this point, title format is: "<name> (<abbr>)"
        # Remove the abbreviation, since the name is all that matters here
        committee_name = title.split(" (")[0]
        return committee_name


class HouseCommitteeList(HouseAndJointCommitteeList):
    committee_type = "House"
    chamber = "lower"


class JointCommitteeList(HouseAndJointCommitteeList):
    committee_type = "Joint"
    chamber = "legislature"
