import requests
from lxml import html
from spatula import URL, HtmlListPage, HtmlPage, XPath, SkipItem, SelectorError
from openstates.models import ScrapeCommittee


class SubcommitteeFound(BaseException):
    def __init__(self, com_name):
        super().__init__(
            f"Scraper has no process for ingesting subcommittee classification: {com_name}"
        )


class CommitteeDetail(HtmlPage):
    def process_page(self):
        com = self.input
        staff = []
        members_list = XPath('//div[@class="member-wrapper"]').match(self.root)
        try:
            citizens = XPath("//div[@class='item-list']//li").match(self.root)
            for member in citizens:
                name, role = (None, None)
                data = member.text_content().split(",")
                if len(data) == 1:
                    name = data[0]
                    role = "Citizen Member"
                elif len(data) == 2:
                    name, role = data
                if name and role:
                    com.add_member(name, role)
        except SelectorError:
            pass
        for data in members_list:
            data_text = data.text_content()
            data_lines = data_text.splitlines()
            name, role = (None, None)
            if len(data_lines) == 22:
                name = " ".join(x.strip() for x in data_lines[12:16] if x.strip())
                role = data_lines[-3].strip()

            elif len(data_lines) in [13, 14]:
                role = data_lines[-1].strip()
                if not role:
                    role = "Member"
                name = data_lines[9].strip()

            elif len(data_lines) == 11:
                name = " ".join([x.strip() for x in data_lines if x.strip()])
                staff.append({"role": "staff", "name": name})
                continue

            elif len(data_lines) == 12:
                role = data_lines[-1].split("     ")[-1].strip()
                if not role:
                    role = "Member"
                name = data_lines[9].strip()
            if name and role:
                com.add_member(name, role)
        if staff:
            com.extras["staff"] = staff
        if not com.members:
            raise SkipItem("empty committee")
        com.add_source(
            self.source.url,
            note="Committee Details page",
        )
        com.add_link(
            self.source.url,
            note="homepage",
        )
        return com


class CommitteeList(HtmlListPage):
    source = URL("https://www.ndlegis.gov/assembly/68-2023/committees", timeout=10)

    def process_page(self):
        all_comm_elements = []

        stat_list_url = (
            XPath("//a[contains(text(), 'Statutory')]").match(self.root)[0].get("href")
        )
        stat_response = requests.get(stat_list_url)
        stat_page = html.fromstring(stat_response.content)
        stat_comm_elements = XPath("//div[@class='grouping-wrapper']//span/a").match(
            stat_page
        )
        all_comm_elements += stat_comm_elements

        for comm_type in ["senate", "house", "interim"]:
            all_comm_elements += XPath(
                f"//a[contains(@href, '/committees/{comm_type}/')]"
            ).match(self.root)

        for elem in all_comm_elements:
            comm_url = elem.get("href")

            # joint committees
            if comm_url[0] == "/":
                comm_url = "https://www.ndlegis.gov" + comm_url

            name = elem.text
            if "subcommittee" in name.lower():
                raise SubcommitteeFound(name)

            # chamber
            if "/house/" in comm_url.lower():
                chamber = "lower"
            elif "senate" in comm_url.lower():
                chamber = "upper"
            else:
                chamber = "legislature"

            com = ScrapeCommittee(
                name=name,
                chamber=chamber,
                parent=None,
                classification="committee",
            )

            com.add_source(
                self.source.url,
                note="Committee List page of ndlegis gov site",
            )
            yield CommitteeDetail(com, source=URL(comm_url, timeout=15))
