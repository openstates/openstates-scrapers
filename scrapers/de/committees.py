import lxml.html
from openstates.scrape import Scraper, Organization
from utils import LXMLMixin


class DECommitteeScraper(Scraper, LXMLMixin):
    jurisdiction = "de"

    def scrape(self, chamber=None, session=None):
        if chamber:
            yield from self.scrape_chamber(chamber, session)
        else:
            chambers = ["upper", "lower"]
            for chamber in chambers:
                yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        urls = {
            "upper": "http://legis.delaware.gov/json/Committees/"
            + "GetCommitteesByTypeId?assemblyId=%s&committeeTypeId=1",
            "lower": "http://legis.delaware.gov/json/Committees/"
            + "GetCommitteesByTypeId?assemblyId=%s&committeeTypeId=2",
        }

        self.info("no session specified, using %s", session)

        if chamber == "lower":
            # only scrape joint comms once
            yield from self.scrape_joint_committees(session)

        # scrap upper and lower committees
        url = urls[chamber] % (session,)
        yield from self.scrape_comm(url, chamber)

    def scrape_comm(self, url, chamber):
        data = self.post(url).json()["Data"]

        for item in data:
            comm_name = item["CommitteeName"]
            committee = Organization(
                name=comm_name, chamber=chamber, classification="committee"
            )
            chair_man = str(item["ChairName"])
            vice_chair = str(item["ViceChairName"])
            comm_id = item["CommitteeId"]
            comm_url = self.get_comm_url(chamber, comm_id, comm_name)
            members = self.scrape_member_info(comm_url)
            if vice_chair != "None":
                committee.add_member(vice_chair, role="Vice-Chair")
            if chair_man != "None":
                committee.add_member(chair_man, role="Chairman")

            for member in members:
                # vice_chair and chair_man already added.
                if chair_man not in member and vice_chair not in member:
                    member = " ".join(member.split())
                    if member:
                        committee.add_member(member)

            committee.add_source(comm_url)
            committee.add_source(url)
            yield committee

    def scrape_joint_committees(self, session):
        chamber = "legislature"
        url = (
            "http://legis.delaware.gov/json/Committees/"
            + "GetCommitteesByTypeId?assemblyId=%s&committeeTypeId=3" % (session,)
        )
        yield from self.scrape_comm(url, chamber)

    def scrape_member_info(self, comm_url):
        comm_page = lxml.html.fromstring(self.get(comm_url).text)
        # all members including chair_man and vice_chair
        members = comm_page.xpath(
            "//section[@class='section-short']/div[@class='info"
            + "-horizontal']/div[@class='info-group']/div[@class="
            + "'info-value']//a/text()"
        )
        return members

    def get_comm_url(self, chamber, comm_id, comm_name):
        if chamber == "legislature":
            # only Sunset url is not following pattern.
            if comm_name == "Joint Legislative Oversight and Sunset Committee":
                comm_url = "http://legis.delaware.gov/Sunset"
            else:
                comm_url = "http://legis.delaware.gov/" + "".join(comm_name.split())
        else:
            comm_url = "http://legis.delaware.gov/CommitteeDetail?committeeId=" + str(
                comm_id
            )
        return comm_url
