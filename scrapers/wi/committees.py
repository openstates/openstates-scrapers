import lxml.html
from openstates_core.scrape import Scraper, Organization

from .common import SESSION_TERMS


class WICommitteeScraper(Scraper):
    def scrape_committee(self, name, url, chamber):
        org = Organization(name=name, chamber=chamber, classification="committee")
        org.add_source(url)
        data = self.get(url).text
        doc = lxml.html.fromstring(data)

        for leg in doc.xpath('//div[@id="members"]/div[@id="members"]/p/a/text()'):
            leg = leg.replace("Representative ", "")
            leg = leg.replace("Senator ", "")
            leg = leg.strip()
            if " (" in leg:
                leg, role = leg.split(" (")
                if "Vice-Chair" in role:
                    role = "vice-chair"
                elif "Co-Chair" in role:
                    role = "co-chair"
                elif "Chair" in role:
                    role = "chair"
                else:
                    raise Exception("unknown role: %s" % role)
            else:
                role = "member"
            org.add_member(leg, role)

        return org

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        term = SESSION_TERMS[session]

        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        for chamber in chambers + ["legislature"]:
            url = "http://docs.legis.wisconsin.gov/{}/committees/".format(
                term.split("-")[0]
            )
            if chamber == "legislature":
                url += "joint"
            elif chamber == "upper":
                url += "senate"
            else:
                url += "assembly"
            data = self.get(url).text
            doc = lxml.html.fromstring(data)
            doc.make_links_absolute(url)

            for a in doc.xpath('//ul[@class="docLinks"]/li/p/a'):
                if "(Disbanded" not in a.text:
                    comm_name = a.text
                    comm_name = comm_name.replace("Committee on", "")
                    comm_name = comm_name.replace("Assembly", "")
                    comm_name = comm_name.replace("Joint Survey", "")
                    comm_name = comm_name.replace("Joint Review", "")
                    comm_name = comm_name.replace("Joint", "")
                    comm_name = comm_name.replace("Senate", "")
                    comm_name = comm_name.replace("Committee for", "")
                    comm_name = comm_name.replace("Committee", "")
                    comm_name = comm_name.strip()
                    yield self.scrape_committee(comm_name, a.get("href"), chamber)
