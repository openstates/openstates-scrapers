# import re
from spatula import XPath, URL, JsonListPage
from openstates.models import ScrapeCommittee

# to get all committees: https://apps.azleg.gov/api/Committee

#


class SenateCommitteeList(JsonListPage):
    # source = "https://www.senate.mo.gov/committee/"
    # source = URL("https://apps.azleg.gov/api/Committee", headers={sessionId=session_id,
    #         includeOnlyCommitteesWithAgendas="false",
    #         legislativeBody="S" if chamber == "upper" else "H",})

    # https://apps.azleg.gov/api/StandingCommittee/?legislativeBody=S&sessionId=123&includeMembers=true

    # OKAY SO THE PLAN:
    # first go here: https://apps.azleg.gov/api/Committee/?legislativeBody=S&sessionId=123&includeMembers=true
    # how to get session_id? idk lol
    # then go to each of the standing committees on that list, for ex.

    # or actually, go here for Senate: https://apps.azleg.gov/api/Committee/?legislativeBody=S&sessionId=123&includeMembers=true
    # then here for House: https://apps.azleg.gov/api/Committee/?legislativeBody=H&sessionId=123&includeMembers=true

    # class Legislators(XmlListPage):
    # session_num = "32"
    # source = URL(
    #     "http://www.legis.state.ak.us/publicservice/basis/members"
    #     f"?minifyresult=false&session={session_num}",
    #     headers={"X-Alaska-Legislature-Basis-Version": "1.4"},
    # )
    session_id = "123"
    source = URL(
        "https://apps.azleg.gov/api/Committee/"
        f"?legislativeBody=S&sessionId={session_id}&includeMembers=true"
    )
    selector = XPath("//CommitteeModel")
    chamber = "upper"

    def process_item(self, item):
        print("HUH")
        # print("ITEM", item[""])
        # name = XPath("/CommitteeName").match(item)
        name = item["CommitteeName"]
        print("NAME", name)
        print("item", item)

        # print("UM", item[I])
        print(item["IsSubCommittee"])
        if item["IsSubCommittee"] is False:
            # print("NOT HER")
            com = ScrapeCommittee(name=name, chamber=self.chamber)

        else:
            # TODO: unsure of what the parent of a subcommittee info would be stored?
            # check "/Committee/"
            com = ScrapeCommittee(
                name=name,
                classification="subcommittee",
                chamber=self.chamber,
                parent="Appropriations",
            )

        # members = self.data["d3p1:CommitteeMemberModel"]
        # members = item["d3p1:CommitteeMemberModel"]
        for member in item["Members"]:
            # print("MEMBERS", member)
            # com.add_member(member)
            # print("MEMBER NAME", member["FirstName"] + " " + member["LastName"])

            name = member["FirstName"] + " " + member["LastName"]
            if member["IsChair"]:
                position = "Chair"
            elif member["IsViceChair"]:
                position = "Vice Chair"
            else:
                position = "member"

            com.add_member(name, position)
        # for member in members:
        #     print("hi")

        com.extras["Committee ID"] = item["CommitteeId"]
        com.extras["Committee Short Name"] = item["CommitteeShortName"]
        com.extras["Committee Type"] = item["TypeName"]

        # TODO: only standing committees, right?

        # TODO: add links
        return com

        #                     com = ScrapeCommittee(name=name, chamber=self.chamber)
        #         else:
        #             com = ScrapeCommittee(
        #                 name=name,
        #                 classification="subcommittee",
        #                 chamber=self.chamber,
        #                 parent="Appropriations",
        #             )
        # type = item.text_content()
        # if type == "Standing" or type == "Statutory":

        #     print("WHAT WHAT", item.get("href"))
        #     # return SenateTypeCommitteeList(source=item.get("href"))
        # else:
        #     print("HEREEE")
        #     self.skip()
