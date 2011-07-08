import lxml.html
import scrapelib

from billy.scrape.legislators import Legislator, LegislatorScraper

class NDLegislatorScraper(LegislatorScraper):
    state = 'nd'
    site_root = 'http://www.legis.nd.gov'

    def scrape(self, chamber, term):
        # get session
        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][0]

        if chamber == 'upper':
            url_chamber = 'senate'
        else:
            url_chamber = 'house'

        list_url = '%s/assembly/%s/%s/members/district.html' % (self.site_root,
                                                                session,
                                                                url_chamber)

        with self.urlopen(list_url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(list_url)
            for href in doc.xpath('//a[contains(@href,"bios")]/@href'):
                self.scrape_legislator(chamber, term, href)

    def scrape_legislator(self, chamber, term, url):
        if chamber == 'upper':
            mem_type = 'senators'
        else:
            mem_type = 'representatives'

        try:
            html = self.urlopen(url)
        except scrapelib.HTTPError as e:
            if e.response.code == 404:
                self.warning('could not retrieve %s' % url)
                return

        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        name = doc.xpath('//h2/text()')[0].split(' ', 1)[1]

        attribs = {}

        for row in doc.xpath('//div[@class="content"]/table//table/tr'):
            tds = row.getchildren()
            if tds[0].text_content().startswith('Telephone'):
                attribs['office_phone'] = tds[1].text_content().strip()
            elif tds[0].text_content().startswith('E-mail'):
                attribs['email'] = tds[1].text_content().strip()
            elif tds[0].text_content().startswith('District'):
                attribs['district'] = tds[1].text_content().strip()
            elif tds[0].text_content().startswith('Party'):
                attribs['party'] = tds[1].text_content().strip()

        if attribs['party'] == 'Democrat':
            attribs['party'] = 'Democratic'

        img_xpath = '//img[contains(@src, "%s")]/@src' % mem_type
        attribs['photo_url'] = doc.xpath(img_xpath)[0]

        leg = Legislator(term, chamber, full_name=name, **attribs)
        leg.add_source(url)
        self.save_legislator(leg)
