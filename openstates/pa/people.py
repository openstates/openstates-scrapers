import re

import lxml.html
from pupa.scrape import Scraper, Person


base_url = 'http://www.legis.state.pa.us'
urls = {
    'upper': '{}/cfdocs/legis/home/member_information/senators_alpha.cfm'.format(base_url),
    'lower': '{}/cfdocs/legis/home/member_information/representatives_alpha.cfm'.format(base_url),
}


class PALegislatorScraper(Scraper):
    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        leg_list_url = urls[chamber]
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

            person = Person(name=full_name, district=district, party=party,
                            primary_org=chamber)
            person.add_link(leg_list_url)
            person.add_source(leg_list_url)

            # Scrape email, offices, photo.
            page = self.get(url).text
            doc = lxml.html.fromstring(page)
            doc.make_links_absolute(url)

            email = self.scrape_email_address(url, page)
            self.scrape_offices(url, doc, person, email)
            self.scrape_photo_url(url, doc, person)

            yield person

    def scrape_photo_url(self, url, page, person):
        photo_urls = page.xpath("//div[@class='MemberBio']//img[contains(@src, '/members/')]/@src")
        if len(photo_urls) == 0:
            self.warning("No photo found for legislator {}".format(person.name))
        elif len(photo_urls) == 1:
            person.image = photo_urls[0]
        else:
            raise AssertionError("Legislator photo parsing needs to be rewritten")

    def scrape_email_address(self, url, page):
        if re.search(r'var \S+\s+= "(\S+)";', page):
            vals = re.findall(r'var \S+\s+= "(\S+)";', page)
            return '%s@%s%s' % tuple(vals)

    def scrape_offices(self, url, doc, person, email):
        offices = False

        # TODO(jmcarp) restore social media accounts
        # account_types = ["facebook", "twitter", "youtube", "instagram", "pintrest"]
        # soc_media_accounts = doc.xpath("//div[contains(@class,'MemberBio-SocialLinks')]/a/@href")
        # for acct in soc_media_accounts:
        #     for sm_site in account_types:
        #         if sm_site in acct.lower():
        #             legislator[sm_site] = acct

        contact_chunks = doc.xpath('//address')
        if contact_chunks == []:
            return
        for contact_chunk in contact_chunks:
            address = []
            phone, fax = None, None
            for line in contact_chunk.text_content().split("\n"):
                line = line.strip()

                line = line.split("Office Hours")
                line = line[0]

                # sometimes phone and fax are on the same line:
                if "fax" in line.lower() and not line.lower().startswith("fax"):
                    line, fax = line.lower().split("fax")
                    fax = fax.lower().replace(":", "").strip()

                if line.lower().startswith(("hon.", "senator", "rep", "sen.")):
                    pass
                elif line.lower().startswith("fax"):
                    fax = line.lower().replace("fax:", "").strip()
                elif line.startswith("("):
                    phone = line.strip()
                elif line.strip() == "":
                    pass
                else:
                    address.append(line.strip())

            if address:
                address = '\n'.join(address)
                note = 'Capitol Office' if '17120' in address else 'District Office'
                person.add_contact_detail(type='address', value=address, note=note)
                if phone is not None:
                    person.add_contact_detail(type='voice', value=phone, note=note)
                if fax is not None:
                    person.add_contact_detail(type='fax', value=fax, note=note)
                offices = True

        if not offices and email:
            person.add_contact_detail(type='email', value=email, note='Capitol Office')

        person.add_source(url)
