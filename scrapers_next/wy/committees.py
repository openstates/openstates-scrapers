from spatula import URL, JsonListPage
import logging
from openstates.models import ScrapeCommittee
import requests


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
        for committees in ["SE", "O"]:
            if committees == "J":
                comm_resp = self.response.json()
            else:
                comm_list_url = self.source.url.replace("/J", f"/{committees}")
                comm_resp = requests.get(comm_list_url).json()

            for each_comm in comm_resp["committeeList"]:

                committee_url = f"https://web.wyoleg.gov/LsoService/api/committeeDetail/{self.year}/{each_comm['ownerID']}"
                committee_info = requests.get(committee_url).json()

                # name
                name = committee_info["commName"]

                # need to identify this
                if committee_info["senateHasChair"] and committee_info["houseHasChair"]:
                    chamber = "legislature"
                elif committee_info["senateHasChair"]:
                    chamber = "upper"
                else:
                    chamber = "lower"
                if "subcommittee" in committee_info["commName"]:
                    # classification & parent check
                    classification = "subcommittee"
                    parent = (
                        committee_info["commName"].replace("subcommittee", "").strip()
                    )
                else:
                    classification = "committee"
                    parent = None

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
                    committee_url,
                    note="Committee JSON from wyoleg.gov site",
                )
                yield com
