from spatula import HtmlListPage, URL, XPath, HtmlPage, SelectorError
from openstates.models import ScrapeCommittee
import re

'''
class CommitteeDetail(HtmlListPage):
    # selector = XPath("//[text()='Members:']/following-sibling/a")
    selector = XPath(
        '//a[(contains(@href, "/sd") or '
        'contains(@href, "assembly.ca.gov/a")) and '
        '(starts-with(text(), "Senator") or '
        'starts-with(text(), "Assembly Member"))]/text()'
    )
    # "//*[@id="node-182047"]/div/div/div/div/p[11]/a[1]"
    # "//*[@id="node-39"]/div/div/div/div/p[25]/a[8]"
    # "//*[@id="node-39"]/div/div/div/div/p[25]/a[9]"

    def process_item(self, item):
        com = self.input
        # print(item)
        member_name = item.lstrip("Senator ")
        # member_name = item.text_content().lstrip("Senator ")
        com.add_member(name=member_name)
        return com

        # print(member_name)
        # if member_name.contains("(") and member_name.contains(")"):

        # print(item)


class CommitteeList(HtmlListPage):
    source = URL("https://www.senate.ca.gov/committees")
    # "https://www.assembly.ca.gov/committees"

    selector = CSS("div .region.region-content > div.block.block-views.clearfix a")

    def process_item(self, item):
        com_type = (
            item.getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .text_content()
            .strip()
            .split("\n")[0]
            .strip()
        )

        com_name = item.text_content()
        detail_link = item.get("href")
        different_xml = [
            # "https://sbp.senate.ca.gov" # h3 instread of h2,
            # "https://selc.senate.ca.gov" # different format,
            # "https://senv.senate.ca.gov" # different members heading,
            # "https://shea.senate.ca.gov" # h3 p a instead of h2 p a,
            # "https://sjud.senate.ca.gov" # h4 h4 a instead of h2 p a,
            # "https://spsf.senate.ca.gov" # members is p instead of h2,
            # "https://census.senate.ca.gov/" # ul li instead of p a,
            # "https://www.senate.ca.gov/domestic-violence",
            # "https://www.senate.ca.gov/hydrogen-energy",
            # "https://www.senate.ca.gov/mental-health-and-addiction",
            "http://assembly.ca.gov/fairsallocation",
            "http://fisheries.legislature.ca.gov/",
            "https://jtrules.legislature.ca.gov",
            "http://arts.legislature.ca.gov/",
            "http://legaudit.assembly.ca.gov/",
            "https://jtlegbudget.legislature.ca.gov/",
            "http://climatechangepolicies.legislature.ca.gov",
            "https://jtemergencymanagement.legislature.ca.gov/",
        ]
        if detail_link in different_xml:
            self.skip()

        if com_name.startswith("Joint"):
            chamber = "legislature"
        else:
            chamber = "upper"

        com = ScrapeCommittee(
            name=com_name,
            parent=chamber,
        )

        # this is being added for each member (only do once)
        com.add_source(self.source.url)
        com.add_link(detail_link)
        # add link as a source as well

        # print(com_type)
        """
        if com_type == "Sub Committees":
            # com_type = com_type.lower()
            com.classification = "subcommittee"
        elif com_type != "Standing Committees":
            com.extras['Committee Type'] = com_type.lower()
        """
        com.extras["Committee Type"] = com_type.lower()

        source = URL(detail_link)
        # print(source)
        # if source == "https://sbp.senate.ca.gov":
        #    return com
        # else:
        return CommitteeDetail(com, source=source)
'''


class CommitteeDetail(HtmlListPage):
    selector = XPath(
        "//a[(contains(@href, '/sd') or "
        "contains(@href, 'assembly.ca.gov/a')) and "
        "(starts-with(text(), 'Senator') or "
        "starts-with(text(), 'Assembly Member'))]/text()"
    )

    def process_item(self, item):
        com = self.input
        # print(item)

        (mem_name, mem_role) = re.search(
            r"""(?ux)
                ^(?:Senator|Assembly\sMember)\s  # Legislator title
                (.+?)  # Capture the senator's full name
                (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                (?:\s\([RD]\))?  # There may be a party affiliation
                \s*$
                """,
            item,
        ).groups()

        com.add_member(mem_name, role=mem_role if mem_role else "member")

        # if not org._related:
        #    self.warning("No members found for committee {}".format(comm_name))

        return com


class JointcommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        xpaths = [
            "//div/p/a[(contains(text(), 'Senator') or contains(text(), 'Assembly Member'))]/text()",
            '//tbody/tr/td/a[(contains(@href, "/sd") or '
            'contains(@href, "assembly.ca.gov/a"))]/text()',
            "//div/p[@class = 'caption']/text()",
        ]
        for type in xpaths:
            try:
                members = XPath(type).match(self.root)
            except SelectorError:
                continue

        print(members)

        # Special case of members list being presented in text blob.

        # Separate senate membership from assembly membership.
        # This should strip the header from assembly membership
        # string automatically.
        # delimiter = "Assembly Membership:\n"
        # senate_members, delimiter, assembly_members = members.partition(
        #    delimiter
        # )

        # Strip header from senate membership string.
        # senate_members = senate_members.replace("Senate Membership:\n", "")

        # Clean membership strings.
        # senate_members = senate_members.strip()
        # assembly_members = assembly_members.strip()

        # Parse membership strings into lists.
        # senate_members = senate_members.split("\n")
        # assembly_members = assembly_members.split("\n")

        # members = senate_members + assembly_members
        for member in members:
            if not member.strip():
                continue

            (mem_name, mem_role) = re.search(
                r"""(?ux)
                    (.+?)  # Capture the senator's full name
                    (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                    \s*$
                    """,
                member,
            ).groups()
            com.add_member(mem_name, role=mem_role if mem_role else "member")

        return com


class SubcommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        # print(self.data)
        parent_name = XPath('//div[@class="banner-sitename"]/a/text()').match_one(
            self.root
        )
        # print(parent_name)
        com.parent = parent_name
        return com


class CommitteeList(HtmlListPage):
    source = URL("http://senate.ca.gov/committees")

    selector = XPath("//h2/../following-sibling::div//a")

    def process_item(self, item):
        # Retrieve index list of committees.
        # doc = self.lxmlize(url)

        # Get the text of the committee link, which should be the name of
        # the committee.
        # print(item.getparent().get("class"))
        comm_name = XPath("text()").match_one(item)
        if comm_name in ["Teleconference How-To Information", "Legislative Process"]:
            self.skip()

        # (comm_name,) = committee.xpath("text())")

        comm_url = XPath("@href").match_one(item)
        # (comm_url,) = committee.xpath("@href")
        # comm_doc = self.lxmlize(comm_url)

        if comm_name.startswith("Joint"):
            com = ScrapeCommittee(
                name=comm_name, classification="committee", parent="legislature"
            )
            com.add_source(self.source.url)
            com.add_source(comm_url)
            com.add_link(comm_url, note="homepage")
            return JointcommitteeDetail(com, source=URL(comm_url))
        elif comm_name.startswith("Subcommittee"):
            self.skip()
            # print(parent_name)
            # (parent_name,) = comm_doc.xpath(
            #    '//div[@class="banner-sitename"]/a/text()'
            # )
            # (subcom_name,) = comm_doc.xpath('//h1[@class="title"]/text()')
            com = ScrapeCommittee(
                name=comm_name, classification="subcommittee", parent=""
            )
            com.add_source(self.source.url)
            com.add_source(comm_url)
            com.add_link(comm_url, note="homepage")
            return SubcommitteeDetail(com, source=URL(comm_url))

        self.skip()
        com = ScrapeCommittee(
            name=comm_name, classification="committee", parent="upper"
        )
        com.add_source(self.source.url)
        com.add_source(comm_url)
        com.add_link(comm_url, note="homepage")

        return CommitteeDetail(com, source=URL(comm_url))

        """
        # Special case of members list being presented in text blob.
        member_blob = comm_doc.xpath(
            'string(//div[contains(@class, "field-item") and '
            'starts-with(text(), "Senate Membership:")][1]/text()[1])'
        )

        if member_blob:
            # Separate senate membership from assembly membership.
            # This should strip the header from assembly membership
            # string automatically.
            delimiter = "Assembly Membership:\n"
            senate_members, delimiter, assembly_members = member_blob.partition(
                delimiter
            )

            # Strip header from senate membership string.
            senate_members = senate_members.replace("Senate Membership:\n", "")

            # Clean membership strings.
            senate_members = senate_members.strip()
            assembly_members = assembly_members.strip()

            # Parse membership strings into lists.
            senate_members = senate_members.split("\n")
            assembly_members = assembly_members.split("\n")

            members = senate_members + assembly_members
        # Typical membership list format.
        else:
            members = comm_doc.xpath(
                '//a[(contains(@href, "/sd") or '
                'contains(@href, "assembly.ca.gov/a")) and '
                '(starts-with(text(), "Senator") or '
                'starts-with(text(), "Assembly Member"))]/text()'
            )

        for member in members:
            if not member.strip():
                continue

        """

        # (mem_name, mem_role) = re.search(
        #     r"""(?ux)
        #         ^(?:Senator|Assembly\sMember)\s  # Legislator title
        #         (.+?)  # Capture the senator's full name
        #         (?:\s\((.{2,}?)\))?  # There may be role in parentheses
        #         (?:\s\([RD]\))?  # There may be a party affiliation
        #         \s*$
        #         """,
        #     member,
        # ).groups()
        # org.add_member(mem_name, role=mem_role if mem_role else "member")

        """
        if not org._related:
            self.warning("No members found for committee {}".format(comm_name))

        yield org
        """
