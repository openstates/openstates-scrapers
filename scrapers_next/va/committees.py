from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError, SkipItem
from openstates.models import ScrapeCommittee
import time

"""
The data that resulted from this scraper is a little weak (some subcommittee information is missing).

The source that was used for this scraper isn't the best, which is why the code has to sleep so much.
Going forward, we should try and find a more stable source for VA committee data.
"""

# VA lists the full names of committee members on individual separate pages
# MemberDetail grabs a member's full name from their specific page


class MemberDetail(HtmlPage):
    def process_page(self):
        if len(self.input) > 2:
            raise ValueError("please provide only committee object and role")

        com = self.input[0]
        role = self.input[1]
        try:
            mem_name = CSS("#mainC > h3").match(self.root)
        except SelectorError:
            return com

        if "Delegate" in mem_name[0].text:
            cleaned_name = mem_name[0].text.split("Delegate")[1].strip()
        elif "Senator" in mem_name[0].text:
            cleaned_name = mem_name[0].text.split("Senator")[1].strip()
        else:
            cleaned_name = mem_name[0].text.strip()

        if cleaned_name:
            com.add_member(cleaned_name, role)

        return com


# grabs committee details (other than members' full name)
class CommitteeDetail(HtmlListPage):
    def process_page(self):
        com = self.input
        try:
            member_items = CSS("p a").match(self.root)
        except SelectorError:
            com_name = list(com)[0][1]
            print_str = "cannot access " + com_name + " committee details"
            raise SkipItem(print_str)

        members = [i.text for i in member_items]

        for i in range(len(members)):
            if (
                "Agendas" in members[i]
                or "Committee" in members[i]
                or "Comments" in members[i]
            ):
                continue

            if "(Chair)" in members[i]:
                role = "Chair"

            elif "(Co-Chair)" in members[i]:
                role = "Co-Chair"

            elif "(Vice Chair)" in members[i]:
                role = "Vice Chair"

            else:
                role = "Member"

            time.sleep(40)
            detail_link = member_items[i].get("href")
            # .do_scrape() allows us to get information from MemberDetail without
            # returning/writing a com object to disk
            com = [
                i
                for i in MemberDetail(
                    [com, role], source=URL(detail_link, timeout=120)
                ).do_scrape()
            ][0]

        return com


class FindSubCommittees(HtmlListPage):
    try:
        selector = CSS("#mainC > ul:nth-child(12) > li a")
    except SelectorError:
        raise SkipItem("cannot access subcommittees")

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

        detail_link = item.get("href")
        com.add_source(self.source.url, note="homepage")
        com.add_source(detail_link)

        time.sleep(40)

        return CommitteeDetail(com, source=URL(detail_link, timeout=120))


class CommitteeList(HtmlListPage):
    source = "https://lis.virginia.gov/241/com/COM.HTM"
    selector = CSS(".linkSect a")

    def process_item(self, item):
        comm_name = item.text
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

        time.sleep(40)

        return CommitteeDetail(com, source=URL(detail_link, timeout=120, retries=3))


class SubCommitteeList(HtmlListPage):
    source = "https://lis.virginia.gov/241/com/COM.HTM"
    selector = CSS(".linkSect a")

    def process_item(self, item):
        chamber_text = item.getparent().getparent().getparent().getchildren()[0].text
        comm_name = item.text

        # this is hacky but I couldn't figure out another way to ignore a lack of subcommittees
        if "SENATE" in chamber_text:
            if comm_name == "Transportation":
                raise SkipItem("no subcommittees")
            if comm_name == "Rules":
                raise SkipItem("no subcommittees")

        detail_link = item.get("href")
        time.sleep(40)
        return FindSubCommittees(source=URL(detail_link, timeout=120))
