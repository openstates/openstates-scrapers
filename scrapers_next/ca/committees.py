from spatula import HtmlListPage, URL, XPath, CSS, HtmlPage, SelectorError
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


class CommitteeDetail(HtmlPage):
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

            com.add_member(mem_name, role=mem_role if mem_role else "member")

        return com


class JointcommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        xpaths = [
            "//div/p/a[(contains(text(), 'Senator') or contains(text(), 'Assembly Member'))]/text()",
            '//tbody/tr/td/a[(contains(@href, "/sd") or '
            'contains(@href, "assembly.ca.gov/a"))]/text()',
            "//p[@class = 'caption']/text()",
        ]

        page_type = 0
        for xpath in xpaths:
            page_type += 1
            try:
                members = XPath(xpath).match(self.root)
                break
            except SelectorError:
                continue
            print(page_type)

        # print(members)
        if page_type == 3:
            member_1 = members[0] + " " + members[1]
            member_2 = members[2] + " " + members[3]
            members = [member_1, member_2]

        # print(members)

        for member in members:
            # if type(member) != str:
            #    member = member.text_content()
            # print(member)
            # if not member.strip():
            #    continue

            member = re.sub(r"(Senator\s|Assembly\sMember\s)", "", member)
            # print(member)

            """
            if re.search(r",\n", member):
                mem_name, mem_role = member.split(",\n")
                mem_name = mem_name.strip()
                mem_role = mem_role.strip()
            """
            # print(member)
            if re.search(r"\n", member):
                mem_name, mem_role = member.split("\n")
                mem_name = mem_name.strip().rstrip(",")
                mem_role = mem_role.split("of the")[0]
                mem_role = mem_role.strip()
            elif re.search(r",\s", member):
                mem_name, mem_role = member.split(",")
                mem_name = mem_name.strip()
                mem_role = mem_role.strip()
            elif re.search(r"\(", member):
                mem_name, mem_role = member.split(" (")
                mem_role = mem_role.rstrip(")")
            else:
                mem_name = member
                mem_role = "member"

            print(mem_name, mem_role)
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


class StandingCommitteeDetail(HtmlPage):
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
            if not mem or re.search(r"Assemblymember", mem):
                mem = member.getnext().text_content()
                # print(mem)

            mem = re.sub(r"(Senator\s|Assembly\sMember\s)", "", mem)
            mem = re.sub(r"Image\sof\s", "", mem)
            # print(mem)
            if re.search(r",\s(V|C|\()", mem):
                # x = re.split(r",\s(V|C|\()", mem)
                # print(x)
                # mem_name, mem_role = re.split(r",\s(V|C|\()", mem)
                mem_name, mem_role = mem.split(",")
                mem_name = mem_name.strip()
                mem_role = mem_role.strip()
                if "(" in mem_role:
                    mem_role = mem_role.lstrip("(").rstrip(")")
                if "of the" in mem_role:
                    mem_role = mem_role.split("of the")[0].strip()
                if mem_name == "Kevin Kiley":
                    mem_role = "Vice Chair"
                # print(mem_name, mem_role)
            elif re.search(r"\s\((V|C)", mem):
                mem_name, mem_role = mem.split("(")
                mem_name = mem_name.strip()
                mem_role = mem_role.rstrip(")").strip()
                # print(mem_name, mem_role)
            elif re.search(r"\n", mem):
                mem_name, mem_role = mem.split("\n")
                mem_name = mem_name.strip()
                mem_role = mem_role.strip().split("of the")[0].strip()
            elif mem_num == 0:
                mem_name = mem.strip()
                mem_role = "Chair"
                # print(member, "chair not listed")
            else:
                mem_name = mem.strip()
                mem_role = "Vice Chair"
                # print(member, "vice chair not listed")
            mem_num += 1

            print(mem_name, mem_role)
            com.add_member(mem_name, role=mem_role if mem_role else "member")

        return com


class SpecialCommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input

        members = XPath("//tr/td/a[contains(@href, 'assembly.ca.gov')]").match(
            self.root
        )
        for member in members:
            mem_name = member.text_content()
            if re.search(r"\s\(", mem_name):
                mem_name, mem_role = mem_name.split("(")
                mem_name = mem_name.strip()
                mem_role = mem_role.rstrip(")")
                print(mem_name, mem_role)
            else:
                print(mem_name)
            com.add_member(mem_name, role=mem_role if mem_role else "member")

        return com


class AssemblyCommitteeList(HtmlListPage):
    source = URL("https://www.assembly.ca.gov/committees")

    selector = CSS("div .block.block-views ul li", num_items=98)

    def process_item(self, item):
        comm_name = CSS("a").match_one(item).text_content()
        comm_url = CSS("a").match_one(item).get("href")

        to_skip = ["Sub Committees", "Joint Committees"]

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
            in to_skip
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
            == "Special Committees"
        ):
            self.skip()
            com = ScrapeCommittee(
                name=comm_name, classification="committee", parent="lower"
            )
            com.add_source(self.source.url)
            com.add_source(comm_url)
            com.add_link(comm_url, note="homepage")
            return SpecialCommitteeDetail(com, source=URL(comm_url))
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
            == "Select Committees"
        ):
            to_skip = [
                "Census",
                "Coastal Protection and Access to Natural Resources",
                "Emerging Technologies and Innovation",
                "Intellectual and Developmental Disabilities",
                "Non-Profit Sector",
                "Police Reform",
                "Sea Level Rise and the California Economy",
                "Status of Boys and Men of Color",
            ]
            if comm_name in to_skip:
                # self.skip()
                com = ScrapeCommittee(
                    name=comm_name, classification="committee", parent="lower"
                )
                com.add_source(self.source.url)
                com.add_source(comm_url)
                com.add_link(comm_url, note="homepage")
                return StandingCommitteeDetail(com, source=URL(comm_url))
            self.skip()
            com = ScrapeCommittee(
                name=comm_name, classification="committee", parent="lower"
            )
            com.add_source(self.source.url)
            com.add_source(comm_url)
            com.add_link(comm_url, note="homepage")
            return SpecialCommitteeDetail(com, source=URL(comm_url))
        # Just standing committees for now
        self.skip()
        com = ScrapeCommittee(
            name=comm_name, classification="committee", parent="lower"
        )
        com.add_source(self.source.url)
        com.add_source(comm_url)
        com.add_link(comm_url, note="homepage")
        return StandingCommitteeDetail(com, source=URL(comm_url))


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
            # self.skip()
            com = ScrapeCommittee(
                name=comm_name, classification="committee", parent="legislature"
            )
            com.add_source(self.source.url)
            com.add_source(comm_url)
            com.add_link(comm_url, note="homepage")
            return JointcommitteeDetail(com, source=URL(comm_url))
        elif comm_name.startswith("Subcommittee"):
            # self.skip()
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

        # self.skip()
        com = ScrapeCommittee(
            name=comm_name, classification="committee", parent="upper"
        )
        com.add_source(self.source.url)
        com.add_source(comm_url)
        com.add_link(comm_url, note="homepage")

        return CommitteeDetail(com, source=URL(comm_url))
