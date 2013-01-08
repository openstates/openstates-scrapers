import re

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator
import scrapelib


class INLegislatorScraper(LegislatorScraper):
    jurisdiction = 'in'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        chamber_name = {'upper': 'Senate',
                        'lower': 'House'}[chamber]

        url = ("http://www.in.gov/cgi-bin/legislative/listing/"
               "listing-2.pl?data=alpha&chamber=%s" % chamber_name)

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for link in page.xpath("//div[@id='col2']/p/a"):

                name = link.text.strip()
                href = link.get('href')

                details = link.getnext().text.strip()

                party = details.split(',')[0]
                if party == 'Democrat':
                    party = 'Democratic'

                district = re.search(r'District (\d+)', details).group(1)
                district = district.lstrip('0')

                # Get the legislator's bio page.

                leg = Legislator(term, chamber, district, name, party=party,
                                 url=href)
                leg.add_source(url)
                leg.add_source(href)

                details = self.scrape_details(chamber, term, href, page, party, leg)
                if details:
                    leg.update(details)

                self.save_legislator(leg)

    def scrape_details(self, *args):
        chamber, term, href, page, party, leg = args
        methods = {
            'upper': {
                'Democratic': self.scrape_upper_democrat,
                'Republican': self.scrape_upper_republican,
                },
            'lower': {
                'Democratic': self.scrape_lower_democrat,
                'Republican': self.scrape_lower_republican,
                }
            }
        return methods[chamber][party](*args)

    def scrape_upper_republican(self, chamber, term, href, page, party, leg):

        profile = self.urlopen(href)
        profile = lxml.html.fromstring(profile)
        profile.make_links_absolute(href)

        about_url = profile.xpath('//a[contains(., "About Sen.")]/@href')[0]
        about = self.urlopen(about_url)
        about = lxml.html.fromstring(about)
        about.make_links_absolute(about_url)

        leg.add_source(about_url)

        # Get contact info.
        el = about.xpath('//strong[contains(., "Contact")]')
        if el:
            el = el[0].getparent()
        else:
            el = about.xpath('//span[contains(., "Contact")]')
            el = el[0].getparent().getparent()
        lines = ''.join(get_chunks(el)).splitlines()
        line_data = {}
        for line in lines:
            if ':' in line:
                key, val = line.split(':', 1)
                line_data[key] = val.strip()

        offices = []
        if 'Statehouse Mailing Address':
            office = {}
            for key, otherkey in (
                ('phone', 'Statehouse Phone'),
                ('address', 'Statehouse Mailing Address')
                ):
                try:
                    office[key] = line_data[otherkey]
                except KeyError:
                    pass
            office.update(fax=None, type='capitol',
                          name='Statehouse Mailing Address')

            # Nothing is uniform on Indiana's website.
            if 'phone' not in office:
                print line_data
                for key_fail in ('Statehouse Telephone',
                                 'Statehouse Telephone Number'):
                    try:
                        office['phone'] = line_data[key_fail]
                    except KeyError:
                        pass

            offices.append(office)

        # If the phone field contains multiple numbers, take the final
        # and least impersonal one (the first number is a general 800).
        for office in offices:
            if ' ' in office['phone']:
                office['phone'] = re.findall('[\d\-]+', office['phone']).pop()

            leg.add_office(**office)

        # Fix idiocy.
        if 'Email' in line_data:
            leg['email'] = re.sub(r'^Senator\.mailto:', '', line_data['Email'])

        district = leg['roles'][0]['district']
        photo_url = self._upper_republicans_photos(district)
        if photo_url:
            leg['photo_url'] = photo_url
            url = 'http://www.in.gov/legislative/senate_republicans/2355.htm'
            leg.add_source(url)

    def scrape_upper_democrat(self, chamber, term, href, page, party, leg):
        profile = self.urlopen(href)
        profile = lxml.html.fromstring(profile)
        profile.make_links_absolute(href)

        district = leg['roles'][0]['district']
        photo_url = self._upper_democrats_photos(district)
        if photo_url:
            leg['photo_url'] = photo_url
            url = ('http://www.in.gov/legislative/senate_democrats/'
                   'listingbyname.htm')
            leg.add_source(url)

        try:
            xpath = '//div[@id="leftcontent"]/p[3]/a/text()'
            leg['email'] = profile.xpath(xpath)[0]
        except IndexError:
            msg = ('This legislator has FAILED to have a profile page '
                   'that is similar to the others\'. Skipping.')
            self.logger.info(msg)

        # Contact url
        xpath = '//div[@id="sennavcontainer"]/ul/li/a/@href'
        contact_url = profile.xpath(xpath)[0]
        contact = self.urlopen(contact_url)
        contact = lxml.html.fromstring(contact)
        contact.make_links_absolute(href)
        last_p = contact.xpath('//h3[3]/following-sibling::p')
        if last_p:
            last_p = last_p[0]
        if not last_p:
            self.logger.info('Skipping garbage html')
            return
        lines = ''.join(get_chunks(last_p)).splitlines()
        lines = filter(None, lines)
        leg.add_office(name='Statehouse Mailing Address',
                       address=lines[1] + ' ' + lines[2],
                       phone=lines[-1], type='capitol')

    def scrape_lower_republican(self, chamber, term, href, page, party, leg):
        leg.add_office(
            name='Statehouse Mailing Address',
            address='200 W. Washington St. Indianapolis, IN 46204-2786',
            type='capitol', phone='800-382-9842')

        district = leg['roles'][0]['district']
        photo_url = self._lower_republicans_photos(district)
        if photo_url:
            leg['photo_url'] = photo_url
            leg.add_source('http://www.in.gov/legislative/house_republicans/members.html')

    def scrape_lower_democrat(self, chamber, term, href, page, party, leg):

        leg.add_office(
            name='Statehouse Mailing Address',
            address='200 W. Washington St. Indianapolis, IN 46204-2786',
            type='capitol', phone='800-382-9842')

        district = leg['roles'][0]['district']
        photo_url = self._lower_democrats_photos(district)
        if photo_url:
            leg['photo_url'] = photo_url
            leg.add_source('http://indianahousedemocrats.org/members')

        try:
            resp = self.urlopen(href)
        except scrapelib.HTTPError:
            self.logger.warning('Found no profile page for %r' % leg)
            return
        profile = lxml.html.fromstring(resp)
        profile.make_links_absolute(href)

    def _lower_republicans_photos(self, district, cache={}):
        if 'images' in cache:
            return cache['images'].get(district)

        images = {}
        url = 'http://www.in.gov/legislative/house_republicans/members.html'
        page = self.urlopen(url)
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(url)
        for href in doc.xpath('//img/@src'):
            m = re.search(r'r(\d+)thumb.jpg', href)
            if m:
                _district = m.group(1)
                images[_district] = href

        cache['images'] = images
        return images.get(district)

    def _lower_democrats_photos(self, district, cache={}):
        if 'images' in cache:
            return cache['images'].get(district)

        images = {}
        url = 'http://indianahousedemocrats.org/members'
        page = self.urlopen(url)
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(url)
        for div in doc.xpath('//div[@class="thumbnail"]'):
            m = re.search(r'District (\d+)', div.text_content())
            if m:
                _district = m.group(1)
                images[_district] = div.xpath('a/img/@src')[0]

        cache['images'] = images
        return images.get(district)

    def _upper_democrats_photos(self, district, cache={}):
        if 'images' in cache:
            return cache['images'].get(district)

        images = {}
        url = ('http://www.in.gov/legislative/senate_democrats/'
               'listingbyname.htm')
        page = self.urlopen(url)
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(url)
        texts = doc.xpath('//div[@id="fullcontent"]/div/h3/text()')
        texts = filter(lambda s: s.strip(), texts)
        photos = doc.xpath('//div[@id="fullcontent"]/descendant::img/@src')
        for text, url in zip(texts, photos):
            regex = r'\d+'
            m = re.search(regex, text)
            if m:
                _district = m.group()
                images[_district] = url
        cache['images'] = images
        return images.get(district)

    def _upper_republicans_photos(self, district, cache={}):
        if 'images' in cache:
            return cache['images'].get(district)

        images = {}
        url = 'http://www.in.gov/legislative/senate_republicans/2355.htm'
        page = self.urlopen(url)
        doc = lxml.html.fromstring(page)
        doc.make_links_absolute(url)
        for p in doc.xpath('//div[@id="col2content"]/div/p'):
            m = re.search(r'SD (\d+)', p.text_content())
            if m:
                _district = m.group(1)
                images[_district] = p.xpath('a/img/@src')[0]
        cache['images'] = images
        return images.get(district)


def get_chunks(el, buff=None, offset=' '):
    tagmap = {'br': '\n'}
    buff = buff or []
    for kid in el:
        # Tag, text, tail, recur...
        buff.append(tagmap.get(kid.tag, ''))
        buff.append(kid.text or '')
        if kid.tail:
            buff.append('\n' + kid.tail)
        buff = get_chunks(kid, buff, offset + ' ')
    return buff
