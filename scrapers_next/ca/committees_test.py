from spatula import HtmlListPage, URL, XPath, CSS, HtmlPage, SelectorError
from openstates.models import ScrapeCommittee
import re


class ChooseType(HtmlPage):
    def process_page(self):

        # this link was being considered type one, but should be type four
        if self.source.url == "https://ajed.assembly.ca.gov":
            # return None
            return TypeFour(self.input, source=self.source)

        xpaths = {
            "type_one": "//div/p/a[(contains(text(), 'Senator') or contains(text(), 'Assembly Member'))]/text()",
            "type_two": "//a[(contains(@href, '/sd') or "
            "contains(@href, 'assembly.ca.gov/a')) and "
            "(starts-with(text(), 'Senator') or "
            "starts-with(text(), 'Assembly Member'))]/text()",
            "type_three": '//tbody/tr/td/a[(contains(@href, "/sd") or '
            'contains(@href, "assembly.ca.gov/a"))]//text()',
            "type_four": "//p[@class = 'caption']/text()",
        }

        for page_type, xpath in xpaths.items():
            try:
                XPath(xpath).match(self.root)
                break
            except SelectorError:
                continue

        if page_type == "type_one":
            # return None
            return TypeOne(self.input, source=self.source)
        elif page_type == "type_two":
            # return None
            return TypeTwo(self.input, source=self.source)
        elif page_type == "type_three":
            # return None
            return TypeThree(self.input, source=self.source)
        else:
            # return None
            return TypeFour(self.input, source=self.source)


class TypeOne(HtmlPage):
    """
    Type One pages are usually formatted with a red background.
    There are 4 possible formats that are considered Type One:
    1. Senator Name (role)
    2. Senator Name, role
    3. role, Senator Name (D|R)
    4. Senator Name (D|R)

    43 (out of 51 total) Senate committees are considered Type One (see links below).
    https://sagri.senate.ca.gov (40 pages have this format)
    https://fisheries.legislature.ca.gov/ (2 pages have this format)
    https://selc.senate.ca.gov (1 page has this format)

    0 (out of 89 total) Assembly committees are considered Type One.
    """

    def process_page(self):
        com = self.input
        members = XPath(
            "//div/p/a[(contains(text(), 'Senator') or contains(text(), 'Assembly Member'))]/text()"
        ).match(self.root)

        for member in members:
            member = re.sub(r"(Senator\s|Assembly\sMember\s)", "", member)

            if re.search(r"\((D|R)\)", member):
                mem_name, _ = member.split("(")
                if re.search(r",\s", mem_name):
                    mem_role, mem_name = mem_name.split(",")
                else:
                    mem_role = "member"
            elif re.search(r",\s", member):
                # print("FORMAT 2")
                mem_name, mem_role = member.split(",")
                # print(mem_role)
                # print(mem_name)
                # mem_name, _ = mem_name.split("(")
            elif re.search(r"\(", member):
                # print("FORMAT 1")
                mem_name, mem_role = member.split("(")
                mem_role = mem_role.rstrip(")")
            else:
                mem_name = member
                mem_role = "member"

            print(mem_name.strip(), mem_role.strip())
            com.add_member(mem_name.strip(), role=mem_role.strip())

        # print("TYPE ONE")
        return com


