from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class NMLegislatorScraper(LegislatorScraper):
    jurisdiction = 'nm'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'lower':
            xpath = '//table[@id="ctl00_mainCopy_gridViewHouseDistricts"]//a[contains(@href, "SPONCODE")]/@href'
        else:
            xpath = '//table[@id="ctl00_mainCopy_gridViewSenateDistricts"]//a[contains(@href, "SPONCODE")]/@href'

        html = self.get('http://www.nmlegis.gov/lcs/districts.aspx').text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute('http://www.nmlegis.gov/lcs/')
        for link in doc.xpath(xpath):
            # dummy id used for empty seat
            if 'SNULL' in link:
                continue
            self.scrape_legislator(chamber, term, link)

    def scrape_legislator(self, chamber, term, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        # most properties are easy to pull
        optional = ["home_phone"]
        properties = {
            'start_year': 'lblStartYear',
            'district': "linkDistrict",
            'occupation': "lblOccupation",
            'header': "lblHeader",
            'addr_street': "lblAddress",
            'office_phone': ["lblCapitolPhone", "lblOfficePhone"],
            'home_phone': "lblHomePhone",
#            '': "",
#            '': "",
#            '': "",
#            '': "",
            }

        for key, value in properties.iteritems():
            if isinstance(value, list):
                values = value
            else:
                values = [value]

            found = False
            for value in values:
                id_ = 'ctl00_mainCopy_formViewLegislator_%s' % value
                val = None
                try:
                    val = "\n".join(doc.get_element_by_id(id_).itertext())
                    found = True
                except KeyError:
                    pass
                if val:
                    properties[key] = val.strip()
                else:
                    properties[key] = None

            if found is False and key not in optional:
                self.warning('bad legislator page %s missing %s' %
                             (url, id_))
                return

        # image & email are a bit different
        properties['photo_url'] = doc.xpath('//img[@id="ctl00_mainCopy_formViewLegislator_imgLegislator"]/@src')[0]
        email = doc.get_element_by_id('ctl00_mainCopy_formViewLegislator_linkEmail').text
        

        properties['url'] = url

        properties['chamber'] = chamber
        properties['term'] = term

        full_name, party = properties['header'].rsplit("-", 1)

        properties['full_name'] = full_name.replace("Representative","").replace("Senator","").strip()
        properties['party'] = party

        if '(D)' in properties['party']:
            properties['party'] = 'Democratic'
        elif '(R)' in properties['party']:
            properties['party'] = 'Republican'
        elif '(DTS)' in properties['party']:
            # decline to state = independent
            properties['party'] = 'Independent'
        else:
            raise Exception("unknown party encountered")

        address = properties.pop('addr_street')

        phone = (properties.pop('office_phone') or
                 properties.pop('home_phone'))

        leg = Legislator(**properties)
        leg.add_source(url)

        if email:
            properties['email'] = email.strip()
        else:
            print "no email"
            email = None

        leg.add_office('district', 'District Address', address=address,
                       phone=phone, email=email)

        # committees
        # skip first header row
        for row in doc.xpath('//table[@id="ctl00_mainCopy_gridViewCommittees"]/tr')[1:]:
            role, committee, note = [x.text_content()
                                     for x in row.xpath('td')]
            committee = committee.title()
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
