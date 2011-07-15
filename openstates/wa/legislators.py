from .utils import xpath
from billy.scrape.legislators import LegislatorScraper, Legislator

import scrapelib
import lxml.html
import lxml.etree


class WALegislatorScraper(LegislatorScraper):
    state = 'wa'

    def scrape(self, chamber, term):
        biennium = "%s-%s" % (term[0:4], term[7:9])

        url = ("http://wslwebservices.leg.wa.gov/SponsorService.asmx/"
               "GetSponsors?biennium=%s" % biennium)
        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page)

            for member in xpath(page, "//wa:Member"):
                mchamber = xpath(member, "string(wa:Agency)")
                mchamber = {'House': 'lower', 'Senate': 'upper'}[mchamber]

                if mchamber != chamber:
                    continue

                name = xpath(member, "string(wa:Name)")
                party = xpath(member, "string(wa:Party)")
                party = {'R': 'Republican', 'D': 'Democratic'}.get(
                    party, party)

                district = xpath(member, "string(wa:District)")
                email = xpath(member, "string(wa:Email)")
                leg_id = xpath(member, "string(wa:Id)")
                phone = xpath(member, "string(wa:Phone)")

                last = xpath(member, "string(wa:LastName)")
                last = last.lower().replace(' ', '')

                if chamber == 'upper':
                    leg_url = ("http://www.leg.wa.gov/senate/senators/"
                               "Pages/%s.aspx" % last)
                else:
                    leg_url = ("http://www.leg.wa.gov/house/"
                               "representatives/Pages/%s.aspx" % last)

                try:
                    with self.urlopen(leg_url) as leg_page:
                        leg_page = lxml.html.fromstring(leg_page)
                        leg_page.make_links_absolute(leg_url)

                        photo_link = leg_page.xpath(
                            "//a[contains(@href, 'publishingimages')]")
                        if photo_link:
                            photo_url = photo_link[0].attrib['href']
                except scrapelib.HTTPError:
                    # Sometimes the API and website are out of sync
                    # with respect to legislator resignations/appointments
                    photo_url = ''

                leg = Legislator(term, chamber, district,
                                 name, '', '', '', party, email=email,
                                 _code=leg_id, office_phone=phone,
                                 photo_url=photo_url)
                leg.add_source(leg_url)

                self.save_legislator(leg)
