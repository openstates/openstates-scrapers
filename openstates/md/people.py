import re
from collections import defaultdict
import lxml.html

from pupa.scrape import Person, Scraper
def _get_table_item(doc, name):
    """ fetch items out of table that has a left column of th """
    return doc.xpath('//th[contains(text(), "%s")]/following-sibling::td' % name)[0]


class MDPersonScraper(Scraper):
    jurisdiction = 'md'
    latest_term = True

    def scrape(self, chambers=None):
        url = 'http://mgaleg.maryland.gov/webmga/frmmain.aspx?pid=legisrpage&tab=subject6'

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        sen_tbl, house_tbl = doc.xpath('//div[@class="legislrlist"]//table[@class="grid"]')
        if chambers == None:
            chambers = ['upper', 'lower']
        if 'upper' in chambers:
            yield from self.scrape_table('upper', sen_tbl)
        if 'lower' in chambers:
            yield from self.scrape_table('lower', house_tbl)

    def scrape_table(self, chamber, tbl):
        # skip first
        for row in tbl.xpath('tr')[1:]:
            leg_a, district, _, _ = row.xpath('td')
            district = district.text
            name = leg_a.text_content().strip()
            if name.lower() == "to be announced":
                continue
            leg_url = leg_a.xpath('a/@href')[0]

            # get details
            html = self.get(leg_url).text
            ldoc = lxml.html.fromstring(html)
            ldoc.make_links_absolute(leg_url)

            party = _get_table_item(ldoc, 'Party Affiliation:').text
            if party == 'Democrat':
                party = 'Democratic'
            addr_lines = _get_table_item(ldoc, 'Annapolis Address:').xpath('text()')
            address = []
            for line in addr_lines:
                if 'Phone:' not in line:
                    address.append(line)
                else:
                    phone = line
            address = '\n'.join(address)
            try:
                phone = re.findall('Phone: (\d{3}-\d{3}-\d{4})', phone)[0]
            except IndexError:
                self.warning("Missing phone!")
                phone = None

            email = ldoc.xpath('//a[contains(@href, "mailto:")]/text()')
            if not email:
                email = None
            elif len(email) == 1:
                email = email[0].strip()
            else:
                raise AssertionError('Multiple email links found on page')

            img_src = ldoc.xpath('//img[@class="sponimg"]/@src')
            if img_src:
                photo_url=img_src[0]

            leg = Person(
                primary_org=chamber,
                district=district,
                name=name,
                party=party,
                image=photo_url
            )
            leg.add_source(url=leg_url)
            leg.add_link(url=leg_url)


            # type ['address', 'email', 'url', 'fax', 'text', 'voice', 'video', 'pager', 'textphone']
            if address:
                leg.add_contact_detail(
                    type = 'address',
                    value= address or None,
                    note='Capitol Office'
                )
            if phone:
                leg.add_contact_detail(
                    type='voice',
                    value=phone,
                    note='Capitol Office'
                )

            if email:
                 leg.add_contact_detail(
                     type ='email',
                     value=email,
                     note='Capitol Office'
            );

            yield leg;