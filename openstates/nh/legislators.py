import re
import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

from .utils import db_cursor


class NHLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'nh'
    latest_only = True

    chamber_map = {'H': 'lower', 'S': 'upper'}
    inverse_chamber_map = {v: k for k, v in chamber_map.items()}
    party_map = {'D': 'Democratic', 'R': 'Republican', 'I': 'Independent'}

    def __init__(self, *args, **kwargs):
        super(LegislatorScraper, self).__init__(*args, **kwargs)
        self.cursor = db_cursor()

    def _get_photo(self, url, chamber):
        doc = self.lxmlize(url)

        if chamber == 'upper':
            src = doc.xpath('//div[@id="page_content"]//img[contains(@src, '
                '"images/senators") or contains(@src, "Senator")]/@src')
        elif chamber == 'lower':
            src = doc.xpath('//img[contains(@src, "images/memberpics")]/@src')

        if src and 'nophoto' not in src[0]:
            photo_url = src[0]
        else:
            photo_url = ''

        return photo_url

    def scrape(self, chamber, term):
        chamber_code = NHLegislatorScraper.inverse_chamber_map[chamber]

        self.cursor.execute("SELECT "
            "Legislators.Employeeno AS employee_no, "
            "Legislators.LastName AS last_name, "
            "Legislators.FirstName AS first_name, "
            "Legislators.MiddleName AS middle_name, "
            "Legislators.LegislativeBody AS chamber, "
            "County.County AS county, "
            "Legislators.District AS district_no, "
            "Legislators.party AS party, "
            "Legislators.street AS address1, "
            "Legislators.address2 AS address2, "
            "Legislators.city AS city, "
            "Legislators.state AS state, "
            "Legislators.zipcode AS zipcode, "
            "Legislators.HomePhone AS phone, "
            "Legislators.EMailAddress AS email "
            "FROM Legislators LEFT OUTER JOIN County "
            "ON Legislators.countycode = County.CountyID "
            "WHERE LegislativeBody = '{}' AND Legislators.Active = 1 "
            "ORDER BY Legislators.LegislativeBody ASC, "
            "Legislators.District ASC".format(chamber_code))

        for row in self.cursor.fetchall():
            first_name = row['first_name']
            middle_name = row['middle_name']
            last_name = row['last_name']

            full_name = '{} {} {}'.format(first_name, middle_name, last_name)
            full_name = re.sub(r'[\s]{2,}', ' ', full_name)

            district = '{} {}'.format(row['county'], int(row['district_no']))
            party = NHLegislatorScraper.party_map[row['party']]
            email = row['email'] or ''

            legislator = Legislator(term, chamber, district, full_name,
                first_name=first_name, last_name=last_name,
                middle_name=middle_name, party=party, email=email)

            district_address = '{}\n{}\n{}, {} {}'.format(row['address1'],
                row['address2'], row['city'], row['state'], row['zipcode'])\
                .strip()
            home_phone = row['phone']

            legislator.add_office('district', 'Home Address',
                address=district_address, phone=home_phone or None)

            profile_url = None
            if chamber == 'upper':
                profile_url = 'http://www.gencourt.state.nh.us/Senate/members'\
                    '/webpages/district{}.aspx'.format(row['district_no'])
            elif chamber == 'lower':
                profile_url = 'http://www.gencourt.state.nh.us/house/members/'\
                    'member.aspx?member={}'.format(row['employee_no'])

            if profile_url:
                legislator['photo_url'] = self._get_photo(profile_url, chamber)
                legislator.add_source(profile_url)

            self.save_legislator(legislator)
