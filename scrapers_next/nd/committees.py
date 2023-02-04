import spatula
from spatula import URL, HtmlListPage, HtmlPage, XPath, SkipItem
from openstates.models import ScrapeCommittee
import re


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
        for data in members_list:
            data_text = data.text_content()
            data_lines = data_text.splitlines()
            if len(data_lines) == 22:
                print("citizen")
                name = " ".join(x.strip() for x in data_lines[12:16] if x.strip())
                role = data_lines[-3].strip()
                print(name, role)

            elif len(data_lines) == 13:
                role = data_lines[-1].strip()
                if not role:
                    role = "Member"
                name = data_lines[9].strip()
                print(data_lines)
                print(role)
                print(name)

            elif len(data_lines) == 11:
                print("staff")
                name = " ".join([x.strip() for x in data_lines if x.strip()])
                staff.append({"role": "staff", "name": name})
                print(name)
                continue

            elif len(data_lines) == 12:
                print("---Vice")
                role = data_lines[-1].split("     ")[-1].strip()
                if not role:
                    role = "Member"
                name = data_lines[9].strip()
                print(data_lines)
                print(role)
                print(name)

            com.add_member(name, role)
        if staff:
            com.extras["staff"] = staff
        com.add_source(
            self.source.url,
            note="homepage",
        )
        return com


class CommitteeList(HtmlListPage):
    source = URL("https://www.ndlegis.gov/assembly/68-2023/committees", timeout=10)

    def process_page(self):
        all_comm_elements = []
        for comm_type in ["senate", "house", "interim"]:
            all_comm_elements += XPath(
                f"//a[contains(@href, '/committees/{comm_type}/')]"
            ).match(self.root)

        for elem in all_comm_elements:
            comm_url = elem.get("href")
            if comm_url.endswith("/committees"):
                continue
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
