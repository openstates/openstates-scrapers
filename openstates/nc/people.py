from pupa.scrape import Scraper, Person
import lxml.html

party_map = {'Dem': 'Democratic',
             'Rep': 'Republican',
             'Una': 'Unaffiliated',
             'D': 'Democratic',
             'R': 'Republican',
             'U': 'Unaffiliated'}


def get_table_item(doc, name):
    # get span w/ item
    try:
        span = doc.xpath('//span[text()="{0}"]'.format(name))[0]
        # get neighboring td's span
        dataspan = span.getparent().getnext().getchildren()[0]
        if dataspan.text:
            return (dataspan.text + '\n' +
                    '\n'.join([x.tail for x in dataspan.getchildren()])).strip()
        else:
            return None
    except IndexError:
        return None


class NCPersonScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')

    def scrape_chamber(self, chamber):
        url = "http://www.ncleg.net/gascripts/members/memberListNoPic.pl?sChamber="

        if chamber == 'lower':
            url += 'House'
        else:
            url += 'Senate'

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute('http://www.ncleg.net')
        rows = doc.xpath('//div[@id="mainBody"]/table/tr')

        for row in rows[1:]:
            party, district, full_name, counties = row.getchildren()

            party = party.text_content().strip("()")
            party = party_map[party]

            district = district.text_content().replace("District", "").strip()

            notice = full_name.xpath('span')
            if notice:
                notice = notice[0].text_content()
                # skip resigned legislators
                if 'Resigned' in notice or 'Deceased' in notice:
                    continue
            else:
                notice = None
            link = full_name.xpath('a/@href')[0]
            full_name = full_name.xpath('a')[0].text_content()
            full_name = full_name.replace(u'\u00a0', ' ')

            # scrape legislator page details
            lhtml = self.get(link).text
            ldoc = lxml.html.fromstring(lhtml)
            ldoc.make_links_absolute('http://www.ncleg.net')
            photo_url = ldoc.xpath('//a[contains(@href, "pictures")]/@href')[0]
            phone = (get_table_item(ldoc, 'District Phone:') or
                     get_table_item(ldoc, 'Phone:') or None)
            address = (get_table_item(ldoc, 'District Address:') or
                       get_table_item(ldoc, 'Address:') or None)
            email = ldoc.xpath('//a[starts-with(@href, "mailto:")]')[0]
            capitol_email = email.text
            capitol_phone = email.xpath('ancestor::tr[1]/preceding-sibling::tr[1]/td/span')[0].text
            capitol_address = email.xpath('ancestor::tr[1]/preceding-sibling::tr[2]/td/text()')
            capitol_address = [x.strip() for x in capitol_address]
            capitol_address = '\n'.join(capitol_address) or None
            capitol_phone = capitol_phone.strip() or None

            # save legislator
            person = Person(name=full_name, district=district,
                            party=party, primary_org=chamber,
                            image=photo_url)
            person.extras['notice'] = notice
            person.add_link(link)
            person.add_source(link)
            if address:
                person.add_contact_detail(type='address', value=address,
                                          note='District Office')
            if phone:
                person.add_contact_detail(type='voice', value=phone,
                                          note='District Office')
            if capitol_address:
                person.add_contact_detail(type='address', value=capitol_address,
                                          note='Capitol Office')
            if capitol_phone:
                person.add_contact_detail(type='voice', value=capitol_phone,
                                          note='Capitol Office')
            if capitol_email:
                person.add_contact_detail(type='email', value=capitol_email,
                                          note='Capitol Office')
            yield person
