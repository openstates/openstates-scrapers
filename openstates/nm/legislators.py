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

<<<<<<< HEAD
        xpath = '//span[@id="ctl00_mainCopy_formViewLegislator_{}"]/text()'
=======
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

            if found is False and key not in optional:
                self.warning('bad legislator page %s missing %s' %
                             (url, id_))
                return
            elif found is False:
                properties[key] = None
            elif properties[key] == ["lblCapitolPhone", "lblOfficePhone"]:
                properties[key] = None

        # image & email are a bit different
        properties['photo_url'] = doc.xpath('//img[@id="ctl00_mainCopy_formViewLegislator_imgLegislator"]/@src')[0]
        email = doc.get_element_by_id('ctl00_mainCopy_formViewLegislator_linkEmail').text

        properties['url'] = url

        properties['chamber'] = chamber
        properties['term'] = term
>>>>>>> a2bb5ea5c2ffb0014f00414e82ecc3c934da744e

        district = doc.xpath('//a[@id="ctl00_mainCopy_formViewLegislator_linkDistrict"]/text()')[0]

        header = doc.xpath(xpath.format('lblHeader'))
        full_name, party = header[0].rsplit("-", 1)
        full_name = full_name.replace("Representative","").replace("Senator","").strip()

        if '(D)' in party:
            party = 'Democratic'
        elif '(R)' in party:
            party = 'Republican'
        elif '(DTS)' in party:
            # decline to state = independent
            party = 'Independent'
        else:
            raise Exception("unknown party encountered")

        photo_url = doc.xpath('//img[@id="ctl00_mainCopy_formViewLegislator_imgLegislator"]/@src')[0]

        email = doc.xpath('//a[@id="ctl00_mainCopy_formViewLegislator_linkEmail"]/text()')
        if email:
            email = email[0]
        else:
            print "no email"
            email = None

        district_address = ", ".join(doc.xpath(xpath.format('lblAddress')))

        district_phone = doc.xpath(xpath.format('lblHomePhone'))
        # if they don't have a home phone, check for an office phone
        if not district_phone:
            district_phone = doc.xpath(xpath.format('lblOfficePhone'))
        if district_phone:
            district_phone = district_phone[0]
        else:
            district_phone = None

        capitol_address = doc.xpath(xpath.format('lblCapitolRoom'))
        if capitol_address:
            capitol_address = 'Room ' + capitol_address[0] + ' State Capitol, Santa Fe, NM 87501'
        else:
            capitol_address = None
        
        capitol_phone = doc.xpath(xpath.format('lblCapitolPhone'))
        if capitol_phone:
            capitol_phone = "(505) " + capitol_phone[0]
        else:
            capitol_phone = None

        leg = Legislator(term=term, chamber=chamber, district=district, full_name=full_name, party=party, photo_url=photo_url)
        leg.add_source(url)

        leg.add_office('district', 'District Office', address=district_address,
                        phone=district_phone)
        leg.add_office('capitol', 'Capitol Office', address=capitol_address,
                        phone=capitol_phone, email=email)

        # committees
        # skip first header row
        for row in doc.xpath('//table[@id="ctl00_mainCopy_gridViewCommittees"]/tr')[1:]:
            role, committee, note = [x.text_content() for x in row.xpath('td')]
            committee = committee.title()
            if 'Interim' in note:
                role = 'interim ' + role.lower()
            else:
                role = role.lower()
            leg.add_role('committee member', term, committee=committee, position=role, chamber=chamber)

        # Already have the photo url.
        try:
            del leg['image_url']
        except KeyError:
            pass

        self.save_legislator(leg)