class TypeTwo(HtmlPage):
    """
    Type Two pages look very similar to Type One.
    Type Two pages are usually formatted with a red background.
    Their html, however, differs slightly from that of Type One.

    There are 2 possible formats that are considered Type One:
    1. Senator Name (role) (D|R)
    2. Senator Name (role)

    4 (out of 51 total) Senate committees are considered Type Two (see links below).
    https://sedn.senate.ca.gov (has 'table' 'tbody' 'tr' 'td' elements between div and p elements)
    https://sgf.senate.ca.gov (has a 'center' element between div and p elements)
    https://sjud.senate.ca.gov (has 'h4' element instead of p element)
    https://census.senate.ca.gov/ (has 'ul' and 'li' elements instead of p element)

    0 (out of 89 total) Assembly committees are considered Type Two.
    """

    def process_page(self):
        com = self.input
        members = XPath(
            "//a[(contains(@href, '/sd') or "
            "contains(@href, 'assembly.ca.gov/a')) and "
            "(starts-with(text(), 'Senator') or "
            "starts-with(text(), 'Assembly Member'))]/text()"
        ).match(self.root)
        # print(item)

        for member in members:
            (mem_name, mem_role) = re.search(
                r"""(?ux)
                    ^(?:Senator|Assembly\sMember)\s  # Legislator title
                    (.+?)  # Capture the senator's full name
                    (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                    (?:\s\([RD]\))?  # There may be a party affiliation
                    \s*$
                    """,
                member,
            ).groups()

            if mem_role:
                print(mem_name.strip(), mem_role.strip())
            else:
                print(mem_name.strip(), "member")

            com.add_member(
                mem_name.strip(), role=mem_role.strip() if mem_role else "member"
            )

        # print("TYPE TWO")
        return com


class TypeThree(HtmlPage):
    """
    Type Three pages are usually formatted with a green background.

    The format is:
    1. Name (role)

    1 (out of 51 total) Senate committees are considered Type Three (see link below).
    http://assembly.ca.gov/fairsallocation

    48 (out of 89 total) Assembly committees are considered Type Three (see links below).
    https://abgt.assembly.ca.gov/sub1healthandhumanservices
    https://assembly.ca.gov/olympicgames
    https://assembly.ca.gov/cmtewine
    https://assembly.ca.gov/specialcmtelegethics
    """

    def process_page(self):
        com = self.input
        members = XPath(
            "//tbody/tr/td/a[(contains(@href, '/sd') or contains(@href, 'assembly.ca.gov/a'))]//text()"
        ).match(self.root)
        # print(item)

        for member in members:
            (mem_name, mem_role) = re.search(
                r"""(?ux)
                    (.+?)  # Capture the senator's full name
                    (?:\s\((.{2,}?)\))?  # There may be role in parentheses
                    \s*$
                    """,
                member,
            ).groups()

            if mem_role:
                print(mem_name.strip(), mem_role.strip())
            else:
                print(mem_name.strip(), "member")

            com.add_member(
                mem_name.strip(), role=mem_role.strip() if mem_role else "member"
            )

        # print("TYPE THREE")
        return com


