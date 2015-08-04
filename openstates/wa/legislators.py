from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin
import re


class WALegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'wa'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            index_url = 'http://www.leg.wa.gov/senate/senators/Pages/default.aspx'
        else:
            index_url = 'http://www.leg.wa.gov/house/representatives/Pages/default.aspx'
        doc = self.lxmlize(index_url)

        for member in doc.xpath('//div[@id="allMembers"]/div[@class="memberInformation"]'):
            (photo_url, ) = member.xpath('.//a[text()="Print Quality Photo"]/@href')

            (title_name_party, ) = member.xpath('.//span[@class="memberName"]/text()')
            (name, party) = re.search(r'^(?:Senator|Representative)\s(.+)\s\(([RD])\)$', title_name_party).groups()
            if party == 'R':
                party = "Republican"
            elif party == 'D':
                party = "Democratic"

            (district_name, _district_name, ) = member.xpath('.//a[contains(text(), " Legislative District")]/text()')
            assert district_name == _district_name
            district_num = re.search(r'(\d{1,2})\w{2} Legislative District', district_name).group(1)

            leg = Legislator(
                full_name=name,
                term=term,
                chamber=chamber,
                district=district_num,
                party=party,
                photo_url=photo_url
            )

            capitol_office = member.xpath('.//div[@class="memberColumnTitle" and text()=" Olympia Office"]/parent::div[1]/text()')
            capitol_office = [l.strip() for l in capitol_office if l.strip()]
            capitol_fax = None
            if capitol_office[-1].startswith('Fax: '):
                capitol_fax = capitol_office.pop().replace('Fax: ', "")
            assert re.match(r'\(\d{3}\) \d{3} \- \d{4}', capitol_office[-1]), "Phone number expected but not found"
            capitol_phone = capitol_office.pop()
            capitol_address = '\n'.join(capitol_office)
            leg.add_office(
                'capitol',
                'Capitol Office',
                address=capitol_address,
                phone=capitol_phone,
                fax=capitol_fax
            )

            _has_district_office = member.xpath('.//div[@class="memberColumnTitle" and text()=" District Office"]')
            if _has_district_office:
                # Out of both chambers, only one member has multiple district offices, so ignore that
                # Also ignore the few members who have separate mailing addresses
                district_office = member.xpath('.//div[@class="memberColumnTitle" and text()=" District Office"]/parent::div[1]/text()')
                district_office = [l.strip() for l in district_office if l.strip()]
                _end_of_first_address = district_office.index([l for l in district_office if re.search(r'\,\s*WA\s*\d{5}', l)][0])
                district_address = '\n'.join(district_office[0:(_end_of_first_address + 1)])
                try:
                    district_phone = district_office[(_end_of_first_address + 1)]
                    assert re.match(r'\(\d{3}\) \d{3} \- \d{4}', district_phone)
                except IndexError:
                    pass

                leg.add_office(
                    'district',
                    'District Office',
                    address=district_address,
                    phone=district_phone
                )

            leg.add_source(index_url)

            self.save_legislator(leg)
