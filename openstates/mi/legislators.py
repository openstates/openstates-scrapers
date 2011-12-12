import re

from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

class MILegislatorScraper(LegislatorScraper):
    state = 'mi'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        abbr = {'D': 'Democratic', 'R': 'Republican'}

        if chamber == 'lower':
            url = 'http://house.michigan.gov/replist.asp'
            with self.urlopen(url) as html:
                doc = lxml.html.fromstring(html)
                doc.make_links_absolute(url)
                # skip two rows at top
                for row in doc.xpath('//table[@cellspacing=0]/tr')[2:]:
                    tds = row.xpath('td')
                    leg_url = tds[1].xpath('.//a/@href')[0]
                    tds = [x.text_content().strip() for x in tds]
                    (district, last_name, first_name,
                     party, office, phone, email) = tds
                    # vacancies
                    if last_name == 'District':
                        continue
                    leg = Legislator(term=term, chamber=chamber,
                                     district=str(int(district)),
                                     full_name=first_name + " " + last_name,
                                     first_name=first_name,
                                     last_name=last_name,
                                     party=abbr[party],
                                     office=office,
                                     phone=phone,
                                     email=email,
                                     leg_url=leg_url)
                    leg.add_source(url)
                    self.save_legislator(leg)
        else:
            url = 'http://www.senate.michigan.gov/members/memberlist.htm'
            with self.urlopen(url) as html:
                doc = lxml.html.fromstring(html)
                for row in doc.xpath('//table[@width=550]/tr')[1:39]:
                    # party, dist, member, office_phone, office_fax, office_loc
                    party = abbr[row.xpath('td[1]/text()')[0]]
                    district = row.xpath('td[2]/a/text()')[0]
                    leg_url = row.xpath('td[3]/a/@href')[0]
                    name = row.xpath('td[3]/a/text()')[0]
                    office_phone = row.xpath('td[4]/text()')[0]
                    office_fax = row.xpath('td[5]/text()')[0]
                    office_loc = row.xpath('td[6]/text()')[0]
                    leg = Legislator(term=term, chamber=chamber,
                                     district=district, full_name=name,
                                     party=party, office_phone=office_phone,
                                     url=leg_url,
                                     office_fax=office_fax,
                                     office_loc=office_loc)
                    leg.add_source(url)
                    self.save_legislator(leg)
