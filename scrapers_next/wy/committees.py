from spatula import URL, JsonListPage
import logging
from openstates.models import ScrapeCommittee
import requests


class SubcommitteeFound(BaseException):
    def __init__(self, com_name):
        super().__init__(
            f"Scraper has no process for ingesting subcommittee classification: {com_name}"
        )


class CommitteeList(JsonListPage):
    year = 2023
    source = URL(
        f"https://web.wyoleg.gov/LsoService/api/committeeList/{year}/J", timeout=15
    )

    def process_page(self):
        # the request was for only J type committees in the issue, but I added all
        # Joint & Standing > J
        # Select & Task Forces > SE
        # Councils & Commissions > O
        for other in ["SE", "O"]:
            comm_list_url = self.source.url.replace("/J", f"/{other}")
            comm_resp = requests.get(comm_list_url).json()

            for each_comm in comm_resp["committeeList"]:

                committee_url = f"https://web.wyoleg.gov/LsoService/api/committeeDetail/{self.year}/{each_comm['ownerID']}"
                committee_info = requests.get(committee_url).json()

                # name
                name = committee_info["commName"]

                # need to identify this
                if "house" in name.lower():
                    chamber = "lower"
                elif "senate" in name.lower():
                    chamber = "upper"
                else:
                    chamber = "legislature"

                # classification & parent check
                classification = "committee"
                parent = None
                if "subcommittee" in name.lower():
                    raise SubcommitteeFound(name)

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

                com.add_link(committee_url, note="homepage api")
                com.add_source(
                    self.source.url,
                    note="Committee JSON from wyoleg.gov site",
                )
                yield com
