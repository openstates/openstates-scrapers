import re
import itertools

from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import legislators_url

import lxml.html


class PALegislatorScraper(LegislatorScraper):
    jurisdiction = 'pa'

    def scrape(self, chamber, term):
        # Pennsylvania doesn't make member lists easily available
        # for previous sessions, unfortunately
        self.validate_term(term, latest_only=True)

        leg_list_url = legislators_url(chamber)

        page = self.get(leg_list_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(leg_list_url)

        for link in page.xpath("//a[contains(@href, '_bio.cfm')]"):
            full_name = link.text
            district = link.getparent().getnext().tail.strip()
            district = re.search("District (\d+)", district).group(1)

            party = link.getparent().tail.strip()[-2]
            if party == 'R':
                party = 'Republican'
            elif party == 'D':
                party = 'Democratic'

            url = link.get('href')

            legislator = Legislator(term, chamber, district,
                                    full_name, party=party, url=url)
            legislator.add_source(leg_list_url)

            # Scrape email, offices, photo.
            page = self.get(url).text
            doc = lxml.html.fromstring(page)
            doc.make_links_absolute(url)

            email = self.scrape_email_address(url, page)
            self.scrape_offices(url, doc, legislator, email)
            self.scrape_photo_url(url, doc, legislator)
            self.save_legislator(legislator)

    def scrape_photo_url(self, url, page, legislator):
        photo_urls = page.xpath("//div[@class='MemberBio']//img[contains(@src, '/members/')]/@src")
        if len(photo_urls) == 0:
            self.warning("No photo found for legislator {}".format(legislator['full_name']))
        elif len(photo_urls) == 1:
            legislator['photo_url'] = photo_urls[0]
        else:
            raise AssertionError("Legislator photo parsing needs to be rewritten")

    def scrape_email_address(self, url, page):
        email = None
        if re.search(r'var \S+\s+= "(\S+)";', page):
            vals = re.findall(r'var \S+\s+= "(\S+)";', page)
            email = '%s@%s%s' % tuple(vals)
        return email
        
    def scrape_offices(self, url, doc, legislator, email):
        offices = False

        account_types = ["facebook","twitter","youtube","instagram","pintrest"]
        soc_media_accounts = doc.xpath("//div[contains(@class,'MemberBio-SocialLinks')]/a/@href")
        for acct in soc_media_accounts:
            for sm_site in account_types:
                if sm_site in acct.lower():
                    legislator[sm_site] = acct

        contact_chunks = doc.xpath('//address')
        if contact_chunks == []:
            return
        for contact_chunk in contact_chunks:
            address = []
            office = {}
            for line in contact_chunk.text_content().split("\n"):
                line = line.strip()

                #sometimes office hours are on the same line as the address
                line = line.split("Office Hours")
                if len(line) > 1:
                    office["hours"] = line[1].replace(":","").strip()
                line = line[0]

                #sometimes phone and fax are on the same line:
                if "fax" in line.lower() and not line.lower().startswith("fax"):
                    line, fax = line.lower().split("fax")
                    office["fax"] = fax.lower().replace(":","").strip()

                if line.lower().startswith(("hon.","senator","rep","sen.")):
                    pass
                elif line.lower().startswith("fax"):
                    office["fax"] = line.lower().replace("fax:","").strip()
                elif line.startswith("("):
                    office["phone"] = line.strip()
                elif line.strip() == "":
                    pass
                else:
                    address.append(line.strip())

            if address != []:
                address = "\n".join(address)
                if "17120" in address:
                    office["type"] = "capitol"
                else:
                    office["type"] = "district"
                office["address"] = address
                office["name"] = office["type"].title() + " Office"
                office["email"] = email
                legislator.add_office(**office)
                offices = True
        if not offices and email:
            legislator.add_office(
                type="capitol",
                name="Capitol Office",
                email=email)
        legislator.add_source(url)
