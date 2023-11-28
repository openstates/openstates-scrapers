from spatula import HtmlListPage, URL, XPath, CSS, HtmlPage, SkipItem
from openstates.models import ScrapeCommittee
import re


member_name_role_re = re.compile(r"(.+)\((.+)\)")
chair_name_re = re.compile(r"(Senator\s|Assembly\sMember\s*)(.+[a-z])")
chair_title_re = re.compile(r"(.*Chair)")
vacancy_re = re.compile(r"vacant|vacancy|vacancies")
members_check_re = re.compile(r"(Senator|Assemblymember)\s+([A-Z].+)")


class CommMembership(HtmlPage):
    example_source = "https://aaar.assembly.ca.gov/membersstaff"

    def process_page(self):
        committee = self.input

        sen_page_check = self.root.xpath(".//div[@class='banner senate-red col-xs-12']")

        # Handles senate page type format
        if sen_page_check:
            members = []
            a_tags_text_list = self.root.xpath(
                ".//div[@class='field-item even']//a//text()"
            )
            for text in a_tags_text_list:
                member_match = members_check_re.search(text)
                if member_match:
                    member_text = member_match.groups()[1]
                    members.append(member_text)

        # Handles all other page types
        else:
            members = self.root.xpath(".//table//tbody//tr//td[1]//text()")

            # At least two pages has some/all members in table head, not table body
            table_head_members = self.root.xpath(".//thead//td[1]//text()")
            if table_head_members:
                members += table_head_members

        if members:
            for member in members:
                has_role = member_name_role_re.search(member)
                if has_role:
                    name, role = [x.strip() for x in has_role.groups()]
                else:
                    name, role = member.strip(), "Member"

                # Skips rows containing vacant committee seat
                if not name or vacancy_re.search(name.lower()):
                    continue
                committee.add_member(name=name, role=role)

        else:
            raise SkipItem("No membership listed")

        return committee


class CommDetails(HtmlPage):
    example_source = "https://aaar.assembly.ca.gov/"

    def process_page(self):
        committee = self.input

        members_staff_link = self.root.xpath(
            ".//a[contains" "(text(), 'Members & Staff')]"
        )
        members_link = self.root.xpath(
            ".//div[@id='center_box1']//"
            "li//a[contains("
            "text(),'Committee Membership')]"
        )
        members_table = self.root.xpath(
            ".//table//thead//tr//th[contains" "(text(), 'Committee Members')]"
        )
        chairs = self.root.xpath(".//div[@class='chair']")
        sen_page_check = self.root.xpath(
            ".//div[@class=" "'banner senate-red col-xs-12']"
        )

        # Case 1: details page links to membership page in navigation div
        if members_staff_link:
            source = members_staff_link[0].get("href")
            return CommMembership(committee, source=source)

        # Case 2: details page has membership page nav link in div lower down
        elif members_link:
            source = members_link[0].get("href")
            return CommMembership(committee, source=source)

        # Case 3: details page itself has committee membership
        elif members_table or sen_page_check:
            return CommMembership(committee, source=self.source.url)

        # Case 4: no list of members linked or on page, but chairs on page
        elif chairs:
            for chair in chairs:
                chair_and_title = chair.text_content().split("\n")
                name, role = [x for x in chair_and_title if len(x)]
                name = chair_name_re.search(name).groups()[1]
                role = chair_title_re.search(role).group()
                committee.add_member(name=name, role=role)

        # Case 5: page does not fit known formats, or membership not on site
        else:
            raise SkipItem("No membership listed")

        return committee


class SenateCommitteeList(HtmlListPage):
    source = URL("http://senate.ca.gov/committees")
    selector = XPath("//h2/../following-sibling::div//a")

    def process_item(self, item):
        comm_name = XPath("text()").match_one(item)
        if comm_name in ["Teleconference How-To Information", "Legislative Process"]:
            self.skip()

        comm_url = XPath("@href").match_one(item)

        if comm_name.startswith("Joint"):
            com = ScrapeCommittee(
                name=comm_name, classification="committee", chamber="legislature"
            )
        elif comm_name.startswith("Subcommittee"):
            parent_comm = (
                item.getparent()
                .getparent()
                .getparent()
                .getparent()
                .getchildren()[0]
                .text_content()
                .strip()
            )
            com = ScrapeCommittee(
                name=comm_name,
                classification="subcommittee",
                chamber="upper",
                parent=parent_comm,
            )
        else:
            com = ScrapeCommittee(
                name=comm_name, classification="committee", chamber="upper"
            )

        com.add_source(self.source.url, note="Committee List Page")
        com.add_source(comm_url, note="Committee Detail Page")
        com.add_link(comm_url, note="homepage")

        return CommDetails(com, source=URL(comm_url))


class AssemblyCommitteeList(HtmlListPage):
    source = URL("https://www.assembly.ca.gov/committees")
    selector = XPath(".//div[@class='views-field views-field-title']")

    def process_item(self, item):
        comm_name = CSS("a").match_one(item).text_content()
        comm_url = CSS("a").match_one(item).get("href")

        # Joint Committees are being skipped to avoid duplicates
        #  because they are grabbed during SenateCommitteeList()
        if "joint" in comm_name.lower():
            self.skip("Joint committees retrieved by SenateCommitteeList() object")

        if comm_name.startswith("Subcommittee"):
            classification = "subcommittee"
            parent_comm = (
                item.getparent()
                .getparent()
                .getparent()
                .getchildren()[0]
                .text_content()
                .strip()
            )
        else:
            self.skip()
            classification = "committee"
            parent_comm = None

        com = ScrapeCommittee(
            name=comm_name,
            classification=classification,
            chamber="lower",
            parent=parent_comm,
        )

        com.add_source(self.source.url, note="Committee List Page")
        com.add_source(comm_url, note="Committee Detail Page")
        com.add_link(comm_url, note="homepage")

        return CommDetails(com, source=URL(comm_url))
