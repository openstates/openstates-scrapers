from spatula import XPath, URL, JsonListPage
from openstates.models import ScrapeCommittee


class CommitteeList(JsonListPage):

    session_id = "127"
    source = URL(
        "https://apps.azleg.gov/api/Committee/"
        f"?sessionId={session_id}&includeMembers=true"
    )
    selector = XPath("//CommitteeModel")

    def process_item(self, item):

        name = item["CommitteeName"]
        chamber = item["LegislativeBody"]

        if chamber == "H":
            chamber = "lower"
        elif chamber == "S":
            chamber = "upper"
        else:
            # a few Ad Hoc Committees don't have chambers, but are not included in the Standing Committees Scrape anyway
            self.logger.warning("Committee not assigned to chamber")
            chamber = "lower"

        if item["IsSubCommittee"] is False:
            com = ScrapeCommittee(name=name, chamber=chamber)

        else:

            try:
                parent, name = name.split(" Subcommittee on ")
            except ValueError:
                self.logger.warning(f"No parent listed for {name}")

            com = ScrapeCommittee(
                name=name,
                classification="subcommittee",
                chamber=chamber,
                parent=parent,
            )

        members = []
        for member in item["Members"]:

            name = member["FirstName"] + " " + member["LastName"]
            if member["IsChair"]:
                position = "Chair"
            elif member["IsViceChair"]:
                position = "Vice Chair"
            else:
                position = "member"

            # As of now, the API lists all members twice, so we must check for duplicates for members
            if f"{name} {position}" in members:
                continue
            else:
                members.append(f"{name} {position}")
                com.add_member(name, position)

        com.extras["Committee ID"] = item["CommitteeId"]
        com.extras["Committee Short Name"] = item["CommitteeShortName"]
        com.extras["Committee Type"] = item["TypeName"]

        com.add_source(self.source.url)

        return com
