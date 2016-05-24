import csv
import re
import lxml.html
from collections import defaultdict
from cStringIO import StringIO
from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod
from openstates.utils import LXMLMixin, validate_phone_number,\
    validate_email_address


class MNLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'mn'

    _parties = {
        'DFL': 'Democratic-Farmer-Labor',
        'R': 'Republican',
    }

    def scrape(self, chamber, term):
        getattr(self, '_scrape_' + chamber + '_chamber')(term)

    def _scrape_lower_chamber(self, term):
        url = 'http://www.house.leg.state.mn.us/members/hmem.asp'

        page = self.lxmlize(url)

        legislator_nodes = self.get_nodes(
            page,
            '//div[@id="hide_show_alpha_all"]/table/tr/td/table/tr')

        for legislator_node in legislator_nodes:
            photo_url = self.get_node(
                legislator_node,
                './td[1]/a/img/@src')

            info_nodes = self.get_nodes(
                legislator_node,
                './td[2]/p/a')

            name_text = self.get_node(
                info_nodes[0],
                './b/text()')

            name_match = re.search(r'^.+\(', name_text)
            name = name_match.group(0)
            name = name.replace('(', '').strip()

            district_match = re.search(r'\([0-9]{2}[A-Z]', name_text)
            district_text = district_match.group(0)
            district = district_text.replace('(', '').lstrip('0').strip()

            party_match = re.search(r'[A-Z]+\)$', name_text)
            party_text = party_match.group(0)
            party_text = party_text.replace(')', '').strip()
            party = self._parties[party_text]

            info_texts = self.get_nodes(
                legislator_node,
                './td[2]/p/text()[normalize-space() and preceding-sibling'
                '::br]')
            address = '\n'.join((info_texts[0], info_texts[1]))

            phone_text = info_texts[2]
            if validate_phone_number(phone_text):
                phone = phone_text

            email_node = info_nodes[1]
            email_text = email_node.text

            email_text = email_text.replace('Email: ', '').strip()
            if validate_email_address(email_text):
                email = email_text

            legislator = Legislator(
                term=term,
                chamber='lower',
                district=district,
                full_name=name,
                party=party,
                email=email,
                photo_url=photo_url,
            )
            legislator.add_source(url)

            legislator.add_office(
                type='capitol',
                name="Capitol Office",
                address=address,
                phone=phone,
                email=email,
             )

            self.save_legislator(legislator)

    def _scrape_upper_chamber(self, term):
        index_url = 'http://www.senate.mn/members/index.php'
        doc = lxml.html.fromstring(self.get(index_url).text)
        doc.make_links_absolute(index_url)

        leg_data = defaultdict(dict)

        # get all the tds in a certain div
        tds = doc.xpath('//div[@id="hide_show_alpha_all"]//td[@style="vertical-align:top;"]')
        for td in tds:
            # each td has 2 <a>s- site & email
            main_link, email = td.xpath('.//a')
            # get name
            name = main_link.text_content().split(' (')[0]
            leg = leg_data[name]
            leg['office_phone'] = filter(
                lambda string: re.match(r'\d{3}-\d{3}-\d{4}', string),
                td.xpath('.//p/text()'))[0].strip()
            leg['url'] = main_link.get('href')
            leg['photo_url'] = td.xpath('./preceding-sibling::td//img/@src')[0]
            if 'mailto:' in email.get('href'):
                leg['email'] = email.get('href').replace('mailto:', '')

        self.info('collected preliminary data on %s legislators', len(leg_data))
        assert leg_data

        # use CSV for most of data
        csv_url = 'http://www.senate.mn/members/member_list_ascii.php?ls='
        csvfile = self.get(csv_url).text

        for row in csv.DictReader(StringIO(csvfile)):
            if not row['First Name']:
                continue
            name = '%s %s' % (row['First Name'], row['Last Name'])
            party = self._parties[row['Party']]
            leg_data[name]
            if 'email' in leg_data[name]:
                email = leg_data[name].pop('email')
            else:
                email = None
            leg = Legislator(term, 'upper', row['District'].lstrip('0'), name,
                             party=party,
                             first_name=row['First Name'],
                             last_name=row['Last Name'],
                             **leg_data[name]
                            )
            row["Zipcode"] = row["Zipcode"].strip()

            # Accommodate for multiple address column naming conventions.
            address1_fields = [row.get('Address'), row.get('Office Building')]
            address2_fields = [row.get('Address2'), row.get('Office Address')]
            row['Address'] = next((a for a in address1_fields if a is not
                None), False)
            row['Address2'] = next((a for a in address2_fields if a is not
                None), False)

            if (a in row['Address2'] for a in ['95 University Avenue W', '100 Rev. Dr. Martin Luther King']):
                address = '{Address}\n{Address2}\n{City}, {State} {Zipcode}'.format(**row)
                if 'Rm. Number' in row:
                    address = '{0} {1}'.format(row['Rm. Number'], address)
                leg.add_office('capitol', 'Capitol Office',
                    address=address,
                    email=email, phone=leg.get('office_phone'))
            elif row['Address2']:
                leg.add_office('district', 'District Office',
                    address='{Address}\n{Address2}\n{City}, {State} {Zipcode}'.format(**row),
                    email=email)
            else:
                leg.add_office('district', 'District Office',
                    address='{Address}\n{City}, {State} {Zipcode}'.format(**row),
                    email=email)

            leg.add_source(csv_url)
            leg.add_source(index_url)

            self.save_legislator(leg)
