import lxml.html
from collections import defaultdict

from pupa.scrape import Person, Scraper


class KYPersonScraper(Scraper):
    jurisdiction = 'ky'
    latest_only = True

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')

    def scrape_chamber(self, chamber):
        url = 'http://www.lrc.ky.gov/senate/senmembers.htm' if chamber == 'upper' else 'http://www.lrc.ky.gov/house/hsemembers.htm'
        page = self.get(url).text
        page = lxml.html.fromstring(page)

        for link in page.xpath('//a[@onmouseout="hidePicture();"]'):
            yield from self.scrape_member(chamber, year, link.get('href'))

    def scrape_office_info(self, url):
        ret = {}
        legislator_page = self.get(url).text
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
        member_page = self.get(member_url).text
        doc = lxml.html.fromstring(member_page)

        photo_url = doc.xpath('//div[@id="bioImage"]/img/@src')[0]
        name_pieces = doc.xpath('//span[@id="name"]/text()')[0].split()
        full_name = ' '.join(name_pieces[1:-1]).strip()

        party = name_pieces[-1]
        if party == '(R)':
            party = 'Republican'
        elif party == '(D)':
            party = 'Democratic'
        elif party == '(I)':
            party = 'Independent'

        district = doc.xpath('//span[@id="districtHeader"]/text()')[0].split()[-1]

        person = Person(name=full_name, district=district, party=party, primary_org=chamber, image=photo_url)
        person.add_source(member_url)
        person.add_link(member_url)

        address = '\n'.join(doc.xpath('//div[@id="FrankfortAddresses"]//span[@class="bioText"]/text()'))

        phone = None
        fax = None
        phone_numbers = doc.xpath('//div[@id="PhoneNumbers"]//span[@class="bioText"]/text()')
        for num in phone_numbers:
            if num.startswith('Annex: '):
                num = num.replace('Annex: ', '')
                if num.endswith(' (fax)'):
                    fax = num.replace(' (fax)', '')
                else:
                    phone = num

        emails = doc.xpath(
            '//div[@id="EmailAddresses"]//span[@class="bioText"]//a/text()'
        )
        email = reduce(
            lambda match, address: address if '@lrc.ky.gov' in str(address) else match,
            [None] + emails
        )

        if phone:
            person.add_contact_detail(type='voice', value=phone, note='Capitol Office')

        if email:
            person.add_contact_detail(type='email', value=email, note='Capitol Office')

        if address.strip() == "":
            self.warning("Missing Capitol Office!!")
        else:
            person.add_contact_detail(type='address', value=address, note='Capitol Office')

        yield person
