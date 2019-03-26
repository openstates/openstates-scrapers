import re

from pupa.scrape import Scraper, Organization

import lxml.html


def clean(stream):
    return re.sub(r'\s+', ' ', stream).strip()


class RICommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber in ['upper', None]:
            yield from self.scrape_comms('upper', 'ComMemS')
            yield from self.scrape_comms('legislature', 'ComMemJ')
        if chamber in ['lower', None]:
            yield from self.scrape_comms('lower', 'ComMemr')

    def scrape_comm_list(self, ctype):
        url = 'http://webserver.rilin.state.ri.us/CommitteeMembers/'
        page = self.get(url).text
        root = lxml.html.fromstring(page)
        root.make_links_absolute(url)
        return root.xpath("//a[contains(@href,'" + ctype + "')]")

    def add_members(self, comm, url):
        # We do this twice because the first request should create the
        # session cookie we need.
        for x in range(2):
            page = self.get(url).text
        root = lxml.html.fromstring(page)
        # The first <tr> in the table of members
        membertable = root.xpath('//p[@class="style28"]/ancestor::table[1]')[0]
        members = membertable.xpath("*")[1:]

        order = {
            "name": 0,
            "appt": 1,
            "email": 2
        }

        for member in members:
            name = member[order['name']].text_content().strip()
            name = name.replace("Senator", "").replace("Representative", "").strip()
            appt = member[order['appt']].text_content().strip()
            self.info("name " + name + " role " + appt)
            comm.add_member(name, appt)

    def scrape_comms(self, chamber, ctype):
        for a in self.scrape_comm_list(ctype):
            link = a.attrib['href']
            commName = clean(a.text_content())
            self.info("url " + link)
            c = Organization(chamber=chamber, name=commName, classification='committee')
            self.add_members(c, link)
            c.add_source(link)
            yield c
