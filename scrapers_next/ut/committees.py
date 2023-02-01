from spatula import JsonListPage, URL
import logging
from openstates.models import ScrapeCommittee
import requests


class UnknownParentError(BaseException):
    def __init__(self, com_name):
        super().__init__(f"Parent unknown for subcommittee {com_name}")


def get_membership_dict(url):
    membership = {}
    response = requests.get(url)
    for each_legislator in response.json()["legislators"]:
        member_id = each_legislator["id"]
        name = each_legislator["formatName"]
        membership[member_id] = name
    return membership


class CommitteeList(JsonListPage):
    source = URL(
        "https://le.utah.gov/data/committees.json",
        timeout=10,
    )

    def process_page(self):
        legislators_url = "https://le.utah.gov/data/legislators.json"
        # uses helper function defined above this class
        membership = get_membership_dict(legislators_url)

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
                # currently the only committee with subcommittees listed
                if "appropriations" in name.lower():
                    parent = "Executive Appropriations Committee"
                # if other parent committees are discovered in future scrape
                else:
                    raise UnknownParentError(name)
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
            for each_member in members_list:
                member_id = each_member["id"]
                name = membership[member_id]
                role = each_member["position"]
                com.add_member(name, role=role.title())

            if not com.members:
                logging.warning(f"No membership data found for: {name}")
                continue

            if len(each_committee.get("link")):
                com.add_link(each_committee["link"], note="homepage")
            else:
                com.add_link("", note="homepage")

            com.add_source(
                self.source.url,
                note="Committee JSON from le.utah.gov site",
            )
            yield com
