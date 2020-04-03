"""
Archived Committee notes:

Senate committees only avail from 105th forward

Urls are inconsistent
'http://www.capitol.tn.gov/senate/archives/105GA/Committees/scommemb.htm'
'http://www.capitol.tn.gov/senate/archives/106GA/Committees/index.html'

'http://www.capitol.tn.gov/house/archives/99GA/Committees/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/100GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/101GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/102GA/Committees/HComm.htm'
'http://www.capitol.tn.gov/house/archives/103GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/104GA/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/105GA/Committees/hcommemb.htm'
'http://www.capitol.tn.gov/house/archives/106GA/Committees/index.html'

"""
import re

from openstates.scrape import Scraper, Organization
import lxml.html
import requests


# All links in a section with a given title
COMMITTEE_LINKS_TEMPLATE = '//h2[text()="{header}"]/parent::*//a'


class TNCommitteeScraper(Scraper):
    base_href = "http://www.capitol.tn.gov"
    chambers = {"lower": "house", "upper": "senate"}
    parents = {}

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        url_chamber = self.chambers[chamber]
        url = "http://www.capitol.tn.gov/%s/committees/" % (url_chamber)
        if chamber == "upper":
            yield self.scrape_senate_committees(url)
            yield self.scrape_joint_committees()
        else:
            yield self.scrape_house_committees(url)

    def scrape_senate_committees(self, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        standing = COMMITTEE_LINKS_TEMPLATE.format(header="Standing Committees")
        select = COMMITTEE_LINKS_TEMPLATE.format(header="Select Committees")
        find_expr = "{}|{}".format(standing, select)
        links = [(a.text_content(), a.attrib["href"]) for a in page.xpath(find_expr)]

        for committee_name, link in links:
            yield self._scrape_committee(committee_name, link, "upper")

    def scrape_house_committees(self, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        standing = COMMITTEE_LINKS_TEMPLATE.format(header="Committees & Subcommittees")
        select = COMMITTEE_LINKS_TEMPLATE.format(header="Select Committees")
        links = doc.xpath("{}|{}".format(standing, select))

        for a in links:
            yield self._scrape_committee(a.text.strip(), a.get("href"), "lower")

    def _scrape_committee(self, committee_name, link, chamber):
        """Scrape individual committee page and add members"""

        page = self.get(link).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(link)

        is_subcommittee = bool(page.xpath('//li/a[text()="Committee"]'))
        if is_subcommittee:
            # All TN subcommittees are just the name of the parent committee with " Subcommittee"
            # at the end
            parent_committee_name = re.sub(
                r"\s*(Study )?Subcommittee\s*", "", committee_name
            )
            com = Organization(
                committee_name,
                classification="committee",
                parent_id=self.parents[parent_committee_name],
            )
        else:
            com = Organization(
                committee_name, chamber=chamber, classification="committee"
            )
            self.parents[committee_name] = com._id

        OFFICER_SEARCH = (
            '//h2[contains(text(), "Committee Officers")]/'
            "following-sibling::div/ul/li/a"
        )
        MEMBER_SEARCH = (
            '//h2[contains(text(), "Committee Members")]/'
            "following-sibling::div/ul/li/a"
        )
        for a in page.xpath(OFFICER_SEARCH) + page.xpath(MEMBER_SEARCH):

            member_name = " ".join(
                [
                    x.strip()
                    for x in a.xpath("text()") + a.xpath("span/text()")
                    if x.strip()
                ]
            )
            role = a.xpath("small")
            if role:
                role = role[0].xpath("text()")[0].strip()
            else:
                role = "member"
            if "(Vacant)" in role:
                continue

            com.add_member(member_name, role)

        com.add_link(link)
        com.add_source(link)
        return com

    # Scrapes joint committees
    def scrape_joint_committees(self):
        main_url = "http://www.capitol.tn.gov/joint/"

        page = self.get(main_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(main_url)

        for el in page.xpath(COMMITTEE_LINKS_TEMPLATE.format(header="Committees")):
            com_name = el.text
            com_link = el.attrib["href"]
            com = self.scrape_joint_committee(com_name, com_link)
            if com:
                yield com

    # Scrapes the individual joint committee - most of it is special case
    def scrape_joint_committee(self, committee_name, url):
        if "state.tn.us" in url:
            com = Organization(
                committee_name, chamber="legislature", classification="committee"
            )
            try:
                page = self.get(url).text
            except requests.exceptions.ConnectionError:
                self.logger.warning("Committee link is broken, skipping")
                return

            page = lxml.html.fromstring(page)

            for el in page.xpath(
                "//div[@class='Blurb']/table//tr[2 <= position() and  position() < 10]/td[1]"
            ):
                if el.xpath("text()") == ["Vacant"]:
                    continue

                (member_name,) = el.xpath("a/text()")
                if el.xpath("text()"):
                    role = el.xpath("text()")[0].strip(" ,")
                else:
                    role = "member"

                member_name = member_name.replace("Senator", "")
                member_name = member_name.replace("Representative", "")
                member_name = member_name.strip()
                com.add_member(member_name, role)

            com.add_link(url)
            com.add_source(url)
            return com

        elif "gov-opps" in url:
            com = Organization(
                committee_name, chamber="legislature", classification="committee"
            )
            page = self.get(url).text
            page = lxml.html.fromstring(page)

            links = ["senate", "house"]
            for link in links:
                chamber_link = self.base_href + "/" + link + "/committees/gov-opps.html"
                chamber_page = self.get(chamber_link).text
                chamber_page = lxml.html.fromstring(chamber_page)

                OFFICER_SEARCH = (
                    '//h2[contains(text(), "Committee Officers")]/'
                    "following-sibling::div/ul/li/a"
                )
                MEMBER_SEARCH = (
                    '//h2[contains(text(), "Committee Members")]/'
                    "following-sibling::div/ul/li/a"
                )
                for a in chamber_page.xpath(OFFICER_SEARCH) + chamber_page.xpath(
                    MEMBER_SEARCH
                ):
                    member_name = " ".join(
                        [x.strip() for x in a.xpath(".//text()") if x.strip()]
                    )
                    role = a.xpath("small")
                    if role:
                        role = role[0].xpath("text()")[0].strip()
                        member_name = member_name.replace(role, "").strip()
                    else:
                        role = "member"
                    com.add_member(member_name, role)

                com.add_source(chamber_link)

            com.add_link(url)
            com.add_source(url)
            return com

        else:
            return self._scrape_committee(committee_name, url, "legislature")
