from billy.scrape.legislators import Legislator, LegislatorScraper
from billy.scrape import NoDataForPeriod
import lxml.html
import logging
import re

logger = logging.getLogger('openstates')

class NDLegislatorScraper(LegislatorScraper):
    jurisdiction = 'nd'

    def scrape(self, term, chambers):
        self.validate_term(term, latest_only=True)

        # figuring out starting year from metadata
        for t in self.metadata['terms']:
            if t['name'] == term:
                start_year = t['start_year']
                break

        root = "http://www.legis.nd.gov/assembly"
        main_url = "%s/%s-%s/members/members-by-district" % (
            root,
            term,
            start_year
        )

        page = self.get(main_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(main_url)
        for person_url in page.xpath('//div[contains(@class, "all-members")]/div[@class="name"]/a/@href'):
            self.scrape_legislator_page(term, person_url)


    def scrape_legislator_page(self, term, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        name = page.xpath("//h1[@id='page-title']/text()")[0]
        name = re.sub(r'^(Representative|Senator)\s', '', name)
        district = page.xpath("//a[contains(@href, 'district')]/text()")[0]
        district = district.replace("District", "").strip()

        committees = page.xpath("//a[contains(@href, 'committees')]/text()")

        party = page.xpath(
            "//div[contains(text(), 'Political Party')]"
        )[0].getnext().text_content().strip()

        photo = page.xpath(
            "//div[@class='field-person-photo']/img/@src"
        )
        photo = photo[0] if len(photo) else None

        address = page.xpath("//div[@class='adr']")
        if address:
            address = address[0]
            address = re.sub("[ \t]+", " ", address.text_content()).strip()
        else:
            address = None

        item_mapping = {
            "email": "email",
            "home telephone": "home-telephone",
            "cellphone": "cellphone",
            "office telephone": "office-telephone",
            "political party": "party",
            "chamber": "chamber",
            "fax": "fax"
        }
        metainf = {}

        for block in page.xpath("//div[contains(@class, 'field-label-inline')]"):
            label, items = block.xpath("./*")
            key = label.text_content().strip().lower()
            if key.endswith(":"):
                key = key[:-1]

            metainf[item_mapping[key]] = items.text_content().strip()

        chamber = {
            "Senate": "upper",
            "House": "lower"
        }[metainf['chamber']]

        kwargs = {
            "party": {"Democrat": "Democratic",
                      "Republican": "Republican"}[metainf['party']]
        }
        if photo:
            kwargs['photo_url'] = photo

        leg = Legislator(term,
                         chamber,
                         district,
                         name,
                         **kwargs)

        kwargs = {"url": url}
        for key, leg_key in [('email', 'email'),
                             ('fax', 'fax'),
                             ('office-telephone', 'phone')]:
            if key in metainf:
                if metainf[key].strip():
                    kwargs[leg_key] = metainf[key]

        leg.add_office('capitol',
                       'Capitol Office',
                       **kwargs)

        kwargs = {}
        if address:
            kwargs['address'] = address

        if 'cellphone' in metainf:
            kwargs['phone'] = metainf['cellphone']

        if 'home-telephone' in metainf:
            kwargs['phone'] = metainf['home-telephone']

        leg.add_office('district',
                       'District Office',
                       **kwargs)

        #for committee in committees:
        #    leg.add_role('committee member',
        #                 term=term,
        #                 chamber=chamber,
        #                 committee=committee)

        leg.add_source(url)
        self.save_legislator(leg)
