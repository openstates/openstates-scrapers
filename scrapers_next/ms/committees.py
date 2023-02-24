from spatula import HtmlPage, XPath
from openstates.models import ScrapeCommittee
import re

leader_re = re.compile(r"(.+),\s+(.*Chairman)")


class Committees(HtmlPage):
    def process_page(self):
        chamber = XPath(".//house//text()").match(self.root)[0]

        committees = XPath(".//committee").match(self.root)
        for committee in committees:
            name = XPath(".//name//text()").match(committee)[0]

            comm = ScrapeCommittee(
                name=name,
                chamber="upper" if chamber == "S" else "lower",
                classification="committee",
            )

            chair = committee.xpath(".//chair//text()")
            vice = committee.xpath(".//vice_chair//text()")

            for leader in chair, vice:
                if leader:
                    name, role = leader_re.search(leader[0]).groups()
                    comm.add_member(name, role)

            members_block = committee.xpath(".//members//text()")
            members = [x.strip() for x in members_block[0].split(";")]
            for member in members:
                comm.add_member(member, "Member")

            comm.add_source(self.source.url, note="Committees List Page")
            comm.add_link(self.source.url, note="homepage")

            yield comm


class HouseComm(Committees):
    source = "http://billstatus.ls.state.ms.us/htms/h_cmtememb.xml"


class SenateComm(Committees):
    source = "http://billstatus.ls.state.ms.us/htms/s_cmtememb.xml"
