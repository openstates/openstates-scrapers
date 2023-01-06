from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError, SkipItem
from openstates.models import ScrapeCommittee
import time


class MemberDetail(HtmlPage):
    def process_page(self):
        com = self.input[0]
        role = self.input[1]
        try:
            mem_name = CSS("#mainC > h3").match(self.root)
        except SelectorError:
            return None

        if "Delegate" in mem_name[0].text:
            cleaned_name = mem_name[0].text.split("Delegate")[1].strip()
        else:
            cleaned_name = mem_name[0].text.split("Senator")[1].strip()

        if cleaned_name is not None:
            com.add_member(cleaned_name, role)

        # setattr(MemberDetail, "name", cleaned_name)

        return com


class CommitteeDetail(HtmlListPage):
    def process_page(self):
        com = self.input
        member_items = CSS("p a").match(self.root)
        members = [i.text for i in member_items]

        for i in range(len(members)):
            if (
                "Agendas" in members[i]
                or "Committee" in members[i]
                or "Comments" in members[i]
            ):
                raise SkipItem("not a member")

            if "(Chair)" in members[i]:
                role = "Chair"

            elif "(Vice Chair)" in members[i]:
                role = "Vice Chair"

            else:
                role = "Member"

            detail_link = member_items[i].get("href")
            time.sleep(2)
            yield MemberDetail([com, role], source=URL(detail_link, timeout=120))
            # print(list(com))

            # print(cleaned_name.name)

            # if cleaned_name is not None:
            # ADD THIS TO COMMITTEE DETAIL
            # com.add_member(cleaned_name, role)

        return com


class FindSubCommittees(HtmlListPage):

    selector = CSS("#mainC > ul:nth-child(12) > li a")

    def process_item(self, item):
        try:
            comm_name = item.text

        except SelectorError:
            raise SkipItem("no subcommittees")

        chamber_text = item.getparent().getparent().getparent().getchildren()[1].text
        if "house" in chamber_text.lower():
            chamber = "lower"
            parent_comm = chamber_text.split("House")[1].strip()
        else:
            chamber = "upper"
            parent_comm = chamber_text.split("Senate")[1].strip()

        com = ScrapeCommittee(
            name=comm_name,
            classification="subcommittee",
            chamber=chamber,
            parent=parent_comm,
        )
        print(comm_name, parent_comm, "// Comm and Parent")

        detail_link = item.get("href")
        com.add_source(self.source.url, note="homepage")
        com.add_source(detail_link)

        return CommitteeDetail(com, source=URL(detail_link, timeout=120))


class CommitteeList(HtmlListPage):
    source = "https://lis.virginia.gov/231/com/COM.HTM"
    selector = CSS(".linkSect a")

    def process_item(self, item):
        comm_name = item.text
        print(comm_name)
        # both senate and house committees are listed on one page, so this isolates which is which
        chamber_text = item.getparent().getparent().getparent().getchildren()[0].text
        if "HOUSE" in chamber_text:
            chamber = "lower"
        else:
            chamber = "upper"

        com = ScrapeCommittee(
            name=comm_name,
            classification="committee",
            chamber=chamber,
        )

        detail_link = item.get("href")
        com.add_source(self.source.url, note="homepage")
        com.add_source(detail_link)
        time.sleep(3)

        return CommitteeDetail(com, source=URL(detail_link, timeout=120))


class SubCommitteeList(HtmlListPage):
    source = "https://lis.virginia.gov/231/com/COM.HTM"
    selector = CSS(".linkSect a")

    def process_item(self, item):
        chamber_text = item.getparent().getparent().getparent().getchildren()[0].text
        comm_name = item.text

        # this is hacky but I couldn't figure out another way to ignore a lack of subcommittees
        if "SENATE" in chamber_text:
            if comm_name == "Transportation":
                raise SkipItem("no subcommittees")
            if comm_name == "Rules":
                return

        detail_link = item.get("href")
        time.sleep(2)
        return FindSubCommittees(source=URL(detail_link, timeout=120))
