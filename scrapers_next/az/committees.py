# import re
from spatula import XPath, URL, XmlListPage

# from openstates.models import ScrapeCommittee

# to get all committees: https://apps.azleg.gov/api/Committee

#


class SenateCommitteeList(XmlListPage):
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

    def process_item(self, item):
        print("HUH")
        # type = item.text_content()
        # if type == "Standing" or type == "Statutory":

        #     print("WHAT WHAT", item.get("href"))
        #     # return SenateTypeCommitteeList(source=item.get("href"))
        # else:
        #     print("HEREEE")
        #     self.skip()
