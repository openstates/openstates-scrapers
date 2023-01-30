from spatula import JsonListPage, URL
import logging
from openstates.models import ScrapeCommittee


class CommitteeList(JsonListPage):
    source = URL(
        "https://le.utah.gov/data/committees.json",
        timeout=10,
    )

    def process_page(self):
        for each_committee in self.response.json()["committees"]:
            # name
            name = each_committee["description"]
            # chamber
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
                classification = "subcommittee"
                parent = name.lower().split(" ")[-2:]
                parent = " ".join(parent)

            name = (
                name.lower().replace("house", "").replace("senate", "").strip().title()
            )
            com = ScrapeCommittee(
                name=name,
                chamber=chamber,
                parent=parent,
                classification=classification,
            )
            # extracting members
            members_list = each_committee["members"]
            for each_memeber in members_list:
                member_name_split = each_memeber["name"].split(",")
                member_name_split.reverse()
                member_name = " ".join(member_name_split).replace(".", "").strip()

                role = each_memeber["position"]
                com.add_member(name=member_name, role=role)

            if not com.members:
                logging.warning(f"No membership data found for: {name}")
                continue
            if each_committee.get("link"):
                com.add_link(each_committee["link"], note="Committee web page")

            com.add_source(
                self.source.url,
                note="Committee JSON from le.utah.gov site",
            )
            yield com
