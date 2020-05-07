from openstates.scrape import Scraper, Organization

import lxml.etree


class MSCommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        chambers = [chamber] if chamber else ["upper", "lower"]
        for chamber in chambers:
            if chamber == "lower":
                chamber = "h"
            else:
                chamber = "s"

            yield from self.scrape_comm(chamber)

    def scrape_comm(self, chamber):
        url = "http://billstatus.ls.state.ms.us/htms/%s_cmtememb.xml" % chamber
        comm_page = self.get(url)
        root = lxml.etree.fromstring(comm_page.content)
        if chamber == "h":
            chamber = "lower"
        else:
            chamber = "upper"
        for mr in root.xpath("//COMMITTEE"):
            name = mr.xpath("string(NAME)")
            comm = Organization(name, chamber=chamber, classification="committee")
            chair = mr.xpath("string(CHAIR)")
            chair = chair.replace(", Chairman", "")
            role = "Chairman"
            if len(chair) > 0:
                comm.add_member(chair, role=role)
            vice_chair = mr.xpath("string(VICE_CHAIR)")
            vice_chair = vice_chair.replace(", Vice-Chairman", "")
            role = "Vice-Chairman"
            if len(vice_chair) > 0:
                comm.add_member(vice_chair, role=role)
            members = mr.xpath("string(MEMBERS)").split(";")
            if "" in members:
                members.remove("")

            for leg in members:
                leg = leg.strip()
                comm.add_member(leg)

            comm.add_source(url)
            yield comm
