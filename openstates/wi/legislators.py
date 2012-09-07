import datetime
import lxml.html
import re

from billy.scrape.legislators import LegislatorScraper, Legislator


PARTY_DICT = {'D': 'Democratic', 'R': 'Republican', 'I': 'Independent'}

class WILegislatorScraper(LegislatorScraper):
    state = 'wi'
    latest_only = True

    def scrape(self, chamber, term):

        if chamber == 'upper':
            url = "http://legis.wi.gov/w3asp/contact/legislatorslist.aspx?house=senate"
        else:
            url = "http://legis.wi.gov/w3asp/contact/legislatorslist.aspx?house=assembly"

        body = self.urlopen(url)
        page = lxml.html.fromstring(body)
        page.make_links_absolute(url)

        for row in page.xpath("//table[@id='ctl00_C_dgLegData']/tr"):
            if len(row.xpath(".//td/a")) > 0:
                rep_url = row.xpath(".//a/@href")[0]
                rep_doc = lxml.html.fromstring(self.urlopen(rep_url))

                rep_doc_large_name = rep_doc.xpath("//h1")[0].text_content()

                legpart = re.findall(r'([\w\-\,\s\.]+)\s+\(([\w])\)', list(row)[0].text_content())
                if legpart:
                    full_name, party = legpart[0]

                    # skip if the legislator is vacant
                    if full_name == 'Vacant' or rep_doc_large_name == "Vacant":
                        continue

                    party = PARTY_DICT[party]

                    district = str(int(list(row)[2].text_content()))

                    # email
                    email = rep_doc.xpath('//a[starts-with(@href, "mailto")]/text()')
                    if email:
                        email = email[0]
                    else:
                        email = ''

                    leg = Legislator(term, chamber, district, full_name,
                                     party=party, url=rep_url, email=email)
                    leg.add_source(rep_url)

                    # office ####

                    # address is tail of all elements in MadiOffice label
                    address = '\n'.join([x.tail.strip() for x in
                         rep_doc.xpath('//span[@id="ctl00_C_lblMadiOffice"]/*')
                                         if x.tail])
                    # phone number is first line after Telephone h3
                    phone = rep_doc.xpath('//h3[text()="Telephone"]')[0].tail.strip()
                    if phone.endswith('Or'):
                        phone = phone.rsplit(None, 1)[0]
                    # fax is line after Fax h3
                    fax = rep_doc.xpath('//h3[text()="Fax"]')
                    if fax:
                        fax = fax[0].tail.strip() or None
                    else:
                        fax = None
                    leg.add_office('capitol', 'Madison Office',
                                   address=address, phone=phone, fax=fax)


                    # save legislator
                    leg = self.add_committees(leg, rep_url, term, chamber)
                    self.save_legislator(leg)

    def add_committees(self, legislator, rep_url, term, chamber):
        url = rep_url + '&display=committee'
        with self.urlopen(url) as body:
            doc = lxml.html.fromstring(body)

            img = doc.xpath('//img[@id="ctl00_C_picHere"]/@src')
            if img:
                legislator['photo_url'] = img[0]

            cmts = doc.xpath("//span[@id='ctl00_C_lblCommInfo']//a")
            for c in cmts:
                c = c.text_content().split('(')[0].strip()
                # skip subcommittees -- they are broken
                if 'Subcommittee' in c:
                    continue

                if 'Joint' in c or 'Special' in c:
                    c_chamber = 'joint'
                else:
                    c_chamber = chamber
                legislator.add_role('committee member', term, committee=c,
                                    chamber=c_chamber)
            return legislator
