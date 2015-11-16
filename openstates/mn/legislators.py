import csv
import re
import lxml.html
from collections import defaultdict
from cStringIO import StringIO
from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod
from openstates.utils import LXMLMixin


class MNLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'mn'

    _parties = {
        'DFL': 'Democratic-Farmer-Labor',
        'R': 'Republican',
    }

    def _get_node(self, base_node, xpath_query):
        """
        Attempts to return only the first node found for an xpath query. Meant
        to cut down on exception handling boilerplate.
        """
        try:
            node = base_node.xpath(xpath_query)[0]
        except IndexError:
            node = None

        return node

    def _get_nodes(self, base_node, xpath_query):
        """
        Attempts to return all nodes found for an xpath query. Meant to cut
        down on exception handling boilerplate.
        """
        try:
            nodes = base_node.xpath(xpath_query)
        except IndexError:
            nodes = None

        return nodes

    def _validate_phone_number(self, phone_number):
        is_valid = False

        # Phone format validation regex.
        phone_pattern = re.compile(r'\(?\d{3}\)?\s?-?\d{3}-?\d{4}')
        phone_match = phone_pattern.match(phone_number)
        if phone_match is not None:
            is_valid = True

        return is_valid

    def _validate_email_address(self, email_address):
        is_valid = False

        email_pattern = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.'
            r'[a-zA-Z]{2,}\b')
        email_match = email_pattern.match(email_address)
        if email_match is not None:
            is_valid = True

        return is_valid

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber + '_chamber')(term)

    def scrape_lower_chamber(self, term):
        url = 'http://www.house.leg.state.mn.us/members/hmem.asp'

        page = self.lxmlize(url)

        legislator_nodes = self._get_nodes(
            page,
            '//div[@id="hide_show_alpha_all"]/table/tr/td/table/tr')

        for legislator_node in legislator_nodes:
            photo_url = self._get_node(
                legislator_node,
                './td[1]/a/@href')

            info_nodes = self._get_nodes(
                legislator_node,
                './td[2]/p/a')
            #self.logger.debug(info_nodes)

            name_text = self._get_node(
                info_nodes[0],
                './b/text()')
            self.logger.debug(name_text)

            name_match = re.search(r'^.+\(', name_text)
            name = name_match.group(0)
            name = name.replace('(', '').strip()
            self.logger.debug('name: ' + name)

            district_match = re.search(r'\([0-9]{2}[A-Z]', name_text)
            district_text = district_match.group(0)
            district = district_text.replace('(', '').strip()
            self.logger.debug('district: ' + district)

            party_match = re.search(r'[A-Z]+\)$', name_text)
            party_text = party_match.group(0)
            party_text = party_text.replace(')', '').strip()
            party = self._parties[party_text]
            self.logger.debug('party: ' + party)

            info_texts = self._get_nodes(
                legislator_node,
                './td[2]/p/text()[preceding-sibling::br]')
            address = '\n'.join((info_texts[0], info_texts[1]))
            self.logger.debug(address)

            phone_text = info_texts[2]
            if self._validate_phone_number(phone_text):
                phone = phone_text
            self.logger.debug('phone: ' + phone)

            # E-mail markup is screwed-up and inconsistent.
            try:
                email_node = info_nodes[1]
                email_text = email_node.text
            except IndexError:
                # Primarily for Dan Fabian.
                email_node = info_texts[4]
                self.logger.debug(info_texts)

            email_text = email_text.replace('Email: ', '').strip()
            if self._validate_email_address(email_text):
                email = email_text
            self.logger.debug('email: ' + email)

            legislator = Legislator(
                term=term,
                chamber='lower',
                district=district,
                full_name=name,
                party=party,
                email=email,
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

    def scrape_upper_chamber(self, term):
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
            leg['leg_url'] = main_link.get('href')
            leg['photo_url'] = td.xpath('./preceding-sibling::td/a/img/@src')[0]
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
            
            if 'Martin Luther King' in row['Address2']:\
                leg.add_office('capitol', 'Capitol Office',
                           address='{Address}\n{Address2}\n{City}, {State} {Zipcode}'.format(**row),
                           email=email)
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
