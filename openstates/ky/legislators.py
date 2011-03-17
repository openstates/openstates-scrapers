import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import Legislator, LegislatorScraper

import lxml.html


class KYLegislatorScraper(LegislatorScraper):
    state = 'ky'

    def scrape(self, chamber, year):

        if year != self.metadata['terms'][-1]['name']:
            # Data only available for current term
            raise NoDataForPeriod(year)

        if chamber == 'upper':
            leg_list_url = 'http://www.lrc.ky.gov/senate/senmembers.htm'
        else:
            leg_list_url = 'http://www.lrc.ky.gov/house/hsemembers.htm'

        with self.urlopen(leg_list_url) as page:
            page = lxml.html.fromstring(page)

        for link in page.xpath('//a[@onmouseout="hideImg();"]'):
            self.scrape_member(chamber, year, link.get('href'))

    def scrape_member(self, chamber, year, member_url):

        with self.urlopen(member_url) as member_page:

            member = {}
            member_root = lxml.html.fromstring(member_page)

            table = member_root.xpath('//body/div[2]/table')[0]

            imgtag = member_root.xpath('//body/div[2]/table//img')

            member['photo_url'] = imgtag[0].get('src')

            name_list = [mem.text for mem in table.iterdescendants(tag='strong')][0].split(' ')

            member['full_name'] = ' '.join(name_list[1:-1]).strip()

            party = name_list[-1]
            party = re.sub(r'\(|\)', '', party)
            if party == 'R':
                party = 'Republican'
            elif party == 'D':
                party = 'Democratic'
            elif party == 'I':
                party = 'Independent'

            member['party'] = party

            boldList = [bold.text for bold in table.iterdescendants(tag='b')]

            for item in boldList:
                if item == None:
                    continue
                elif 'District' in item:
                    district = item.split(' ')[-1]
                    member['district'] = district.strip()
                else:
                    if member.has_key('additionalRoles'):
                        member['additionalRoles'].append(item)
                    else:
                        member['additionalRoles'] = [item]

            contact_rows = member_root.xpath('//body/div[2]/div[1]/table/tr/td/table[1]/tr')

            for row in contact_rows:
                row_text = self.get_child_text(row)
                
                if len(row_text) > 0: 
                    if row_text[0] == 'Frankfort Address(es)':
                        member['office_address'] = '\n'.join(row_text[1:])

                    if row_text[0] == 'Phone Number(s)':
                        for item in row_text:
                            # Use the first capitol annex phone
                            if item.startswith('Annex:'):
                                member['office_phone'] = item.replace('Annex:', '').strip()
                                break

            leg = Legislator(year, chamber, member['district'], member['full_name'], 
                            party=member['party'], photo_url=member['photo_url'],
                            office_address=member['office_address'], 
                            office_phone=member['office_phone'])
            leg.add_source(member_url)

            if member.has_key('additionalRoles'):
                for role in member['additionalRoles']:
                    leg.add_role(role, year)

            self.save_legislator(leg)

    


    def get_child_text(self, node):

        text = []

        for item in node.iterdescendants():
            if item.text != None:
                if len(item.text.strip()) > 0:
                    text.append(item.text.strip())
            if item.tail != None:
                if len(item.tail.strip()) > 0:
                    text.append(item.tail.strip())
        return text

