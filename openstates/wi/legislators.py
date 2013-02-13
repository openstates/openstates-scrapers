import datetime
import lxml.html
import re

from billy.scrape.legislators import LegislatorScraper, Legislator


PARTY_DICT = {'D': 'Democratic', 'R': 'Republican', 'I': 'Independent'}

class WILegislatorScraper(LegislatorScraper):
    jurisdiction = 'wi'
    latest_only = True

    def scrape(self, chamber, term):

        if chamber == 'upper':
            url = "http://legis.wisconsin.gov/Pages/leg-list.aspx?h=s"
        else:
            url = "http://legis.wisconsin.gov/Pages/leg-list.aspx?h=a"

        body = self.urlopen(url)
        page = lxml.html.fromstring(body)
        page.make_links_absolute(url)

        for row in page.xpath("//table[@class='legis-list']/tr")[1:]:
            if row.xpath(".//a/@href"):
                rep_url = row.xpath(".//a/@href")[0]
                rep_doc = lxml.html.fromstring(self.urlopen(rep_url))
                rep_doc.make_links_absolute(rep_url)

                first_name = rep_doc.xpath('//h2[@class="given-name"]/text()')[0]
                last_name = rep_doc.xpath('//h2[@class="family-name"]/text()')[0]
                full_name = '%s %s' % (first_name, last_name)
                party = rep_doc.xpath('//div[@class="party"]/text()')[0]
                if party == 'Democrat':
                    party = 'Democratic'

                district = str(int(row.getchildren()[2].text_content()))

                # email
                email = rep_doc.xpath('//a[starts-with(@href, "mailto")]/text()')
                if email:
                    email = email[0]
                else:
                    email = ''

                leg = Legislator(term, chamber, district, full_name,
                                 first_name=first_name, last_name=last_name,
                                 party=party, url=rep_url, email=email)

                img = rep_doc.xpath('//img[@class="photo"]/@src')
                if img:
                    leg['photo_url'] = img[0]

                # office ####
                address = '\n'.join(rep_doc.xpath('//dt[text()="Madison Office"]/following-sibling::dd/div/text()'))
                phone = rep_doc.xpath('//dt[text()="Telephone"]/following-sibling::dd/div/text()')
                if phone:
                    phone = re.sub('\s+', ' ', phone[0]).strip()
                else:
                    phone = None
                fax = rep_doc.xpath('//dt[text()="Fax"]/following-sibling::dd/div/text()')
                if fax:
                    fax = re.sub('\s+', ' ', fax[0]).strip()
                else:
                    fax = None

                leg.add_office('capitol', 'Madison Office', address=address,
                               phone=phone, fax=fax)

                # save legislator
                leg.add_source(rep_url)
                self.save_legislator(leg)
