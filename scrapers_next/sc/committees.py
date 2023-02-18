from spatula import HtmlPage, PdfPage, XPath, URL
from openstates.models import ScrapeCommittee
import re


class UnexpectedMemberListFormat(Exception):
    def __init__(self):
        super().__init__(
            "Unexpected member list format, number of headings didn't match number of member groups"
        )


class UnexpectedH4InMemberList(Exception):
    def __init__(self, h4_text):
        super().__init__(f'Unexpected h4 found in member list: "{h4_text}"')


class NotEnoughMembersFound(Exception):
    def __init__(self, found, need):
        super().__init__(f"Not enough members found. Found {found}, but need {need}")


class CommitteeDetails(HtmlPage):
    def process_page(self):
        # Title is present in the only h2 tag on the page
        title = XPath("//h2/text()").match_one(self.root)

        # Remove extra parts from the title
        suffix = " Committee"
        if title.endswith(suffix):
            title = title[: -len(suffix)]

        prefixes = ["House ", "Senate "]
        for prefix in prefixes:
            if title.startswith(prefix):
                title = title[len(prefix) :]

        # Create ScrapeCommittee and add sources
        com = ScrapeCommittee(
            name=title,
            classification="committee",
            chamber=self.input.get("chamber"),
        )
        com.add_source(self.input.get("list_page"), note="Committee list page")
        com.add_source(self.source.url, note="Committee details page")
        com.add_link(self.source.url, note="homepage")

        # Extract member info from the 'contentsection' div. There may be an h4
        # within this div that denotes all following members as ex-officio. Some
        # members may also be named with their title instead of their name, so
        # the link to their profile must be followed to read the member's actual
        # name
        member_info = XPath("//div[@id='contentsection']/div[1]/*").match(self.root)
        ex_officio = False
        for i in member_info:

            if i.get("style") == "clear: both;":
                # Skip the clear div, found before h4
                pass
            elif i.tag == "h4":
                if i.text_content() == "Ex Officio Members":
                    # All remaining members will be marked as Ex-Officio
                    ex_officio = True
                else:
                    raise UnexpectedH4InMemberList(i.text_content())
            elif i.tag == "br":
                # Skip br tag, found after h4
                pass
            else:
                member_link = XPath("./a").match_one(i)
                name, role = parse_member_link(member_link)
                if ex_officio:
                    role = f"{role} (Ex-Officio)"
                com.add_member(name=name, role=role)

        return com


class CommitteeList(HtmlPage):
    def process_page(self):
        self.logger.warning(
            "Committee list page may have information on subcommittees in docx format that cannot be scraped with Spatula."
        )
        committee_links = XPath("//div[@id='contentsection']/h4/a/@href").match(
            self.root
        )
        for link in committee_links:
            yield CommitteeDetails(
                {"chamber": self.chamber, "list_page": self.source.url},
                source=URL(link, timeout=30),
            )


# Converts text into a name and role. Checks if text references a position
# instead of a person and if so, follows the link to read the name on the
# profile.
def parse_member_link(link):
    text = link.text_content()
    name, role = extract_role(text)

    titles = ["Clerk of the House", "Speaker Pro Tempore", "Speaker of the House"]
    if name in titles:
        profile = MemberProfile(source=link.get("href"))
        name = next(profile.do_scrape())
    return name, role


# Gets a member name from their profile page
class MemberProfile(HtmlPage):
    def process_page(self):
        header = (
            XPath("//h2[@class='barheader']")
            .match_one(self.root)
            .text_content()
            .strip()
        )
        prefixes = ["Representative ", "Senator"]
        for prefix in prefixes:
            if header.startswith(prefix):
                header = header[len(prefix) :]
        return header


# Finds a role suffix from a name, removed it and returns (name, role)
def extract_role(name):
    # More roles can be added here if needed
    # SC abbreviates most roles
    name_suffixes = {
        ", Chairman": "Chairman",
        ", Vice Chairman": "Vice Chairman",
        ", 1st V.C.": "1st Vice Chairman",
        ", 2nd V.C.": "2nd Vice Chairman",
        ", V.C.": "Vice Chairman",
        ", Secy./Treas.": "Secretary, Treasurer",
        ", Secy.": "Secretary",
        ", Treas.": "Treasurer",
    }

    # Search for matching role and remove it from the name
    for suffix, suffix_role in name_suffixes.items():
        if name.endswith(suffix):
            # Role found, can return early
            name = name[: -len(suffix)]
            return name, suffix_role

    # No role found, so default to "Member"
    return name, "Member"


# Assume that the name ends in a role. Extract it and return name,role
def extract_any_role(name):
    return name.rsplit(", ", 1)


# Convert from "<lastname>, <firstname>" to "<firstname> <lastname>"
def reorder_name(name):
    name = name.split(", ")
    suffix = None
    if len(name) > 2:
        suffix = name.pop()
    name.reverse()
    partial_name = " ".join(name)
    if suffix:
        partial_name += f", {suffix}"

    return partial_name


# Used when parsing the Joint committee PDF, but too long to keep inside the function
non_name_prefixes = [
    "House of Representatives",
    "Published by:",
    "Senate and House",
    "of the",
    "Committees",
    "Joint and Special",
    "South Carolina",
    "\x0c",
    "vacant",
    "or designee,",
    "Association of",
    "persons recommended",
    "County council",
    "or administrator",
    "House from",
    "recommended",
    "State ",
    "General Assembly",
    "Apptd. by",
    "Commissioner of",
    "Association",
    "Chair,",
    "Committee",
    "Commission",
    "Special",
    "Gov.,",
    "Chair, ",
    "Solicitor",
    "Supt.",
]


