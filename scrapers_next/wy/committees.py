from spatula import URL, JsonListPage
import logging
from openstates.models import ScrapeCommittee
import requests
import re


class UnknownSubCommFound(BaseException):
    def __init__(self, com_name):
        super().__init__(f"unknown for subcommittee found: {com_name}")


class CommitteeList(JsonListPage):
    year = 2024
    source = URL(
        f"https://web.wyoleg.gov/LsoService/api/committeeList/{year}/J", timeout=15
    )
    num_name_re = re.compile(r"(\d+)-(.+)")

    def process_page(self):
        # the request was for only J type committees in the issue, but I added all
        # Joint & Standing > J
        # Select & Task Forces > SE
        # Councils & Commissions > O

        comm_resp = self.response.json()
        for each_comm in comm_resp["committeeList"]:

            committee_url = f"https://web.wyoleg.gov/LsoService/api/committeeDetail/{self.year}/{each_comm['ownerID']}"
            committee_info = requests.get(committee_url).json()

            # name
            name = committee_info["commName"]

            num_name = self.num_name_re.search(name)
            if num_name:
                name = num_name.groups()[-1]

            # need to identify this
            if committee_info["senateHasChair"] and committee_info["houseHasChair"]:
                chamber = "legislature"
            elif committee_info["senateHasChair"]:
                chamber = "upper"
            else:
                chamber = "lower"

            classification = "committee"
            parent = None
            if "subcommittee" in name.lower():
                if (
                    "capitol interpretive exhibits" in name.lower()
                    or "capitol governance" in name.lower()
                ):
                    name = name.replace("Subcommittee", "").strip()
                else:
                    raise UnknownSubCommFound(name)

            com = ScrapeCommittee(
                name=name,
                chamber=chamber,
                parent=parent,
                classification=classification,
            )

            # extracting members
            for each_member in committee_info["commMembers"]:
                name = each_member["name"]
                if each_member["chairman"].strip() == "":
                    role = "Member"
                else:
                    role = each_member["chairman"]
                com.add_member(name, role=role)
            if not com.members:
                logging.warning(f"No membership data found for: {name}")
                continue

            comm_html = (
                f"https://www.wyoleg.gov/Committees/{self.year}/{each_comm['ownerID']}"
            )
            com.add_link(comm_html, note="homepage")
            com.add_source(
                committee_url,
                note="Committee JSON from wyoleg.gov site",
            )
            yield com
