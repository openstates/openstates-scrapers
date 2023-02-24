from spatula import JsonPage, URL
from openstates.models import ScrapeCommittee
import json


# Receives data about members in a single committee
class MemberList(JsonPage):
    def process_page(self):
        data = self.response.json().get("data").get("membersByCommittee")
        for member in data:
            yield (member.get("MemberName"), member.get("MemberPosition"))


# Receives a list of committees
class CommitteeList(JsonPage):
    def process_page(self):
        data = self.response.json().get("data").get("committees")
        for committee in data:
            name = committee.get("Committee")

            # Removes extra text from committee name
            if name.startswith("Joint "):
                name = name[len("Joint ") :]
            if name.endswith(" Committee"):
                name = name[: -len(" Committee")]

            com = ScrapeCommittee(
                name=name,
                chamber=self.chamber,
                classification="committee",
            )

            # Individual pages can't be accessed with  url, so add the
            # committee list page as the homepage link
            if self.chamber == "upper":
                com.add_link(
                    "https://alison.legislature.state.al.us/committees-senate-standing-current-year",
                    note="homepage",
                )
            elif self.chamber == "lower":
                com.add_link(
                    "https://alison.legislature.state.al.us/committees-house-standing-current",
                    note="homepage",
                )
            elif self.chamber == "joint":
                com.add_link(
                    "https://alison.legislature.state.al.us/joint-interim-committees",
                    note="homepage",
                )

            # Add sources
            member_source = get_committee_members_source(committee.get("CommitteeId"))
            com.add_source(member_source.url, note="Membership information api call")
            com.add_source(self.source.url, note="Committee list api call")

            # Add members
            members = MemberList(source=member_source).do_scrape()
            for name, role in members:
                com.add_member(name=name, role=role)

            # Check if there are any members. Only yield if there are members,
            # otherwise log a warning.
            if len(com.members) == 0:
                self.logger.warning(f"No membership information for: {com.name}")
            else:
                yield com


def graphql_query(data):
    return URL(
        "https://gql.api.alison.legislature.state.al.us/graphql",
        method="POST",
        headers={
            "Content-Type": "application/json",
            # Referer required or graphql will respond with http error 403
            "Referer": "https://alison.legislature.state.al.us/",
        },
        data=json.dumps(data),
    )


def get_committee_members_source(committeeId):
    return graphql_query(
        {
            "query": '{membersByCommittee(committeeId:"'
            + committeeId
            + '") {Committee,MemberName,MemberPosition}}',
            "operationName": "",
            "variables": [],
        },
    )


# Chamber should be "House", "Senate", or "Joint"
def get_committees_source(chamber):
    return graphql_query(
        {
            "query": '{committees(body:"'
            + chamber
            + '", direction:"asc"orderBy:"committee"limit:"99999"offset:"0" customFilters: {}){ CommitteeId,Committee }}',
            "operationName": "",
            "variables": [],
        },
    )


class Joint(CommitteeList):
    chamber = "legislature"
    source = get_committees_source(chamber="Joint")


class House(CommitteeList):
    chamber = "lower"
    source = get_committees_source(chamber="House")


class Senate(CommitteeList):
    chamber = "upper"
    source = get_committees_source(chamber="Senate")
