import re
import lxml.html
from pupa.scrape import Scraper, Organization
from .utils import LXMLMixinOK


class OKCommitteeScraper(Scraper, LXMLMixinOK):
    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from getattr(self, "scrape_" + chamber)()

    def scrape_lower(self):
        url = "http://www.okhouse.gov/Committees/Default.aspx"
        page = self.curl_lxmlize(url)

        parents = {}

        for link in page.xpath(
            "//table[@id='ctl00_ContentPlace"
            "Holder1_dgrdCommittee_ctl00']//a[contains(@href, 'Members')]"
        ):
            name = link.xpath("string()").strip()

            if "Members" in name or "Conference" in name:
                continue

            match = re.search(r"CommID=(\d+)&SubCommID=(\d+)", link.attrib["href"])
            comm_id, sub_comm_id = int(match.group(1)), int(match.group(2))

            if sub_comm_id == 0:
                parents[comm_id] = name
                parent = None
            else:
                parent = parents[comm_id]

            yield from self.scrape_lower_committee(name, parent, link.attrib["href"])

    def scrape_lower_committee(self, name, parent, url):
        page = self.curl_lxmlize(url)

        if "Joint" in name or (parent and "Joint" in parent):
            chamber = "joint"
        else:
            chamber = "lower"

        if parent:
            comm = Organization(
                name=parent, chamber=chamber, classification="committee"
            )
            subcomm = Organization(
                name=name, parent_id=comm, classification="committee"
            )
        else:
            comm = Organization(name=name, chamber=chamber, classification="committee")
        comm.add_source(url)

        xpath = "//a[contains(@href, 'District')]"
        for link in page.xpath(xpath):
            member = link.xpath("string()").strip()
            member = re.sub(r"\s+", " ", member)

            if not member or member == "House District Maps":
                continue

            match = re.match(r"((Co-)?(Vice )?Chair)?Rep\. ([^\(]+)", member)
            member = match.group(4).strip()
            role = match.group(1) or "member"

            member = member.replace("Representative ", "")

            comm.add_member(member, role.lower())

        if not comm._related:
            if subcomm.name == "test":
                # Whoopsie, prod data.
                return

            raise Exception("no members for %s (%s)" % (comm.name, subcomm.name))

        yield comm

    def scrape_upper(self):
        url = "http://www.oksenate.gov/Committees/standingcommittees.htm"
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'standing/')]"):
            name = link.text.strip()
            name = re.sub(r"\s+", " ", name)
            if "Committee List" in name:
                continue

            yield from self.scrape_upper_committee(name, link.attrib["href"])

    def scrape_upper_committee(self, name, url):
        page = lxml.html.fromstring(self.get(url).text)

        comm = Organization(name=name, chamber="upper", classification="committee")
        comm.add_source(url)

        for link in page.xpath("//a[contains(@href, 'biographies')]"):
            member = link.xpath("string()").strip()
            member = re.sub(r"\s+", " ", member)
            if not member:
                continue
            role = link.tail
            if not role:
                role = "member"
            elif "Vice Chair" in role:
                role = "vice chair"
            elif "Chair" in role:
                role = "chair"
            member = member.replace("Senator ", "")
            comm.add_member(member, role=role)

        if not comm._related:
            raise Exception("no members for %s", comm.name)
        yield comm
