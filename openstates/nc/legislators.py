from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

party_map = {'Dem': 'Democratic',
             'Rep': 'Republican',
             'Una': 'Unaffiliated',
             'D': 'Democratic',
             'R': 'Republican',
             'U': 'Unaffiliated'}

def get_table_item(doc, name):
    # get span w/ item
    span = doc.xpath('//span[text()="{0}"]'.format(name))[0]
    # get neighboring td's span
    dataspan = span.getparent().getnext().getchildren()[0]
    if dataspan.text:
        return (dataspan.text + '\n' +
                '\n'.join([x.tail for x in dataspan.getchildren()])).strip()
    else:
        return None

class NCLegislatorScraper(LegislatorScraper):
    jurisdiction = 'nc'

    def scrape(self, term, chambers):
        for chamber in chambers:
            self.scrape_chamber(chamber, term)

    def scrape_chamber(self, chamber, term):
        url = "http://www.ncga.state.nc.us/gascripts/members/"\
            "memberListNoPic.pl?sChamber="

        if chamber == 'lower':
            url += 'House'
        else:
            url += 'Senate'

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute('http://www.ncga.state.nc.us')
        rows = doc.xpath('//div[@id="mainBody"]/table/tr')

        for row in rows[1:]:
            party, district, full_name, counties = row.getchildren()

            party = party.text_content().strip("()")
            party = party_map[party]

            district = district.text_content().replace("District","").strip()

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
            ldoc.make_links_absolute('http://www.ncga.state.nc.us')
            photo_url = ldoc.xpath('//a[contains(@href, "pictures")]/@href')[0]
            phone = get_table_item(ldoc, 'Phone:') or None
            address = get_table_item(ldoc, 'Address:') or None
            email = ldoc.xpath('//a[starts-with(@href, "mailto:")]')[0]
            capitol_email = email.text
            capitol_phone = email.xpath('ancestor::tr[1]/preceding-sibling::tr[1]/td/span')[0].text
            capitol_address = email.xpath('ancestor::tr[1]/preceding-sibling::tr[2]/td/text()')
            capitol_address = [x.strip() for x in capitol_address]
            capitol_address = '\n'.join(capitol_address)
            capitol_phone = capitol_phone.strip()

            # save legislator
            legislator = Legislator(term, chamber, district, full_name,
                                    photo_url=photo_url, party=party,
                                    url=link, notice=notice)
            legislator.add_source(link)
            legislator.add_office('district', 'District Office',
                                  address=address, phone=phone)
            legislator.add_office('capitol', 'Capitol Office',
                                  address=capitol_address, phone=capitol_phone, email=capitol_email)
            self.save_legislator(legislator)
