from spatula import HtmlPage, XPath, URL, SelectorError
from openstates.models import ScrapeCommittee


# All committees are listed on the same page
class CommitteeList(HtmlPage):
    source = "https://www.capitol.hawaii.gov/comminfolist.aspx"

    def process_page(self):

        # List of all committees on the page
        committees = XPath(
            "//div[@id='tabContent']//div[contains(@class,'justify-content-begin')]"
        ).match(self.root)

        for com in committees:
            yield self.process_committee(com)

    def process_committee(self, com_element):
        href = XPath("./h3/a/@href").match_one(com_element)
        name = XPath("./span/text()").match_one(com_element).strip()
        return CommitteeDetails(
            {"name": name, "list_url": self.source.url}, source=URL(href, timeout=30)
        )


# All committee types have the same format
class CommitteeDetails(HtmlPage):
    def process_page(self):

        # Detect which chamber this committee is for.
        chamber_header = (
            XPath("//*[@id='ctl00_MainContent_LabelChamberHeader']")
            .match_one(self.root)
            .text_content()
        )

        # Detect chamber type
        if chamber_header == "Senate Committee on":
            chamber = "upper"
        elif chamber_header == "House Committee on":
            chamber = "lower"
        else:
            chamber = "legislature"

        # Create committee and add links/sources
        com = ScrapeCommittee(
            name=transform_committee_title(self.input.get("name")),
            chamber=chamber,
            classification="committee",  # No subcommittees for HI as of 2023-02-13
        )
        com.add_source(self.input.get("list_url"), note="Committee list page")
        com.add_source(self.source.url, note="Committee member list")
        com.add_link(self.source.url, note="homepage")

        # Chairs and Vice-Chairs are important members and are listed
        # apart from other members
        important_members = []
        try:
            important_members = XPath(
                "//div[@class='d-flex flex-row contact-info']/div[2]"
            ).match(self.root)
        except SelectorError:
            # Important members not found, skip them
            pass
        for important_member in important_members:
            name = (
                XPath(".//h4/text()")
                .match_one(important_member)
                .strip()
                .replace("\n", "")
            )
            role = XPath(".//strong/text()").match_one(important_member)
            com.add_member(name=transform_name(name), role=role)

        # Regular members just have their names listed
        other_members = []
        try:
            other_members = XPath(
                "//table[@id='ctl00_MainContent_DataList1']//a/text()"
            ).match(self.root)
        except SelectorError:
            # Regular members list not found, skip them
            pass
        for other_member in other_members:
            name = other_member.strip().replace("\n", "")
            com.add_member(name=name, role="Member")

        # Check to make sure there is at least one member before returning
        if len(com.members) > 0:
            return com
        else:
            self.logger.warning(f"No membership data found for: {com.name}")


# Convert from "<lastname>, <firstname>" to "<firstname> <lastname>"
def transform_name(name):
    name = name.rsplit(", ", 1)
    name[0], name[1] = name[1], name[0]
    return " ".join(name)


# Remove prefixes from committee titles.
# HI has a few committees with names like:
# "House Investigative Committee to Investigate Compliance with Audit Nos. 19-12 and 21-01"
# For names like these, only the prefix of "House " will be removed.
def transform_committee_title(title):
    prefixes = [
        "Senate Special Committee on ",
        "House Special Committee on ",
        "Special Committee on ",
        "House ",
        "Senate ",
    ]
    for prefix in prefixes:
        if title.startswith(prefix):
            title = title[len(prefix) :]
    return title
