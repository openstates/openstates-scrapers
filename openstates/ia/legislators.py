import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class IALegislatorScraper(LegislatorScraper):
    state = 'ia'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            chamber_name = 'senate'
        else:
            chamber_name = 'house'

        url = "http://www.legis.iowa.gov/Legislators/%s.aspx" % chamber_name
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'legislator.aspx')]"):
            name = link.text.strip()
            district = link.xpath("string(../../td[2])")
            party = link.xpath("string(../../td[3])")
            email = link.xpath("string(../../td[5])")

            if party == 'Democrat':
                party = 'Democratic'

            pid = re.search("PID=(\d+)", link.attrib['href']).group(1)
            photo_url = ("http://www.legis.iowa.gov/getPhotoPeople.aspx"
                         "?GA=84&PID=%s" % pid)

            leg = Legislator(term, chamber, district, name, party=party,
                             email_address=email, photo_url=photo_url)
            leg.add_source(url)

            leg_page = lxml.html.fromstring(self.urlopen(link.attrib['href']))
            comm_path = "//a[contains(@href, 'committee')]"
            for comm_link in leg_page.xpath(comm_path):
                comm = comm_link.text.strip()

                if comm.endswith('Appropriations Subcommittee'):
                    sub = re.match('^(.+) Appropriations Subcommittee$',
                                   comm).group(1)
                    leg.add_role('committee member', term, chamber=chamber,
                                 committee='Appropriations',
                                 subcommittee=sub)
                else:
                    leg.add_role('committee member', term, chamber=chamber,
                                 committee=comm)

            self.save_legislator(leg)
