from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html

party_map = {'Dem': 'Democratic',
             'Rep': 'Republican',
             'Una': 'Unaffiliated'}

class NCLegislatorScraper(LegislatorScraper):
    state = 'nc'

    def scrape(self, chamber, term):
        url = "http://www.ncga.state.nc.us/gascripts/members/"\
            "memberList.pl?sChamber="

        if chamber == 'lower':
            url += 'House'
        else:
            url += 'Senate'

        with self.urlopen(url) as data:
            doc = lxml.html.fromstring(data)
            doc.make_links_absolute('http://www.ncga.state.nc.us')
            rows = doc.xpath('//div[@id="mainBody"]/table/tr')

            for row in rows[1:]:
                party, district, full_name, counties = row.getchildren()

                party = party.text_content()
                party = party_map[party]

                district = district.text_content()

                notice = full_name.xpath('span')
                if notice:
                    notice = notice[0].text_content()
                else:
                    notice = None
                link = full_name.xpath('a/@href')[0]
                full_name = full_name.xpath('a')[0].text_content()
                full_name = full_name.replace(u'\u00a0', ' ')

                with self.urlopen(link) as lhtml:
                    ldoc = lxml.html.fromstring(lhtml)
                    ldoc.make_links_absolute('http://www.ncga.state.nc.us')
                    photo_url = ldoc.xpath('//a[contains(@href, "pictures")]/@href')[0]

                legislator = Legislator(term, chamber, district, full_name,
                                        photo_url=photo_url, party=party,
                                        notice=notice)
                legislator.add_source(link)
                self.save_legislator(legislator)
