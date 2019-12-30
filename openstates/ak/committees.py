import lxml.html
from pupa.scrape import Scraper, Organization


class AKCommitteeScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        url = (
            "http://www.legis.state.ak.us/basis/commbr_info.asp" "?session=%s" % session
        )

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        chamber_abbrev = {"upper": "S", "lower": "H"}[chamber]

        for link in page.xpath("//a[contains(@href, 'comm=')]"):
            name = link.text.strip().title()

            if name.startswith("Conference Committee"):
                continue

            url = link.attrib["href"]
            if ("comm=%s" % chamber_abbrev) in url:
                yield from self.scrape_committee(chamber, name, url)

    def scrape_committee(self, chamber, name, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        if page.xpath("//h3[. = 'Joint Committee']"):
            chamber = "joint"

        subcommittee = page.xpath("//h3[@align='center']/text()")[0]
        if "Subcommittee" not in subcommittee:
            comm = Organization(chamber=chamber, name=name, classification="committee")
        else:
            comm = Organization(
                name=subcommittee,
                classification="committee",
                parent_id={"classification": chamber, "name": name},
            )

        comm.add_source(url)

        for link in page.xpath("//a[contains(@href, 'member=')]"):
            member = link.text.strip()

            mtype = link.xpath("string(../preceding-sibling::td[1])")
            mtype = mtype.strip(": \r\n\t").lower()

            comm.add_member(member, mtype)

        if not comm._related:
            self.warning("not saving %s, appears to be empty" % name)
        else:
            yield comm
