import re

import lxml.html
from openstates.scrape import Scraper, Organization


class KYCommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        if chamber == "lower":
            urls = [("http://www.lrc.ky.gov/committee/standing_house.htm", "lower")]
        else:
            urls = [
                ("http://www.lrc.ky.gov/committee/standing_senate.htm", "upper"),
                # ("http://www.lrc.ky.gov/committee/interim.htm", 'upper'),
                ("http://www.lrc.ky.gov/committee/statutory.htm", "legislature"),
            ]

        self.parents = {}

        for url_info in urls:
            url = url_info[0]
            chamber = url_info[1]

            page = self.get(url).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            links = []

            cttypages = [
                "//a[contains(@href, 'standing/')]",
                "//a[contains(@href, 'interim')]",
                "//a[contains(@href, 'statutory')]",
            ]

            for exp in cttypages:
                links += page.xpath(exp)

            for link in links:
                yield from self.scrape_committee(chamber, link)

    def scrape_committee(self, chamber, link, parent_comm=None):
        home_link = link.attrib["href"]
        name = re.sub(r"\s+\((H|S)\)$", "", link.text).strip().title()
        name = name.replace(".", "").strip()
        if "Subcommittee " in name and parent_comm:
            name = name.split("Subcommittee")[1]
            name = name.replace(" on ", "").replace(" On ", "")
            name = name.strip()
            comm = Organization(
                name, parent_id=self.parents[parent_comm], classification="committee"
            )
        else:
            for c in ["Committee", "Comm", "Sub", "Subcommittee"]:
                if name.endswith(c):
                    name = name[: -1 * len(c)].strip()
            comm = Organization(name, chamber=chamber, classification="committee")
            self.parents[name] = comm._id
        comm.add_source(home_link)
        comm_url = home_link.replace("home.htm", "members.htm")
        self.scrape_members(comm, comm_url)

        if comm._related:
            yield comm
        else:
            self.logger.warning("Empty committee, skipping.")

        # deal with subcommittees
        if parent_comm is None:
            # checking parent_comm so we don't look for subcommittees
            # in subcommittees leaving us exposed to infinity
            page = self.get(home_link).text
            page = lxml.html.fromstring(page)
            page.make_links_absolute(home_link)
            sub_links = page.xpath("//li/a[contains(@href, '/home.htm')]")
            for link in sub_links:
                if "committee" in link.text.lower():
                    yield from self.scrape_committee(chamber, link, name)

    def scrape_members(self, comm, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        comm.add_source(url)

        for link in page.xpath("//a[contains(@href, 'Legislator')]"):
            name = re.sub(r"^(Rep\.|Sen\.) ", "", link.text).strip()
            name = name.replace("  ", " ")
            if not link.tail or not link.tail.strip():
                role = "member"
            elif link.tail.strip() == "[Chair]":
                role = "chair"
            elif link.tail.strip() == "[Co-Chair]":
                role = "co-chair"
            elif link.tail.strip() == "[Vice Chair]":
                role = "vice chair"
            elif link.tail.strip() == "[Co-Chair Designate]":
                role = "co-chair designate"
            elif link.tail.strip() in [
                "[ex officio]",
                "[non voting ex officio]",
                "[Liaison Member]",
            ]:
                role = "member"
            else:
                raise Exception("unexpected position: %s" % link.tail)
            comm.add_member(name, role=role)
