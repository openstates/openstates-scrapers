from spatula import (
    HtmlPage,
    SkipItem,
    HtmlListPage,
    CSS,
    XPath,
    URL,
    SelectorError,
    PdfPage,
)
from openstates.models import ScrapeCommittee
import re


class CommitteeList(HtmlListPage):
    # www.cga.ct.gov has and invalid ssl cert as of 2023-01-30, so passing verify=False
    source = URL("http://www.cga.ct.gov/asp/menu/cgacommittees.asp", verify=False)

    # This page has a list of links to committees
    selector = CSS(".row .square-bullet .list-group-item a")

    def process_item(self, item):
        href = item.get("href")
        committee_name = item.text_content().strip()

        # "\xc2\xa0" is sometimes used instead of a normal space in committee names
        # There may be a better way than this to replace them with regular spaces
        committee_name = (
            committee_name.encode("ascii", "replace").decode("utf-8").replace("?", " ")
        )

        # As of 2023-01-30, only one committee has a prefix that needs to be removed
        prefix = "Joint Committee on "
        if committee_name.startswith(prefix):
            committee_name = committee_name[len(prefix) :]

        # In CT, all committees are joint and there are no subcommittees
        com = ScrapeCommittee(
            name=committee_name,
            classification="committee",
            chamber="legislature",
        )

        # One of the committee pages is formatted differently from the rest
        if committee_name == "Reapportionment Commission":
            # This is the start of a chain of 3 pages that must be traversed
            # to get to the member pdf.
            # Javascript redirect page -> Committee details page -> Membership PDF
            return ReapportionmentCommissionRedirect(
                dict(com=com),
                source=URL(href, timeout=30, verify=False),
            )
        else:
            # Every other committee page is in the same format
            return CommitteeMemberPage(
                dict(com=com),
                source=URL(href, timeout=30, verify=False),
            )


class CommitteeMemberPage(HtmlPage):
    def process_page(self):
        com = self.input.get("com")
        com.add_source(self.source.url, note="Committee details page")
        com.add_link(self.source.url, note="homepage")

        # Member names and rows are stored within a table
        row_selector = XPath("//table[@summary='Committee member list']/tbody/tr")
        member_rows = None
        try:
            member_rows = row_selector.match(self.root)
        except SelectorError:
            raise SkipItem(f"No membership data found for: {com.name}")

        # Add every member found in the table
        for row in member_rows:
            member_role = XPath("td[2]").match_one(row).text_content().strip()
            member_name = XPath("td[3]").match_one(row).text_content().strip()

            # Transform "lastname, firstname" into "firstname lastname"
            name_parts = member_name.split(", ")
            name_parts.reverse()
            member_name = " ".join(name_parts)

            com.add_member(
                name=member_name,
                role=member_role,
            )

        if len(com.members) == 0:
            raise SkipItem(f"No membership data found for: {com.name}")

        return com


class ReapportionmentCommissionRedirect(HtmlPage):
    # This page uses javascript to do a redirect like so:
    # window.location.href = "/rr/taskforce.asp?TF=20210401_2021%20Redistricting%20Project";
    def process_page(self):

        # Extract the redirect link
        text = self.root.text_content()
        href = re.findall(r'"(.*)"', text)[0]

        # Prepend the domain name, since this is a relative link
        href = "http://www.cga.ct.gov" + href

        return ReapportionmentCommissionDetailsPage(
            self.input,
            source=URL(href, timeout=30, verify=False),
        )


class ReapportionmentCommissionDetailsPage(HtmlPage):
    # The only info needed from this page is the link to the membership pdf
    def process_page(self):
        pdf_link_sel = XPath("/html/body/div[3]/div[3]/div[1]/div/div[4]/div[2]/a")
        pdf_link = pdf_link_sel.match_one(self.root)
        href = pdf_link.get("href")
        return ReapportionmentCommissionPdf(
            self.input,
            source=URL(href, timeout=30, verify=False),
        )


class ReapportionmentCommissionPdf(PdfPage):
    def process_page(self):
        com = self.input.get("com")
        com.add_source(self.source.url, note="Committee member list pdf")

        # All the lines after "Membership List" are member names or blank lines
        members_text = self.text.strip().split("Membership List")[1]

        # Split into a list and remove the remove blank lines
        members = [m for m in members_text.split("\n") if m]

        # Most members have district info after their name, it should be ignored
        members = [m.split(", ")[0] for m in members]

        # Most members also have a prefix before their name
        # These prefixes are based on those found on 2023-01-30
        # This may not be an exhaustive list.
        title_prefixes = [
            "Senator ",
            "Senate President Pro Tempore ",
            "Senator Majority Leader ",  # <- This was found as a title, it may be a typo.
            "Senate Majority Leader ",  # <- If the typo is fixed, it may be changed to this.
            "Senate Minority Leader ",
            "House Majority Leader ",
            "House Minority Leader ",
            "Speaker of the House ",
            "Representative ",
        ]

        # Sort the prefixes by decreasing length to make sure a shorter prefix
        # isn't removed when it's really part of a longer prefix. Example where
        # this is required:
        # "Senator" and "Senator Majority Leader"
        title_prefixes.sort(key=len, reverse=True)

        for name in members:
            # Remove the matching prefix from the name
            for prefix in title_prefixes:
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    # Can stop after first match, there won't be multiple prefixes
                    break

            com.add_member(
                name=name,
                role="Member",  # This committee does not appear to have roles as of 2023-01-30
            )

        if len(com.members) == 0:
            raise SkipItem(f"No membership data found for: {com.name}")

        return com
