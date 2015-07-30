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

        body = self.get(url).text
        page = lxml.html.fromstring(body)
        page.make_links_absolute(url)

        for row in page.xpath(".//div[@class='box-content']/div[starts-with(@id,'district')]"):

            if row.xpath(".//a/@href") and not row.xpath(".//a[text()='Vacant']"):
                rep_url = row.xpath(".//a[text()='Details']/@href")[0].strip("https://")
                rep_url = "https://docs."+rep_url
                rep_doc = lxml.html.fromstring(self.get(rep_url).text)
                rep_doc.make_links_absolute(rep_url)

                full_name = rep_doc.xpath('.//div[@id="district"]/h1/text()')[0].replace("Senator ","").replace("Representative ","")


                party = rep_doc.xpath('.//div[@id="district"]/h3/small/text()')
                if len(party) > 0:
                    party = PARTY_DICT[party[0].split("-")[0].strip("(").strip()]
                else:
                    party = None
                district = rep_doc.xpath('.//div[@id="district"]/h3/a/@href')[1]
                district = district.split("/")[-1]
                district = str(int(district))

                # email
                email = rep_doc.xpath("//span[@class='info email']/a/text()")
                if email:
                    email = email[0]
                else:
                    email = ''

                assert party is not None, "{} is missing party".format(full_name)

                leg = Legislator(term, chamber, district, full_name,
                                 party=party, url=rep_url)

                img = rep_doc.xpath('.//div[@id="district"]/img/@src')
                if img:
                    leg['photo_url'] = img[0]

                # office ####
                address_lines = rep_doc.xpath('.//span[@class="info office"]/text()')
                address = '\n'.join([line.strip() for line in address_lines if line.strip() != ""])

                phone = rep_doc.xpath('.//span[@class="info telephone"]/text()')
                if phone:
                    phone = re.sub('\s+', ' ', phone[1]).strip()
                else:
                    phone = None

                fax = rep_doc.xpath('.//span[@class="info fax"]/text()')
                if fax:
                    fax = re.sub('\s+', ' ', fax[1]).strip()
                else:
                    fax = None


                leg.add_office('capitol', 'Madison Office', address=address,
                               phone=phone, fax=fax, email=email)

                # save legislator
                leg.add_source(rep_url)
                self.save_legislator(leg)
