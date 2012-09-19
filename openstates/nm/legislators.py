from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class NMLegislatorScraper(LegislatorScraper):
    state = 'nm'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'lower':
            xpath = '//table[@id="ctl00_mainCopy_HouseDistGrid"]//a[contains(@href, "SPONCODE")]/@href'
        else:
            xpath = '//table[@id="ctl00_mainCopy_SenateDistGrid"]//a[contains(@href, "SPONCODE")]/@href'

        with self.urlopen('http://www.nmlegis.gov/lcs/districts.aspx') as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute('http://www.nmlegis.gov/lcs/')
            for link in doc.xpath(xpath):
                # dummy id used for empty seat
                if 'SNULL' in link:
                    continue
                self.scrape_legislator(chamber, term, link)

    def scrape_legislator(self, chamber, term, url):
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            # most properties are easy to pull
            properties = {
                'first_name': 'FNAME',
                'last_name': 'LNAME',
                'party': 'PARTY',
                'district': 'DISTRICT',
                'county': 'COUNTY',
                'start_year': 'STARTYEAR',
                'occupation': 'OCCUPATION',
                'addr_street': 'STREET',
                'addr_city': 'CITY',
                'addr_state': 'STATE',
                'addr_zip': 'ZIP',
                'office_phone': 'WKPH',
                'home_phone': 'HMPH'
                }

            for key, value in properties.iteritems():
                id_ = 'ctl00_mainCopy_LegisInfo_%sLabel' % value
                try:
                    val = doc.get_element_by_id(id_).text
                except KeyError:
                    self.warning('bad legislator page %s missing %s' %
                                 (url, id))
                    return
                if val:
                    properties[key] = val.strip()
                else:
                    properties[key] = None

            # image & email are a bit different
            properties['photo_url'] = doc.xpath('//img[@id="ctl00_mainCopy_LegisInfo_LegislatorPhoto"]/@src')[0]
            email = doc.get_element_by_id('ctl00_mainCopy_LegisInfo_lnkEmail').text
            if email:
                properties['email'] = email.strip()

            properties['url'] = url

            properties['chamber'] = chamber
            properties['term'] = term
            properties['full_name'] = '%(first_name)s %(last_name)s' % properties
            if '(D)' in properties['party']:
                properties['party'] = 'Democratic'
            elif '(R)' in properties['party']:
                properties['party'] = 'Republican'
            elif '(DTS)' in properties['party']:
                # decline to state = independent
                properties['party'] = 'Independent'
            else:
                raise Exception("unknown party encountered")

            address = '%s\n%s, %s %s' % (properties.pop('addr_street'),
                                         properties.pop('addr_city'),
                                         properties.pop('addr_state'),
                                         properties.pop('addr_zip'))
            phone = (properties.pop('office_phone') or
                     properties.pop('home_phone'))

            leg = Legislator(**properties)
            leg.add_source(url)

            leg.add_office('district', 'District Address', address=address,
                           phone=phone)

            # committees
            # skip first header row
            for row in doc.xpath('//table[@id="ctl00_mainCopy_MembershipGrid"]/tr')[1:]:
                role, committee, note = [x.text_content()
                                         for x in row.xpath('td')]
                if 'Interim' in note:
                    role = 'interim ' + role.lower()
                else:
                    role = role.lower()
                leg.add_role('committee member', term, committee=committee,
                              position=role, chamber=chamber)

            # Already have the photo url.
            try:
                del leg['image_url']
            except KeyError:
                pass

            self.save_legislator(leg)
