from .utils import xpath
from billy.scrape.legislators import LegislatorScraper, Legislator

import scrapelib
import lxml.html
import lxml.etree


class WALegislatorScraper(LegislatorScraper):
    jurisdiction = 'wa'

    def scrape(self, chamber, term):
        biennium = "%s-%s" % (term[0:4], term[7:9])

        url = ("http://wslwebservices.leg.wa.gov/SponsorService.asmx/"
               "GetSponsors?biennium=%s" % biennium)

        # these pages are useful for checking if a leg is still in office
        if chamber == 'upper':
            cur_members = self.urlopen('http://www.leg.wa.gov/senate/senators/Pages/default.aspx')
        else:
            cur_members = self.urlopen('http://www.leg.wa.gov/house/representatives/Pages/default.aspx')

        with self.urlopen(url) as page:
            page = lxml.etree.fromstring(page.bytes)

            for member in xpath(page, "//wa:Member"):
                mchamber = xpath(member, "string(wa:Agency)")
                mchamber = {'House': 'lower', 'Senate': 'upper'}[mchamber]

                if mchamber != chamber:
                    continue

                name = xpath(member, "string(wa:Name)")

                # if the legislator isn't in the listing, skip them
                if name not in cur_members:
                    self.warning('%s is no longer in office' % name)
                    continue

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
                scraped_offices = []

                try:
                    with self.urlopen(leg_url) as leg_page:
                        leg_page = lxml.html.fromstring(leg_page)
                    leg_page.make_links_absolute(leg_url)

                    photo_link = leg_page.xpath(
                        "//a[contains(@href, 'publishingimages')]")
                    if photo_link:
                        photo_url = photo_link[0].attrib['href']
                    offices = leg_page.xpath("//table[@cellspacing='0']/tr/td/b[contains(text(), 'Office')]")
                    for office in offices:
                        office_block = office.getparent()
                        office_name = office.text_content().strip().rstrip(":")
                        address_lines = [x.tail for x in office_block.xpath(".//br")]
                        address_lines = filter(lambda a: a is not None, address_lines)
                        phone = address_lines.pop(len(address_lines) - 1)
                        address = "\n".join(address_lines)
                        obj = {
                            "name": office_name,
                            "phone": phone
                        }
                        if address.strip() != '':
                            obj['address'] = address

                        scraped_offices.append(obj)
                except scrapelib.HTTPError:
                    # Sometimes the API and website are out of sync
                    # with respect to legislator resignations/appointments
                    photo_url = ''

                leg = Legislator(term, chamber, district,
                                 name, '', '', '', party,
                                 _code=leg_id,
                                 photo_url=photo_url, url=leg_url)
                leg.add_source(leg_url)

                for office in scraped_offices:
                    typ = 'district' if 'District' in office['name'] else 'capitol'
                    leg.add_office(typ, office.pop('name'),
                                   **office)

                self.save_legislator(leg)
