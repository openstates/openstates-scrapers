import re

from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

class MILegislatorScraper(LegislatorScraper):
    state = 'mi'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        abbr = {'D': 'Democratic', 'R': 'Republican'}

        if chamber == 'lower':
            with self.urlopen('http://house.michigan.gov/replist.asp') as html:
                doc = lxml.html.fromstring(html)
                # skip two rows at top
                for row in doc.xpath('//table[@cellspacing=0]/tr')[2:]:
                    tds = [x.text_content().strip() for x in row.xpath('td')]
                    (district, last_name, first_name,
                     party, office, phone, email) = tds
                    leg = Legislator(term=term, chamber=chamber,
                                     district=district,
                                     full_name=first_name + " " + last_name,
                                     first_name=first_name,
                                     last_name=last_name,
                                     party=party,
                                     office=office,
                                     phone=phone,
                                     email=email
                                    )
                    self.save_legislator(leg)
        else:
            with self.urlopen('http://www.senate.michigan.gov/members/memberlist.htm') as html:
                doc = lxml.html.fromstring(html)
                for row in doc.xpath('//table[@width=550]/tr')[1:39]:
                    # party, dist, member, office_phone, office_fax, office_loc
                    party = abbr[row.xpath('td[1]/text()')[0]]
                    district = row.xpath('td[2]/a/text()')[0]
                    name = row.xpath('td[3]/a/text()')[0]
                    office_phone = row.xpath('td[4]/text()')[0]
                    office_fax = row.xpath('td[5]/text()')[0]
                    office_loc = row.xpath('td[6]/text()')[0]
                    leg = Legislator(term=term, chamber=chamber,
                                     district=district, full_name=name,
                                     party=party, office_phone=office_phone,
                                     office_fax=office_fax,
                                     office_loc=office_loc)
                    self.save_legislator(leg)
