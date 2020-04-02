from openstates_core.scrape import Scraper, Organization
import lxml.html
from scrapelib import HTTPError


class MNCommitteeScraper(Scraper):
    # bad SSL as of August 2017
    verify = False

    def scrape(self, chambers=("upper", "lower")):
        if "upper" in chambers:
            yield from self.scrape_senate_committees()
        if "lower" in chambers:
            yield from self.scrape_house_committees()

    def scrape_senate_committees(self):
        url = "http://www.senate.mn/committees/index.php"

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        for link in doc.xpath('//a[contains(@href, "committee_bio")]/@href'):
            yield from self.scrape_senate_committee(link)

    def scrape_senate_committee(self, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        com_name = doc.xpath('//a[contains(@href, "committee_bio")]/text()')[0]
        parent = doc.xpath('//h4//a[contains(@href, "committee_bio")]/text()')
        if parent:
            self.log("%s is subcommittee of %s", com_name, parent[0])
            com = Organization(
                com_name,
                chamber="upper",
                classification="committee",
                parent_id={"name": parent[0], "classification": "upper"},
            )
        else:
            com = Organization(com_name, chamber="upper", classification="committee")

        for link in doc.xpath('//div[@id="members"]//a[contains(@href, "member_bio")]'):
            name = link.text_content().strip()
            if name:
                position = link.xpath(".//preceding-sibling::b/text()")
                if not position:
                    position = "member"
                elif position[0] == "Chair:":
                    position = "chair"
                elif position[0] == "Vice Chair:":
                    position = "vice chair"
                elif position[0] == "Ranking Minority Member:":
                    position = "ranking minority member"
                else:
                    raise ValueError("unknown position: %s" % position[0])

                name = name.split(" (")[0]
                com.add_member(name.strip(), position)

        com.add_source(url)
        yield com

    def scrape_house_committees(self):
        url = "http://www.house.leg.state.mn.us/comm/commemlist.asp"

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        for com in doc.xpath('//h2[@class="commhighlight"]'):
            members_url = com.xpath(
                'following-sibling::p[1]/a[text()="Members"]/@href'
            )[0]

            com = Organization(com.text, chamber="lower", classification="committee")
            com.add_source(members_url)

            try:
                member_html = self.get(members_url).text
                mdoc = lxml.html.fromstring(member_html)
            except HTTPError:
                self.warning(
                    "Member list for {} failed to respond; skipping".format(com.name)
                )
                continue

            # each legislator in their own table
            # first row, second column contains all the info
            for ltable in mdoc.xpath("//table/tr[1]/td[2]/p/b[1]"):

                # name is tail string of last element
                name = ltable.text_content()
                text = ltable.text
                if text and name != text:
                    name = name.replace(text, "")

                # role is inside a nested b tag
                role = ltable.xpath("b/*/text()")
                if role:
                    # if there was a role, remove it from name
                    role = role[0]
                    name = name.replace(role, "")
                else:
                    role = "member"
                name = name.split(" (")[0]
                com.add_member(name.strip(), role)

            # save
            yield com
