import re

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

abbr = {'D': 'Democratic', 'R': 'Republican'}


class MILegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'mi'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)
        if chamber == 'lower':
            return self.scrape_lower(chamber, term)
        return self.scrape_upper(chamber, term)

    def scrape_lower(self, chamber, term):
        url = 'http://www.house.mi.gov/mhrpublic/frmRepList.aspx'
        table = [
            "website",
            "district",
            "name",
            "party",
            "location",
            "phone",
            "email"
        ]
        doc = self.lxmlize(url)
        # skip two rows at top
        for row in doc.xpath('//table[@id="grvRepInfo"]/*'):
            tds = row.xpath('.//td')
            if len(tds) == 0:
                continue
            metainf = {}
            for i in range(0, len(table)):
                metainf[table[i]] = tds[i]
            district = str(int(metainf['district'].text_content().strip()))
            party = metainf['party'].text_content().strip()
            phone = metainf['phone'].text_content().strip()
            email = metainf['email'].text_content().strip()
            leg_url = metainf['website'].xpath("./a")[0].attrib['href']
            name = metainf['name'].text_content().strip()
            if name == 'Vacant' or re.match(r'^District \d{1,3}$', name):
                self.warning('District {} appears vacant, and will be skipped'.format(district))
                continue

            office = metainf['location'].text_content().strip()
            office = re.sub(
                    ' HOB',
                    ' Anderson House Office Building\n124 North Capitol Avenue\nLansing, MI 48933',
                    office
                    )
            office = re.sub(
                    ' CB',
                    ' State Capitol Building\nLansing, MI 48909',
                    office
                    )

            leg = Legislator(term=term,
                             chamber=chamber,
                             full_name=name,
                             district=district,
                             party=abbr[party],
                             url=leg_url)

            leg.add_office('capitol', 'Capitol Office',
                           address=office,
                           phone=phone,
                           email=email)

            leg.add_source(url)
            self.save_legislator(leg)

    def scrape_upper(self, chamber, term):
        url = 'http://www.senate.michigan.gov/senatorinfo.html'
        doc = self.lxmlize(url)
        for row in doc.xpath('//table[not(@id="calendar")]//tr')[3:]:
            if len(row) != 6:
                continue

            # party, dist, member, office_phone, office_fax, office_loc
            party, dist, member, phone, fax, loc = row.getchildren()
            if (party.text_content().strip() == "" or
                    'Lieutenant Governor' in member.text_content()):
                continue

            party = abbr[party.text]
            district = dist.text_content().strip()
            name = member.text_content().strip()
            name = re.sub(r'\s+', " ", name)

            if name == 'Vacant':
                self.info('district %s is vacant', district)
                continue

            leg_url = member.xpath('a/@href')[0]
            office_phone = phone.text
            office_fax = fax.text
            
            office_loc = loc.text
            office_loc = re.sub(
                    ' Farnum Bldg',
                    ' Farnum Office Building\n125 West Allegan Street\nLansing, MI 48933',
                    office_loc
                    )
            office_loc = re.sub(
                    ' Capitol Bldg',
                    ' State Capitol Building\nLansing, MI 48909',
                    office_loc
                    )

            leg = Legislator(term=term, chamber=chamber,
                             district=district,
                             full_name=name,
                             party=party,
                             url=leg_url)

            leg.add_office('capitol', 'Capitol Office',
                           address=office_loc,
                           fax=office_fax,
                           phone=office_phone)

            leg.add_source(url)
            self.save_legislator(leg)