class Joint(PdfPage):
    source = "https://www.scstatehouse.gov/publicationspage/JtSpecCommList.pdf"

    def process_page(self):
        # The membership pdf can't be parsed 100% accurately because the pdf
        # displays data in a two column layout and pdf2text causes the columns
        # to mix together. This function is a best attempt, and may break if the
        # PDF changes too much.

        # These lists will store data between steps
        com_names = []
        com_content = []
        com_members = []

        # Step 1
        # Break the PDF down into sections for each committee
        # Reversing makes it easier to find the committee names
        lines = self.text.split("\n")
        lines.reverse()
        name = ""
        in_name_section = False
        content = []
        for line_number, line in enumerate(lines):
            line = line.strip()
            if line == "Authority":
                # Committee name lines start this text. Current lines need to be
                # pushed as content since their section has ended
                in_name_section = True
                name = ""
                content.reverse()
                com_content += [content]
                content = []
            elif not in_name_section:
                content += [line]
            elif line == "":
                # Committe name lines end with a blank line
                in_name_section = False
                # Name can be pushed, but may have extra spaces that need to be cleaned up
                name = (
                    name.replace("COM MITTEE", "COMMITTEE")
                    .replace("CAN DI DATES", "CANDIDATES")
                    .replace("COM MISSION", "COMMISSION")
                    .replace("PUB LISH", "PUBLISH")
                    .title()
                )
                com_names += [name]
            else:
                # If inside a name section, prepend the line to the current name
                name = f"{line} {name}"

        # Step 2 -  Extract member list from each committee.
        for name, content in zip(com_names, com_content):
            names = []

            expected_members = 0
            for line in content:

                # Detect expected number of members
                member_count = re.match(r"^Members \((\d+)\)$", line)
                if member_count:
                    expected_members = int(member_count.groups(1)[0])

                # Blank lines aren't member names
                if line == "":
                    continue

                # Add vacant seats as placeholders, will be removed later
                vacancy_number = re.match(r"(\d+) vacanc", line)
                if vacancy_number:
                    vacancy_number = int(vacancy_number.groups(1)[0])
                    for i in range(0, vacancy_number):
                        names += [None]
                    continue

                # Handle single vacant seats
                if "vacant" in line.lower() or "vacancy" in line.lower():
                    names += [None]
                    continue

                # No names have a ':' or ';' character
                if ":" in line or ";" in line:
                    continue

                # No names end with a comma
                if line.endswith(","):
                    continue

                # Anything with numbers isn't a name
                if any(i.isdigit() for i in line):
                    continue

                # Ignore everything after the first comma for checking purposes
                full_line = line
                line = line.split(", ")[0]

                # Every word in a name starts with a capital letter
                if any(i[0].islower() for i in line.split(" ")):
                    continue

                # Names must have at least one space in them
                if " " not in line:
                    continue

                # Anything with a non_name_prefix isn't a name
                skip = False
                for nnp in non_name_prefixes:
                    if line.lower().startswith(nnp.lower()):
                        skip = True
                        break
                if skip:
                    continue

                # Return the part of the line after the first comma if it's part
                # of the name
                role = "Member"
                allowed_comma_suffixes = [
                    "jr.",
                    "jr",
                    "iii",
                    "iv",
                    "sr",
                    "sr.",
                    "v",
                    "vi",
                    "vii",
                    "viii",
                    "ix",
                    "x",
                    "m.d.",
                ]
                line = []
                for i, line_part in enumerate(full_line.split(", ")):
                    phrase = line_part.lower().strip()
                    # Skip first part, since that's before the first comma
                    if i == 0:
                        line += [line_part]
                    # Allow things like Jr. and III
                    elif phrase in allowed_comma_suffixes:
                        line += [line_part]
                    # Handle some special cases related to roles
                    elif phrase == "chm.":
                        role = "Chairman"
                    elif phrase == "v. chm.":
                        role = "Vice Chairman"
                    elif phrase == "ex officio":
                        role += " (Ex-Officio)"

                names += [dict(name=", ".join(line), role=role)]

            # Make sure there are at least the expected number of members
            if len(names) >= expected_members:
                names = names[0:expected_members]
                names = [i for i in names if i]  # Remove the Nones from vacancies
                com_members += [names]
            else:
                # Minimum number of expected members wasn't found
                raise NotEnoughMembersFound(len(names), expected_members)

        # Ste p3 - Create ScrapeCommittee and add members to it
        for name, members in zip(com_names, com_members):

            # Remove suffixes and prefixes from title
            prefixes = ["Joint ", "South Carolina ", "Committee On "]
            for prefix in prefixes:
                if name.lower().startswith(prefix.lower()):
                    name = name[len(prefix) :]

            suffixes = [" Committee"]
            for suffix in suffixes:
                if name.lower().endswith(suffix.lower()):
                    name = name[: -len(suffix)]

            # Replace special characters in the member name
            name = name.replace("\u2014", " - ")

            # Create committee object and add sources
            com = ScrapeCommittee(
                name=name, classification="committee", chamber="legislature"
            )
            com.add_source(self.source.url, note="Joint Committee information PDF")
            com.add_link(self.source.url, note="homepage")

            # Replace special characters in member names and add them to the committee
            for m in members:
                name = (
                    m.get("name")
                    .replace("\u201c", '"')
                    .replace("\u201d", '"')
                    .replace("\u2019", "'")
                )
                com.add_member(
                    name=name,
                    role=m.get("role"),
                )

            # Double check that there is at lest one member before yielding
            if len(com.members) == 0:
                self.logger.warning(f"No membership info for: {name}")
            else:
                yield com


class Senate(CommitteeList):
    source = "https://www.scstatehouse.gov/committee.php?chamber=S"
    chamber = "upper"


class House(CommitteeList):
    source = "https://www.scstatehouse.gov/committee.php?chamber=H"
    chamber = "lower"
