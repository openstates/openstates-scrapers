import re
import csv
import difflib
import urlparse
from itertools import dropwhile, takewhile

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator
import scrapelib

from .committees import scrape_committees


def url_xpath(url):
    html = scrapelib.urlopen(url)
    html = html
    doc = lxml.html.fromstring(html)
    return doc


class MTLegislatorScraper(LegislatorScraper):

    jurisdiction = 'mt'

    def scrape(self, chamber, term):

        for tdata in self.metadata['terms']:
            if term == tdata['name']:
                year = tdata['start_year']
                session_number = tdata['session_number']
                break

        # Scrape committees. Also produce a name dictionary that can be
        # used for fuzzy matching between the committee page names and the
        # all-caps csv names.
        for name_dict, _ in scrape_committees(year, chamber):
            pass

        # Fetch the csv.
        url = 'http://leg.mt.gov/content/sessions/%s/%d%sMembers.txt' % \
            (session_number, year, chamber == 'upper' and 'Senate' or 'House')

        # Parse it.
        data = self.urlopen(url)
        data = data.replace('"""', '"')  # weird triple quotes
        data = data.splitlines()

        fieldnames = ['last_name', 'first_name', 'party', 'district',
                      'address', 'city', 'state', 'zip']
        csv_parser = csv.DictReader(data, fieldnames)

        district_leg_urls = self._district_legislator_dict()

        for entry in csv_parser:
            if not entry:
                continue

            # City.
            entry['city'] = entry['city'].title()

            # Address.
            entry['address'] = entry['address'].title()

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
            _fullname = '%s %s' % (entry['first_name'].capitalize(),
                                   entry['last_name'].capitalize())

            city_lower = entry['city'].lower()
            fullname = difflib.get_close_matches(
                           _fullname, name_dict[city_lower], cutoff=0.5)

            # If there are no close matches with the committee page,
            # use the title-capped first and last name.
            if len(fullname) < 1:
                fullname = _fullname
                # msg = 'No matches found for "%s" with "%s" from %r'
                # self.debug(msg % (_fullname, fullname,
                #                   name_dict[city_lower]))
            else:
                fullname = fullname[0]
                # if _fullname != fullname:
                #     msg = 'matched "%s" with "%s" from %r'
                #     self.debug(msg % (_fullname, fullname,
                #                       name_dict[city_lower]))

            # Get any info at the legislator's detail_url.
            detail_url = district_leg_urls[hd_or_sd][district]
            deets = self._scrape_details(detail_url)

            # Add the details and delete junk.
            entry.update(deets)
            del entry['first_name'], entry['last_name']

            legislator = Legislator(term, chamber, district, fullname,
                                    party=party)
            legislator.update(entry)
            legislator.add_source(detail_url)
            legislator.add_source(url)
            legislator['url'] = detail_url

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
        doc = url_xpath(url)
        doc.make_links_absolute(baseurl)

        # Get the link to the current member roster.
        url = doc.xpath('//a[contains(@href, "roster.asp")]/@href')[0]

        # Fetch it.
        doc = url_xpath(url)

        # Get the new baseurl, like 'http://leg.mt.gov/css/Sessions/62nd/'
        parts = urlparse.urlparse(url)
        path, _, _ = parts.path.rpartition('/')
        parts._replace(path=path)
        baseurl = parts.geturl()
        doc.make_links_absolute(baseurl)
        table = doc.xpath('//table[@name="Legislators"]')[0]

        for tr in table.xpath('tr'):

            td1, td2 = tr.xpath('td')

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
        doc = url_xpath(url)

        details = {
            'photo_url': doc.xpath('//table[@name][1]/'
                                   'descendant::img/@src')[0],
            }

        # Get base url.
        parts = urlparse.urlparse(url)
        parts._replace(path='')
        baseurl = parts.geturl()

        doc.make_links_absolute(baseurl)

        # Parse address.
        elements = list(doc.xpath('//b[contains(., "Address")]/..')[0])
        dropper = lambda element: element.tag != 'b'
        elements = dropwhile(dropper, elements)
        assert next(elements).text == 'Address'
        taker = lambda element: element.tag == 'br'
        elements = list(takewhile(taker, elements))
        chunks = []
        for br in elements:
            chunks.extend(filter(None, [br.text, br.tail]))

        # As far as I can tell, MT legislators don't have capital offices.
        office = dict(name='District Office', type='district', phone=None,
                      fax=None, email=None,
                      address='\n'.join(chunks[:2]))
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
                    office[key] = number

        details['offices'] = [office]

        try:
            email = doc.xpath('//b[contains(., "Email")]/..')[0]
        except IndexError:
            pass
        else:
            if email:
                html = lxml.html.tostring(email.getparent())
                match = re.search('\w+@\w+\.[a-z]+', html)
                if match:
                    details['email'] = match.group()

        return details

