import re
from collections import defaultdict

from billy.scrape.legislators import Legislator, LegislatorScraper

import lxml.html


class KYLegislatorScraper(LegislatorScraper):
    state = 'ky'
    latest_only = True

    def scrape(self, chamber, year):

        if chamber == 'upper':
            leg_list_url = 'http://www.lrc.ky.gov/senate/senmembers.htm'
        else:
            leg_list_url = 'http://www.lrc.ky.gov/house/hsemembers.htm'

        with self.urlopen(leg_list_url) as page:
            page = lxml.html.fromstring(page)

        for link in page.xpath('//a[@onmouseout="hidePicture();"]'):
            self.scrape_member(chamber, year, link.get('href'))

    def scrape_office_info(self, url):
        ret = {}
        with self.urlopen(url) as legislator_page:
            legislator_page = lxml.html.fromstring(legislator_page)
        legislator_page.make_links_absolute(url)
        info = legislator_page.xpath("//table//span")
        for span in info:
            elements = span.xpath("./*")
            if len(elements) < 1:
                continue
            if elements[0].tag != "b":
                continue
            txt = elements[0].text_content().strip()

            if txt == "Bio" or \
               "committees" in txt.lower() or \
               "service" in txt.lower() or \
               txt == "":
                continue

            def _handle_phone(obj):
                ret = defaultdict(list)
                for x in obj.xpath(".//*")[:-1]:
                    phone = x.tail.strip()
                    obj = phone.split(":", 1)
                    if len(obj) != 2:
                        continue
                    typ, number = obj
                    typ, number = typ.strip(), number.strip()
                    ret[typ].append(number)
                return ret

            def _handle_address(obj):
                addr = " ".join([x.tail or "" for x in obj.xpath(".//*")[1:]])
                return [addr.strip()]

            def _handle_emails(obj):
                ret = []
                emails = obj.xpath(".//a[contains(@href, 'mailto')]")
                if len(emails) < 1:
                    return []
                for email in emails:
                    _, efax = email.attrib['href'].split(":", 1)
                    ret.append(efax)
                return ret

            handlers = {
                "Mailing Address": _handle_address,
                "Frankfort Address(es)": _handle_address,
                "Phone Number(s)": _handle_phone,
                "Email Address(es)": _handle_emails
            }

            try:
                handler = handlers[txt]
                ret[txt] = handler(span)
            except KeyError:
                pass

        return ret

    def scrape_member(self, chamber, year, member_url):
        with self.urlopen(member_url) as member_page:
            member = {}
            member_root = lxml.html.fromstring(member_page)

            table = member_root.xpath('//body/div[2]/table')[0]
            imgtag = member_root.xpath('//body/div[2]/table//img')

            member['photo_url'] = imgtag[0].get('src')
            name_list = table.xpath('string(.//strong[1])').split(' ')
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
                    if 'additionalRoles' in member:
                        member['additionalRoles'].append(item)
                    else:
                        member['additionalRoles'] = [item]

            contact_rows = member_root.xpath(
                '//body/div[2]/div[1]/table/tr/td/table[1]/tr')

            for row in contact_rows:
                row_text = self.get_child_text(row)

                if len(row_text) > 0:
                    if row_text[0] == 'Frankfort Address(es)':
                        member['office_address'] = '\n'.join(row_text[1:])

                    if row_text[0] == 'Phone Number(s)':
                        for item in row_text:
                            # Use the first capitol annex phone
                            if item.startswith('Annex:'):
                                member['office_phone'] = item.replace(
                                    'Annex:', '').strip()
                                break

            office_info = self.scrape_office_info(member_url)

            leg = Legislator(year, chamber, member['district'],
                             member['full_name'],
                             party=member['party'],
                             photo_url=member['photo_url'],
                             url=member_url,
                             office_address=member['office_address'],
                             office_phone=member['office_phone'])
            leg.add_source(member_url)

            kwargs = {}
            if office_info['Email Address(es)'] != []:
                kwargs['email'] = office_info['Email Address(es)'][0]
                leg['email'] = office_info['Email Address(es)'][0]

            if office_info['Phone Number(s)']['Annex'] != []:
                kwargs['phone'] = office_info['Phone Number(s)']['Annex'][0]

            if office_info['Frankfort Address(es)'] != []:
                kwargs['address'] = office_info['Frankfort Address(es)'][0]

            if kwargs != {}:
                leg.add_office('capitol',
                               'Annex Office',
                               **kwargs)

            if 'additionalRoles' in member:
                for role in member['additionalRoles']:
                    leg.add_role(role, year, chamber=chamber)

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