class TypeFour(HtmlPage):
    """
    Type Four pages are usually formatted with a green background.

    The format is:
    Name,
    role (on a new line)

    3 (out of 51 total) Senate committees are considered Type Four (see links below).
    https://jtrules.legislature.ca.gov/
    https://legaudit.assembly.ca.gov/
    https://climatechangepolicies.legislature.ca.gov/

    41 (our of 89) Assembly committees are considered Type Four (see links below).
    https://aaar.assembly.ca.gov
    https://awpw.assembly.ca.gov
    https://jtlegbudget.legislature.ca.gov/sublegislativeanalyst
    https://census.assembly.ca.gov/
    https://scbmc.assembly.ca.gov
    https://ajed.assembly.ca.gov/
    """

    def process_page(self):
        com = self.input

        try:
            members = CSS("div.chair img").match(self.root)
        except SelectorError:
            members = [CSS("p img").match(self.root)[0]]

        # print(members)
        mem_num = 0
        for member in members:
            mem = member.get("alt")
            # print(mem)

            # this link has bad formatting for the img alt (use p text instead)
            # https://aesm.assembly.ca.gov/
            if not mem or re.search(r"Assemblymember", mem):
                mem = member.getnext().text_content()
                # print(mem)

            # these links also has bad formatting
            # https://idd.assembly.ca.gov name is Mark Stone instead of Jim Frazier
            # https://policereform.assembly.ca.gov/ name is Gipson instead of Mike A. Gipson
            if self.source.url in [
                "https://idd.assembly.ca.gov",
                "https://policereform.assembly.ca.gov/",
            ]:
                mem = member.getparent().getnext().text_content()

            mem = re.sub(r"(Senator\s|Assembly\sMember\s)", "", mem)
            mem = re.sub(r"Image\sof\s", "", mem)
            # print(mem)
            if re.search(r",\s(V|C|\()", mem):
                # x = re.split(r",\s(V|C|\()", mem)
                # print(x)
                # mem_name, mem_role = re.split(r",\s(V|C|\()", mem)
                member_info = mem.split(",")

                # some names have , Jr. or , Sr.
                # this handles an extra comma
                if len(member_info) == 2:
                    mem_name = member_info[0]
                    mem_role = member_info[1]
                elif len(member_info) == 3:
                    mem_name = member_info[0]
                    mem_name += member_info[1]
                    mem_role = member_info[2]

                # mem_name = mem_name.strip()
                # mem_role = mem_role.strip()
                if "(" in mem_role:
                    mem_role = mem_role.strip().lstrip("(").rstrip(")")
                if "of the" in mem_role:
                    mem_role = mem_role.split("of the")[0]
                if mem_name == "Kevin Kiley":
                    mem_role = "Vice Chair"
                # print(mem_name, mem_role)
            elif re.search(r"\s\((V|C)", mem):
                mem_name, mem_role = mem.split("(")
                # mem_name = mem_name.strip()
                mem_role = mem_role.rstrip(")")
                # print(mem_name, mem_role)
            elif re.search(r"\n", mem):
                mem_name, mem_role = mem.split("\n")
                # mem_name = mem_name.strip()
                mem_role = mem_role.split("of the")[0]
            elif mem_num == 0:
                mem_name = mem.strip()
                mem_role = "Chair"
                # print(member, "chair not listed")
            else:
                mem_name = mem.strip()
                mem_role = "Vice Chair"
                # print(member, "vice chair not listed")
            mem_num += 1

            print(mem_name.strip(), mem_role.strip())
            com.add_member(
                mem_name.strip(), role=mem_role.strip() if mem_role else "member"
            )

        # print("TYPE FOUR")
        return com


class SenateCommitteeList(HtmlListPage):
    source = URL("http://senate.ca.gov/committees")

    selector = XPath("//h2/../following-sibling::div//a")

    def process_item(self, item):
        comm_name = XPath("text()").match_one(item)
        if comm_name in ["Teleconference How-To Information", "Legislative Process"]:
            self.skip()

        comm_url = XPath("@href").match_one(item)

        if comm_name.startswith("Joint"):
            # self.skip()
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
            )
            # print(parent_comm)
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
        com.add_source(self.source.url)
        com.add_source(comm_url)
        com.add_link(comm_url, note="homepage")
        return ChooseType(com, source=URL(comm_url))


class AssemblyCommitteeList(HtmlListPage):
    source = URL("https://www.assembly.ca.gov/committees")

    selector = CSS("div .block.block-views ul li", num_items=98)

    def process_item(self, item):
        comm_name = CSS("a").match_one(item).text_content()
        comm_url = CSS("a").match_one(item).get("href")

        # "https://jtlegbudget.legislature.ca.gov/sublegislativeanalyst" has no members
        if comm_url == "https://jtlegbudget.legislature.ca.gov/sublegislativeanalyst":
            self.skip()

        if (
            item.getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .text_content()
            .split("\n")[2]
            .lstrip("\t")
            == "Joint Committees"
        ):
            self.skip()
        elif (
            item.getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .text_content()
            .split("\n")[2]
            .lstrip("\t")
            == "Sub Committees"
        ):
            # self.skip()
            parent_comm = item.getparent().getparent().getchildren()[0].text_content()
            # print(parent_comm)
            com = ScrapeCommittee(
                name=comm_name,
                classification="subcommittee",
                chamber="lower",
                parent=parent_comm,
            )
        else:
            # self.skip()
            com = ScrapeCommittee(
                name=comm_name, classification="committee", chamber="lower"
            )
        com.add_source(self.source.url)
        com.add_source(comm_url)
        com.add_link(comm_url, note="homepage")
        return ChooseType(com, source=URL(comm_url))
