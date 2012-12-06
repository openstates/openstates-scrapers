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
        doc = lxml.html.fromstring(self.urlopen(leg_url))
        email = doc.xpath('//a[contains(@href, "mailto:")]')[0].get('href').split(':')[-1]
        leg['email'] = email

        # order of this page is
        # h3 - District Offices
        # p - office info
        # h4 - Legislative Assistant
        # p - legislative assistant
        # (repeat)
        # h3 - Tallahassee Office
        # p - office info
        skip_next_p = False
        office_type = 'district'
        office_name = 'District Office'
        for elem in doc.xpath('//h3[contains(text(), "District Office")]/following-sibling::*'):
            if elem.tag == 'p' and elem.text_content().strip():
                # skip legislative assistants
                if skip_next_p:
                    skip_next_p = False
                    continue
                # not skipping, parse the office
                address = []
                phone = None
                fax = None
                for line in elem.xpath('text()'):
                    line = line.strip()
                    if line.startswith('('):
                        phone = line
                    elif line.startswith('FAX '):
                        fax = line[4:]
                    elif line.startswith(('Senate VOIP', 'Statewide')):
                        continue
                    else:
                        address.append(line)
                # done parsing address
                leg.add_office(office_type, office_name,
                               address='\n'.join(address), phone=phone,
                               fax=fax)
            elif elem.tag == 'h4':
                skip_next_p = True
            elif elem.tag == 'h3' and elem.text == 'Tallahassee Office:':
                office_type = 'capitol'
                office_name = 'Tallahassee Office'

    def scrape_senators(self, term):
        url = "http://www.flsenate.gov/Senators/"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'Senators/s')]"):
                name = link.text.strip()
                name = re.sub(r'\s+', ' ', name)
                leg_url = link.get('href')

                if 'Vacant' in name:
                    continue

                # Special case - name_tools gets confused
                # by 'JD', thinking it is a suffix instead of a first name
                if name == 'Alexander, JD':
                    name = 'JD Alexander'
                elif name == 'Vacant':
                    name = 'Vacant Seat'

                district = link.xpath("string(../../td[1])")
                party = link.xpath("string(../../td[2])")

                # for consistency
                if party == 'Democrat':
                    party = 'Democratic'

                photo_url = ("http://www.flsenate.gov/userContent/"
                             "Senators/2010-2012/photos/s%03d.jpg" % (
                                 int(district)))

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

        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for div in page.xpath('//div[@id="rep_icondocks2"]'):
            link = div.xpath('.//div[@class="membername"]/a')[0]
            name = link.text_content().strip()

            if 'Vacant' in name or 'Resigned' in name:
                continue

            party = div.xpath('.//div[@class="partyname"]/text()')[0].strip()
            if party == 'Democrat':
                party = 'Democratic'

            district = div.xpath('.//div[@class="districtnumber"]/text()')[0].strip()

            leg_url = link.get('href')
            split_url = urlparse.urlsplit(leg_url)
            member_id = urlparse.parse_qs(split_url.query)['MemberId'][0]
            photo_url = ("http://www.flhouse.gov/FileStores/Web/"
                         "Imaging/Member/%s.jpg" % member_id)

            leg = Legislator(term, 'lower', district, name,
                             party=party, photo_url=photo_url, url=leg_url)

            # offices
            leg_doc = lxml.html.fromstring(self.urlopen(leg_url))
            self.scrape_rep_office(leg, leg_doc, 'Capitol Office')
            self.scrape_rep_office(leg, leg_doc, 'District Office')

            leg.add_source(url)
            leg.add_source(leg_url)
            self.save_legislator(leg)
