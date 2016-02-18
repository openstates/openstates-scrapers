import re
import lxml.html
import scrapelib
from billy.scrape.legislators import Legislator, LegislatorScraper
from openstates.utils import LXMLMixin


class NELegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ne'
    latest_only = True

    def scrape(self, term, chambers):
        base_url = 'http://news.legislature.ne.gov/dist'

        #there are 49 districts
        for district in range(1, 50):
            rep_url = base_url + str(district).zfill(2)

            full_name = None
            address   = None
            phone     = None
            email     = None
            photo_url = None

            try:
                page = self.lxmlize(rep_url)

                info_node = self.get_node(page,
                    '//div[@class="container view-front"]'
                    '//div[@class="col-sm-4 col-md-3 ltc-col-right"]'
                    '/div[@class="block-box"]')

                full_name = self.get_node(
                    info_node,
                    './h2/text()[normalize-space()]')
                full_name = re.sub(r'^Sen\.[\s]+', '', full_name).strip()
                if full_name == 'Seat Vacant':
                    continue

                address_node = self.get_node(
                    info_node,
                    './address[@class="feature-content"]')

                email = self.get_node(
                    address_node,
                    './a[starts-with(@href, "mailto:")]/text()')

                contact_text_nodes = self.get_nodes(
                    address_node,
                    './text()[following-sibling::br]')

                address_sections = []
                for text in contact_text_nodes:
                    text = text.strip()

                    if not text:
                        continue

                    phone_match = re.search(r'Phone:', text)

                    if phone_match:
                        phone = re.sub('^Phone:[\s]+', '', text)
                        continue

                    # If neither a phone number nor e-mail address.
                    address_sections.append(text)

                address = '\n'.join(address_sections)

                photo_url =\
                    'http://www.nebraskalegislature.gov/media/images/blogs'\
                    '/dist{:2d}.jpg'.format(district)

                # Nebraska is offically nonpartisan.
                party = 'Nonpartisan'

                leg = Legislator(term, 'upper', str(district), full_name,
                                 party=party, url=rep_url, photo_url=photo_url)
                if email:
                    leg['email'] = email

                leg.add_source(rep_url)
                leg.add_office('capitol', 'Capitol Office', address=address,
                    phone=phone, email=email)

                self.save_legislator(leg)
            except scrapelib.HTTPError:
                self.warning('could not retrieve %s' % rep_url)
