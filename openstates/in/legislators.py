import re
import datetime
import urlparse
import collections
import contextlib

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator
import scrapelib


class INLegislatorScraper(LegislatorScraper):
    jurisdiction = 'in'
    _url = 'http://iga.in.gov/legislative/%d/legislators'

    @property
    def url(self):
        return self._url % self.year

    def get_termdata(self, term_id):
        for term in self.metadata['terms']:
            if term['name'] == term_id:
                return term

    def scrape(self, chamber, term):
        self.requests_per_minute = 15
        self.termdata = self.get_termdata(term)

        year = datetime.datetime.now().year
        if year not in self.termdata.values():
            year = self.termdata['start_year']
        self.year = year

        # Get the find-a-legislator page.
        html = self.urlopen(self.url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(self.url)
        optgroup = dict(upper='Senators', lower='Representatives')[chamber]
        for option in doc.xpath('//optgroup[@id="%s"]/option' % optgroup):
            self.scrape_legislator(chamber, term, option)

    @contextlib.contextmanager
    def scrapelib_settings(self, **kwargs):
        previous = {}
        for k, v in kwargs.items():
            # Store previous setting.
            val = getattr(self, k, None)
            previous[k] = val

            # Override them.
            setattr(self, k, val)
        yield
        for k, v in previous.items():
            setattr(self, k, v)

    def scrape_legislator(self, chamber, term, option):
        url = urlparse.urljoin(self.url, option.attrib['value'])
        name, party, district = re.split(r'\s*,\s*', option.text.strip())
        name = re.sub(r'^(Sen\.|Rep\.)\s+', '', name)
        district = re.sub(r'^District\s+', '', district)
        if district == '[N/A]':
            msg = 'No district found for %r; skipping.'
            self.logger.warning(msg, name)
            return
        leg = Legislator(term, chamber, district, name, party=party)
        leg.add_source(self.url)

        # Scrape leg page.
        try:
            html = self.urlopen(url)
        except scrapelib.HTTPError as exc:
            # As of July 2014, this only happens when a page has
            # gone missing from their varnish server.
            # if exc.response.status_code is 503:
            self.logger.exception(exc)
            self.logger.warning('Skipping legislator at url: %s' % url)
            skipped = True
            return

        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(self.url)
        leg.add_source(url)

        # Scrape committees.
        for tr in doc.xpath('//div[@class="legislator-committees-container"]//table//tr'):
            committee, committee_type, role = tr
            committee = committee.text_content().strip()
            role = role.text_content().strip()
            if 'member' in role.lower():
                role = 'committee member'
            elif 'chair' in role.lower():
                role = 'chair'
            if committee != "Committee Name":
                leg.add_role(role, term, chamber=chamber, committee=committee)

        # Scrape offices.
        dist_office, phone = doc.xpath('//address')
        dist_office = dist_office.text_content().strip()
        dist_office = re.sub(r' {2,}', '', dist_office)

        phone = phone.text_content().strip()
        email = doc.xpath('string(//a[starts-with(@href, "mailto:")]/@href)')
        photo_url = doc.xpath('string(//img[contains(@class, "member")]/@src)')

        leg.update(email=email, photo_url=photo_url)
        leg.add_office(
            address=dist_office, name='District Office',
            type='district', phone=phone)

        self.save_legislator(leg)

