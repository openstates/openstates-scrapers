from spatula import URL, HtmlListPage, HtmlPage, XPath
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
        staff = {"staff": []}
        members = XPath('//div[@class="member-wrapper"]').match(self.root)
        for each_member in members:
            member_detail = each_member.text_content().strip()
            member_detail = [x.strip() for x in member_detail.splitlines() if x.strip()]

            if len(member_detail) == 5:
                role = member_detail[-1]
            else:
                role = "Member"
            name = [
                x.text_content()
                for x in each_member.findall("div", {"class": "strong member-name"})
            ]

            if len(name) == 1:
                name = re.sub("\\s+", " ", name[0]).strip()
                staff["staff"].append({"name": name, "role": "staff"})
                continue
            elif len(name) == 3:
                name = f"{name[0]}{name[1]}"
                name = re.sub("\\s+", " ", name).strip()
                staff["staff"].append(
                    {"name": name, "role": "Committee Citizen Members"}
                )
                continue
            else:
                name = member_detail[1]
            com.add_member(name, role)
        com.extras = staff
        com.add_source(
            self.source.url,
            note="Committee Details page",
        )
        return com


class CommitteeList(HtmlListPage):
    source = URL("https://www.ndlegis.gov/assembly/68-2023/committees", timeout=10)

    def process_page(self, only_name=False):
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
