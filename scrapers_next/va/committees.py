from spatula import URL, CSS, HtmlListPage, HtmlPage, SkipItem, MissingSourceError
from openstates.models import ScrapeCommittee
import requests
from lxml import html
import time
import re
import logging


class CommitteeDetail:
    def __init__(self, committee, source):
        self.com = committee
        self.source = source

    def process_page(self):
        response = requests.get(self.source, timeout=120)
        logging.log(logging.INFO, f" fetching {self.com.name} details from {self.source}")
        if response.status_code != 200:
            raise SkipItem(f"Cannot access {self.com.name} committee details")

        tree = html.fromstring(response.content)

        # Extract member details
        member_items = tree.cssselect("p a")
        members = [i.text_content() for i in member_items]

        for i in range(len(members)):
            member_text = members[i].strip()
            if (
                "Agendas" in member_text
                or "Committee" in member_text
                or "Comments" in member_text
            ):
                continue

            if "(Chair)" in member_text:
                role = "Chair"
            elif "(Co-Chair)" in member_text:
                role = "Co-Chair"
            elif "(Vice Chair)" in member_text:
                role = "Vice Chair"
            else:
                role = "Member"

            detail_link = member_items[i].get("href")
            # Fetch and process member details
            partial_name = member_items[i].text_content().replace(",", "").strip()
            if detail_link:
                self.process_member(partial_name, detail_link, role)

        return self.com

    def process_member(self, partial_name, member_url, role):
        member_pattern = re.compile(r"(?:Delegate |Senator )(.+)")  # Regex pattern to match and extract the name

        # Filter out non-HTTP/HTTPS URLs
        if not member_url.startswith("http"):
            # Convert relative URLs to absolute
            if member_url.startswith("/"):
                member_url = f"https://lis.virginia.gov{member_url}"
            else:
                # Skip non-HTTP URLs like 'mailto:'
                return

        time.sleep(2)  # Adding delay to avoid overloading the server
        response = requests.get(member_url, timeout=120)
        logging.log(logging.INFO, f"Fetching details on {partial_name} from {self.source}")
        if response.status_code != 200:
            return

        tree = html.fromstring(response.content)
        mem_name_element = tree.cssselect("#mainC > h3")

        if not mem_name_element:
            logging.warning(f"No member name element found at {member_url}")
            return

        mem_name = mem_name_element[0].text_content().strip()

        # Use the regex pattern to extract the clean name
        match = member_pattern.match(mem_name)
        if match:
            cleaned_name = match.group(1).strip()  # Extract the name without the title
        else:
            cleaned_name = mem_name  # Fallback to the original name if no match

        self.com.add_member(cleaned_name, role)


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
        if not detail_link:
            raise SkipItem("No link found for committee.")

        com.add_source(self.source.url, note="Committee List Page")
        com.add_source(detail_link, note="Committee Detail Page")

        try:
            detail_page = CommitteeDetail(com, source=detail_link)
            return detail_page.process_page()
        except MissingSourceError:
            raise SkipItem("No link found for committee.")


class SubcommitteeList(HtmlPage):
    def __init__(self, source, parent, chamber):
        self.source = source
        self.parent = parent
        self.chamber = chamber

    def process_page(self):
        response = requests.get(self.source, timeout=120)
        if response.status_code != 200:
            raise SkipItem(f"Cannot access parent committee details")
        tree = html.fromstring(response.content)
        # Check for subcommittees
        link_list = tree.cssselect(".linkSect")
        if len(link_list) > 2:
            try:
                sub_com_list = link_list[2].cssselect("li a")
                # [x.get("href") for x in sub_com_list]
                for link in sub_com_list:
                    detail_link = f"https://lis.virginia.gov{link.get('href')}"
                    sub_com_name = link.text_content().strip()
                    if "Subcommittee" in sub_com_name:
                        sub_com_name = f"{self.parent} {sub_com_name}"
                    sub_com = ScrapeCommittee(
                        name=sub_com_name,
                        classification="subcommittee",
                        chamber=self.chamber,
                        parent=self.parent
                    )
                    sub_com.add_source(self.source, note="Committee List Page")
                    sub_com.add_source(detail_link, note="Committee Detail Page")
                    try:
                        detail_page = CommitteeDetail(sub_com, source=detail_link)
                        return detail_page.process_page()
                    except MissingSourceError:
                        raise SkipItem("No link found for committee.")

            except IndexError:
                raise SkipItem(f"Committees has no subcommittees.")


class FindSubcommittees(HtmlListPage):
    source = "https://lis.virginia.gov/241/com/COM.HTM"
    selector = CSS(".linkSect a")

    def process_item(self, item):
        parent_name = item.text
        # both senate and house committees are listed on one page, so this isolates which is which
        chamber_text = item.getparent().getparent().getparent().getchildren()[0].text
        if "HOUSE" in chamber_text:
            chamber = "lower"
        else:
            chamber = "upper"

        detail_link = item.get("href")
        if not detail_link:
            raise SkipItem("No link found for committee.")

        try:
            detail_page = SubcommitteeList(source=detail_link, parent=parent_name, chamber=chamber)
            return detail_page.process_page()
        except MissingSourceError:
            raise SkipItem("No link found for committee.")
