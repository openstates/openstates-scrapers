from collections import defaultdict
from urlparse import urlunsplit
from urllib import urlencode
from operator import methodcaller
import re

import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator


class DELegislatorScraper(LegislatorScraper):
    jurisdiction = 'de'

    def scrape(self, chamber, term, text=methodcaller('text_content'),
               re_spaces=re.compile(r'\s{,5}')):

        url = {
            'upper': 'http://legis.delaware.gov/legislature.nsf/sen?openview',
            'lower': 'http://legis.delaware.gov/Legislature.nsf/Reps?openview',
            }[chamber]

        doc = lxml.html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)

        if chamber == "upper":
            #for the senate, it's the same table
            #but the html is hard-coded in js.
            table_js = doc.xpath('.//script')[-1].text_content()
            table = None
            for line in table_js.split("\n"):
                if line.strip().startswith("var") and "sen=" in line:
                    table = line.replace("var","")
                    table = table.replace('sen="<','<')
                    table = table.replace('>";','>')
                    break

            assert table is not None, "Senate table could not be found"

            table = lxml.html.fromstring(table)
            table.make_links_absolute(url)
            trs = table.xpath('//tr')


        else:
            #same table for the house, but kindly in actual html
            trs = doc.xpath('//tr')

        base_url = "http://legis.delaware.gov/"

        for tr in trs:

            name_and_url = tr.xpath('.//a')[0]
            bio_url = name_and_url.attrib["href"]
            bio_url = bio_url.replace("JavaScript:window.location.href=","")
            bio_url = base_url + bio_url.replace('"','')
            name = name_and_url.text_content()
            if name.strip() == "." or name.strip() == "":
                continue
            name = ' '.join(re_spaces.split(name))
            district = tr.xpath('.//td')[2].text_content()
            district = district.replace("District:","").strip()


            leg = self.scrape_bio(term, chamber, district, name, bio_url)
            leg.add_source(bio_url, page="legislator detail page")
            leg.add_source(url, page="legislator list page")
            self.save_legislator(leg)

    def scrape_bio(self, term, chamber, district, name, url):
        # this opens the committee section without having to do another request
        url += '&TableRow=1.5.5'
        doc = lxml.html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)

        # party is in one of these
        party = doc.xpath('//div[@id="page_header"]')[0].text.strip()[-3:]
        if '(D)' in party:
            party = 'Democratic'
        elif '(R)' in party:
            party = 'Republican'
        print party

        leg = Legislator(term, chamber, district, name, party=party)

        photo_url = doc.xpath('//img[contains(@src, "jpg")]/@src')
        if photo_url:
            leg['photo_url'] = photo_url[0]

        contact_info = self.scrape_contact_info(doc)
        leg.update(contact_info)
        return leg

    def scrape_contact_info(self, doc):

        # Email
        email = doc.xpath(".//a[contains(@href,'mailto')]")
        email = email[0].text_content().strip()
        if not email:
            email = None

        # Offices

        leg_office = dict(name="Capitol Office", type="capitol",
                        phone=None, fax=None, email=email, address=None)
        dist_office = dict(name="District Office", type="district",
                        phone=None,fax=None, email=email, address=None) 

        #this is enormously painful, DE.
        office_list = doc.xpath("//tr")
        for office in office_list:
            title_td = 0
            #in some trs the photo is the first td
            if len(office.xpath("./td/img")) > 0:
                title_td = 1
            try:
                title_text = office.xpath("./td")[title_td].text_content().lower()
                content = office.xpath("./td")[title_td+1].text_content()

            except IndexError:
                continue

            if "legislative office" in title_text:
                leg_office["address"] = content.strip()
            if "legislative phone" in title_text:
                phones = content.lower().split("\n")
                if len(phones) == 1:
                    phone = phones[0].replace("phone:","").strip()
                    if phone:
                        leg_office["phone"] = phone
                else:
                    for line in phones:
                        if "phone" in line:
                            leg_office["phone"] = line.replace("phone:","").strip()
                        elif "fax" in line:
                            leg_office["fax"] = line.replace("fax:","").strip()

            if "outside office" in title_text:
                dist_office["address"] = content.strip()
            if "outside phone" in title_text:
                phones = content.lower().split("\n")
                if len(phones) == 1:
                    phone = phones[0].replace("phone:","").strip()
                    if phone:
                        dist_office["phone"] = phone
                else:
                    for line in phones:
                        if "phone" in line:
                            dist_office["phone"] = line.replace("phone:","").strip()
                        elif "fax" in line:
                            dist_office["fax"] = line.replace("fax:","").strip()

        offices = [o for o in [leg_office,dist_office] if o["address"]]

        return {"offices":offices}
