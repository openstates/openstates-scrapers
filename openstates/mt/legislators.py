import re
import csv
import urlparse

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator


class NoDetails(Exception):
    pass


class MTLegislatorScraper(LegislatorScraper):

    jurisdiction = 'mt'

    def url_xpath(self, url):
        # Montana's legislator page was returning valid content with 500
        # code as of 1/9/2013. Previous discussions with them after similar
        # incidents in the past suggest some external part of their stack
        # is having some issue and the error is bubbling up to the ret code.
        self.raise_errors = False
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        self.raise_errors = True
        return doc

    def scrape(self, chamber, term):

        for tdata in self.metadata['terms']:
            if term == tdata['name']:
                year = tdata['start_year']
                session_number = tdata['session_number']
                break

        # Fetch the csv.
        url = 'http://leg.mt.gov/content/sessions/%s/%d%sMembers.txt' % \
            (session_number, year, chamber == 'upper' and 'Senate' or 'House')

        # Parse it.
        data = self.get(url).text
        data = data.replace('"""', '"')  # weird triple quotes
        data = data.splitlines()

        fieldnames = ['last_name', 'first_name', 'party', 'district',
                      'address', 'city', 'state', 'zip']
        csv_parser = csv.DictReader(data, fieldnames)

        district_leg_urls = self._district_legislator_dict()

        # Toss the row headers.
        next(csv_parser)

        for entry in csv_parser:
            if not entry:
                continue

            # City.
            entry['city'] = entry['city']

            # Address.
            entry['address'] = entry['address']

            # District.
            district = entry['district']
            hd_or_sd, district = district.split()
            del entry['district']

            # Party.
            party_letter = entry['party']
            party = {'D': 'Democratic', 'R': 'Republican'}[party_letter]
            entry['party'] = party
            del entry['party']

            # Get full name properly capped.
            fullname = _fullname = '%s %s' % (entry['first_name'].capitalize(),
                                   entry['last_name'].capitalize())

            city_lower = entry['city'].lower()

            # Get any info at the legislator's detail_url.
            detail_url = district_leg_urls[hd_or_sd][district]

            # Get the office.
            address = '\n'.join([
                entry['address'],
                '%s, %s %s' % (entry['city'], entry['state'], entry['zip'])
                ])

            office = dict(
                name='District Office', type='district', phone=None,
                fax=None, email=None,
                address=address)

            try:
                deets = self._scrape_details(detail_url)
            except NoDetails:
                self.logger.warning("No details found at %r" % detail_url)
                continue

            # Add the details and delete junk.
            entry.update(deets)
            del entry['first_name'], entry['last_name']
            if 'phone' in entry:
                del entry['phone']
            if 'fax' in entry:
                del entry['fax']
            if 'email' in entry:
                del entry['email']

            legislator = Legislator(term, chamber, district, fullname,
                                    party=party)
            legislator.update(entry)
            legislator.add_source(detail_url)
            legislator.add_source(url)
            legislator['url'] = detail_url

            office['phone'] = deets.get('phone')
            office['fax'] = deets.get('fax')
            office['email'] = deets.get('email')
            legislator.add_office(**office)

            self.save_legislator(legislator)

    def _district_legislator_dict(self):
        '''Create a mapping of districts to the legislator who represents
        each district in each house.

        Used to get properly capitalized names in the legislator scraper.
        '''
        res = {'HD': {}, 'SD': {}}

        url = 'http://leg.mt.gov/css/find%20a%20legislator.asp'

        # Get base url.
        parts = urlparse.urlparse(url)
        parts._replace(path='')
        baseurl = parts.geturl()

        # Go the find-a-legislator page.
        doc = self.url_xpath(url)
        doc.make_links_absolute(baseurl)

        # Get the link to the current member roster.
        url = doc.xpath('//a[contains(@href, "roster.asp")]/@href')[0]

        # Fetch it.
        self.raise_errors = False
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        self.raise_errors = True

        # Get the new baseurl, like 'http://leg.mt.gov/css/Sessions/62nd/'
        parts = urlparse.urlparse(url)
        path, _, _ = parts.path.rpartition('/')
        parts._replace(path=path)
        baseurl = parts.geturl()
        doc.make_links_absolute(baseurl)
        table = doc.xpath('//table[@name="Legislators"]')[0]

        for tr in table.xpath('tr'):

            td1, td2 = tr.xpath('td')

            # Skip header rows and retired legislators
            if (not td2.text_content().strip() or
                    'Resigned' in tr.text_content()):
                continue

            # Get link to the member's page.
            detail_url = td1.xpath('h4/a/@href')[0]

            # Get the members district so we can match the
            # profile page with its csv record.
            house, district = td2.text_content().split()

            res[house][district] = detail_url

        return res

    def _scrape_details(self, url):
        '''Scrape the member's bio page.

        Things available but not currently scraped are office address,
        and waaay too much contanct info, including personal email, phone.
        '''
        doc = self.url_xpath(url)
        # Get base url.
        parts = urlparse.urlparse(url)
        parts._replace(path='')
        baseurl = parts.geturl()

        doc.make_links_absolute(baseurl)

        xpath = '//img[contains(@src, "legislator")]/@src'

        try:
            photo_url = doc.xpath(xpath).pop()
        except IndexError:
            raise NoDetails('No details found at %r' % url)

        details = { 'photo_url': photo_url }

        # # Parse address.
        elements = list(doc.xpath('//b[contains(., "Address")]/..')[0])

        # # MT's website currently has a typo that places the "address"
        # # heading inline with the "Information Office" phone number.
        # # This hack tempprarily makes things work.
        elements = elements[3:]
        chunks = []
        for br in elements:
            chunks.extend(filter(None, [br.text, br.tail]))

        # As far as I can tell, MT legislators don't have capital offices.
        for line in chunks[2:]:
            if not line.strip():
                continue
            for key in ('ph', 'fax'):
                if key in line.lower():
                    key = {'ph': 'phone'}.get(key)
                    break
            number = re.search('\(\d{3}\) \d{3}\-\d{4}', line)
            if number:
                number = number.group()
                if key:
                    # Used to set this on the office.
                    details[key] = number

        try:
            email = doc.xpath('//b[contains(., "Email")]/..')[0]
        except IndexError:
            pass
        else:
            if email:
                html = lxml.html.tostring(email.getparent())
                match = re.search('[a-zA-Z0-9\.\_\%\+\-]+@\w+\.[a-z]+', html)
                if match:
                    details['email'] = match.group()

        return details
