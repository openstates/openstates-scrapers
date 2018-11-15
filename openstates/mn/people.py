import collections
import logging
import lxml.html
import re

from pupa.scrape import Person, Scraper
from spatula import Page, CSV, Spatula
from openstates.utils import validate_phone_number, validate_email_address

PARTIES = {
    'DFL': 'Democratic-Farmer-Labor',
    'R': 'Republican',
}


class SenList(CSV):
    url = 'http://www.senate.mn/members/member_list_ascii.php?ls='
    _html_url = 'http://www.senate.mn/members/index.php'

    def __init__(self, scraper, url=None, *, obj=None, **kwargs):
        super().__init__(scraper, url=url, obj=obj, **kwargs)
        self._scrape_extra_info()

    def _scrape_extra_info(self):
        self.extra_info = collections.defaultdict(dict)

        resp = self.scraper.get(self._html_url)
        doc = lxml.html.fromstring(resp.text)
        doc.make_links_absolute(self._html_url)
        xpath = ('//div[@id="hide_show_alpha_all"]'
                 '//td[@style="vertical-align:top;"]')
        for td in doc.xpath(xpath):
            main_link, email_link = td.xpath('.//a')
            name = main_link.text_content().split(' (')[0]
            leg = self.extra_info[name]
            leg['office_phone'] = next(filter(
                lambda string: re.match(r'\d{3}-\d{3}-\d{4}', string),
                td.xpath('.//p/text()')
            )).strip()
            leg['url'] = main_link.get('href')
            leg['image'] = td.xpath('./preceding-sibling::td//img/@src')[0]
            if 'mailto:' in email_link.get('href'):
                leg['email'] = email_link.get('href').replace('mailto:', '')

        logger = logging.getLogger("pupa")
        logger.info('collected preliminary data on {} legislators'
                    .format(len(self.extra_info)))
        assert self.extra_info

    def handle_list_item(self, row):
        if not row['First Name']:
            return
        name = '{} {}'.format(row['First Name'], row['Last Name'])
        party = PARTIES[row['Party']]
        leg = Person(name=name, district=row['District'].lstrip('0'),
                     party=party, primary_org='upper', role='Senator',
                     image=self.extra_info[name]['image'])
        leg.add_link(self.extra_info[name]['url'])
        leg.add_contact_detail(type='voice',
                               value=self.extra_info[name]['office_phone'], note='capitol')
        if 'email' in self.extra_info[name]:
            leg.add_contact_detail(type='email',
                                   value=self.extra_info[name]['email'], note='capitol')

        row['Zipcode'] = row['Zipcode'].strip()
        # Accommodate for multiple address column naming conventions.
        address1_fields = [row.get('Address'), row.get('Office Building')]
        address2_fields = [row.get('Address2'), row.get('Office Address')]
        row['Address'] = next((a for a in address1_fields if a is not
                               None), False)
        row['Address2'] = next((a for a in address2_fields if a is not
                                None), False)

        if (a in row['Address2'] for a in ['95 University Avenue W',
                                           '100 Rev. Dr. Martin Luther King']):
            address = ('{Address}\n{Address2}\n{City}, {State} {Zipcode}'
                       .format(**row))
            if 'Rm. Number' in row:
                address = '{0} {1}'.format(row['Rm. Number'], address)
            leg.add_contact_detail(type='address', value=address,
                                   note='capitol')
        elif row['Address2']:
            address = ('{Address}\n{Address2}\n{City}, {State} {Zipcode}'
                       .format(**row))
            leg.add_contact_detail(type='address', value=address,
                                   note='district')
        else:
            address = '{Address}\n{City}, {State} {Zipcode}'.format(**row)
            leg.add_contact_detail(type='address', value=address,
                                   note='district')

        leg.add_source(self.url)
        leg.add_source(self._html_url)

        return leg

    def handle_page(self):
        yield super(SenList, self).handle_page()


class RepList(Page):
    url = 'http://www.house.leg.state.mn.us/members/hmem.asp'
    list_xpath = '//div[@id="hide_show_alpha_all"]/table/tr/td/table/tr'

    def handle_list_item(self, item):
        photo_url = item.xpath('./td[1]/a/img/@src')[0]
        info_nodes = item.xpath('./td[2]/p/a')
        name_text = info_nodes[0].xpath('./b/text()')[0]
        url = info_nodes[0].get('href')

        name_match = re.match(r'^(.+)\(([0-9]{2}[AB]), ([A-Z]+)\)$', name_text)
        name = name_match.group(1).strip()
        district = name_match.group(2).lstrip('0').upper()
        party_text = name_match.group(3)
        party = PARTIES[party_text]

        info_texts = [x.strip() for x in item.xpath(
            './td[2]/p/text()[normalize-space() and preceding-sibling::br]'
        ) if x.strip()]
        address = '\n'.join((info_texts[0], info_texts[1]))

        phone_text = info_texts[2]
        if validate_phone_number(phone_text):
            phone = phone_text

        email_node = info_nodes[1]
        email_text = email_node.text
        email_text = email_text.replace('Email: ', '').strip()
        if validate_email_address(email_text):
            email = email_text

        rep = Person(name=name, district=district, party=party,
                     primary_org='lower', role='Representative',
                     image=photo_url)
        rep.add_link(url)
        rep.add_contact_detail(type='address', value=address, note='capitol')
        rep.add_contact_detail(type='voice', value=phone, note='capitol')
        rep.add_contact_detail(type='email', value=email, note='capitol')
        rep.add_source(self.url)

        yield rep


class MNPersonScraper(Scraper, Spatula):
    def scrape(self):
        yield from self.scrape_page_items(SenList)
        yield from self.scrape_page_items(RepList)
