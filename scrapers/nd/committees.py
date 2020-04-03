from openstates_core.scrape import Scraper, Organization
import lxml.html


class NDCommitteeScraper(Scraper):
    def scrape_committee(self, term, href, name):
        page = self.get(href).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(href)
        members = page.xpath(
            "//div[@class='view-content']" "//a[contains(@href, 'members')]"
        )

        if "/joint/" in href:
            chamber = "legislature"
        elif "/senate/" in href:
            chamber = "upper"
        elif "/house/" in href:
            chamber = "lower"
        else:
            # interim committees and others were causing duplicate committee issues, skipping
            self.warning("Failed to identify chamber for {}; skipping".format(href))
            return

        cttie = Organization(name, chamber=chamber, classification="committee")
        for a in members:
            member = a.text
            role = a.xpath("ancestor::div/h2[@class='pane-title']/text()")[0].strip()
            role = {
                "Legislative Members": "member",
                "Chairman": "chair",
                "Vice Chairman": "member",
            }[role]

            if member is None or member.startswith("District"):
                continue

            member = member.replace("Senator ", "").replace("Representative ", "")

            cttie.add_member(member, role=role)

        cttie.add_source(href)
        yield cttie

    def scrape(self, chamber=None):
        # figuring out starting year from metadata
        start_year = self.jurisdiction.legislative_sessions[-1]["start_date"][:4]
        term = self.jurisdiction.legislative_sessions[-1]["identifier"]

        root = "http://www.legis.nd.gov/assembly"
        main_url = "%s/%s-%s/committees" % (root, term, start_year)

        page = self.get(main_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(main_url)

        ctties = page.xpath("//div[@class='inside']")[0]
        for a in ctties.xpath(".//a[contains(@href, 'committees')]"):
            yield from self.scrape_committee(term, a.attrib["href"], a.text)
