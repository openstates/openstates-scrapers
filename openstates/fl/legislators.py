import re
import urlparse

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class FLLegislatorScraper(LegislatorScraper):
    jurisdiction = 'fl'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'upper':
            self.scrape_senators(term)
        else:
            self.scrape_reps(term)

    def scrape_sen_offices(self, leg, leg_url):
        doc = lxml.html.fromstring(self.get(leg_url).text)
        email = doc.xpath('//a[contains(@href, "mailto:")]')[0].get('href').split(':')[-1]
        PHONE_RE = r'\(\d{3}\)\s\d{3}\-\d{4}'

        offices = doc.xpath('//h4[contains(text(), "Office")]')
        for office in offices:

            (name, ) = office.xpath('text()')
            if name == "Tallahassee Office":
                type_ = 'capitol'
            else:
                type_ = 'district'

            address_lines = [
                    x.strip() for x in
                    office.xpath('following-sibling::div[1]/text()')
                    if x.strip()
                    ]

            if re.search(PHONE_RE, address_lines[-1]):
                phone = address_lines.pop()
            else:
                phone = None
            if re.search(r'(?i)open\s+\w+day', address_lines[0]):
                address_lines = address_lines[1: ]
            assert ", FL" in address_lines[-1]
            address = "\n".join(address_lines)
            address = re.sub(r'\s{2,}', " ", address)

            leg.add_office(
                    type=type_,
                    name=name,
                    address=address,
                    phone=phone,
                    email=email if type_ == 'capitol' else None
                    )

    def scrape_senators(self, term):
        url = "http://www.flsenate.gov/Senators/"
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, 'Senators/s')]"):
            name = " ".join(link.xpath('.//text()'))
            name = re.sub(r'\s+', " ", name).replace(" ,", ",").strip()
            leg_url = link.get('href')
            leg_doc = lxml.html.fromstring(self.get(leg_url).text)
            leg_doc.make_links_absolute(leg_url)

            if 'Vacant' in name:
                continue

            district = link.xpath("string(../../td[1])")
            party = link.xpath("string(../../td[2])")

            # for consistency
            if party == 'Democrat':
                party = 'Democratic'

            photo_url = leg_doc.xpath('//div[@id="sidebar"]//img/@src').pop()

            leg = Legislator(term, 'upper', district, name,
                             party=party, photo_url=photo_url, url=leg_url)
            leg.add_source(url)
            leg.add_source(leg_url)

            self.scrape_sen_offices(leg, leg_url)

            self.save_legislator(leg)

    def scrape_rep_office(self, leg, doc, name):
        pieces = [x.tail.strip() for x in
                  doc.xpath('//strong[text()="%s"]/following-sibling::br' %
                            name)]
        if not pieces:
            return
        address = []
        for piece in pieces:
            if piece.startswith('Phone:'):
                # 'Phone: \r\n        (303) 222-2222'
                if re.search(r'\d+', piece):
                    phone = piece.split(None, 1)[1]
                else:
                    phone = None
            else:
                piece = re.sub(r'\s+', ' ', piece)
                address.append(piece)

        office = dict(name=name, address='\n'.join(address))

        # Phone
        if phone is not None:
            office['phone'] = phone

        # Type
        if 'Capitol' in name:
            office['type'] = 'capitol'
        elif 'District' in name:
            office['type'] = 'district'

        leg.add_office(**office)

    def scrape_reps(self, term):
        url = ("http://www.flhouse.gov/Sections/Representatives/"
               "representatives.aspx")

        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for div in page.xpath('//div[@class="rep_listing1"]'):
            link = div.xpath('.//div[@class="rep_style"]/a')[0]
            name = link.text_content().strip()
            term_details = div.xpath(
                './/div[@class="term_style"]')[0].text_content()
            if 'Resigned' in term_details:
                continue

            party = div.xpath('.//div[@class="party_style"]/text()')[0].strip()
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'
            else:
                raise NotImplementedError(
                        "Unknown party found: {}".format(party))

            district = div.xpath(
                    './/div[@class="district_style"]/text()')[0].strip()

            leg_url = link.get('href')
            split_url = urlparse.urlsplit(leg_url)
            member_id = urlparse.parse_qs(split_url.query)['MemberId'][0]
            photo_url = ("http://www.flhouse.gov/FileStores/Web/"
                         "Imaging/Member/%s.jpg" % member_id)

            leg = Legislator(term, 'lower', district, name,
                             party=party, photo_url=photo_url, url=leg_url)

            # offices
            leg_doc = lxml.html.fromstring(self.get(leg_url).text)
            self.scrape_rep_office(leg, leg_doc, 'Capitol Office')
            self.scrape_rep_office(leg, leg_doc, 'District Office')

            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)
