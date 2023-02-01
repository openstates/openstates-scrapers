from spatula import JsonPage
from openstates.models import ScrapeCommittee
import json
import re
import logging


class SubcommitteeDetectedError(BaseException):
    def __init__(self, name):
        super().__init__(f"Scraper has no way to detect parent of subcommittee: {name}")


class CommitteeList(JsonPage):
    def process_page(self):
        membership = json.loads(self.data[1][0]["CommitteeMembership"])

        for committee in self.data[0]:
            name = committee["Code_Description"]
            if committee["Code_House"] == "S":
                chamber = "upper"
            elif committee["Code_House"] == "A":
                chamber = "lower"
            else:
                chamber = "legislature"

            if "subcommittee" in name.lower():
                raise SubcommitteeDetectedError(name)

            name = name.removeprefix("Assembly ").removeprefix("Senate ").strip()

            try:
                members = membership["Committees"][committee["Comm_Status"]]
            except KeyError:
                logging.warning(f"No membership data found for: {name}")
                continue

            comm = ScrapeCommittee(
                name=name,
                chamber=chamber,
                classification="committee",
            )

            for member in members:
                member_name = member["FullName"]
                name_regex = re.compile("(.*?), +(.*)")
                name_match = name_regex.match(member_name)
                new_name = " ".join([name_match.group(2), name_match.group(1)])

                role = member["Position"]
                comment = member["Comment"]
                # Covers cases of members with extraordinary
                #  reasons for placement on committee
                #  (i.e. comment = "Treasury Member" for Asst. Treasury Sec.)
                if comment and not role:
                    role = comment

                comm.add_member(
                    name=new_name,
                    role=role if role else "Member",
                )

            comm.add_link(
                "https://www.njleg.state.nj.us/"
                f"committees/{self.link_keyword}-committees",
                note="homepage",
            )
            comm.add_source(
                self.source.url, note="JSON data page from NJ Legislative API"
            )
            yield comm


class JointCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/joint-committees"
    link_keyword = "joint"


class SenateCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/senate-committees"
    link_keyword = "senate"


class AssemblyCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/assembly-committees"
    link_keyword = "assembly"


class OtherCommitteeList(CommitteeList):
    source = "https://www.njleg.state.nj.us/api/legislatorData/committeeInfo/other-committees"
    link_keyword = "other"
