from pupa.scrape import Scraper, Person
import re
import lxml.html


def get_field(doc, key):
    # get text_content of parent of the element containing the key
    # elem = doc.xpath('//div[@id="member-info"]/p/strong[text()="%s"]/..' % key)
    elem = doc.xpath('//li[contains(@class,"column")]/h4[text()="%s"]/../p')
    if elem:
        return elem[0].text_content().strip()
    else:
        return ""


class DCPersonScraper(Scraper):
    def scrape(self):
        council_url = "http://dccouncil.us/councilmembers/"
        data = self.get(council_url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(council_url)
        # page should have 13 unique council URLs
        urls = set(doc.xpath('//a[contains(@href, "dccouncil.us/council/")]/@href'))
        # print '\n'.join(urls)
        assert len(urls) <= 13, "should have 13 unique councilmember URLs"

        for url in urls:
            data = self.get(url).text
            doc = lxml.html.fromstring(data)
            doc.make_links_absolute(url)

            descriptor = doc.xpath(
                '//div[contains(@class,"media-object-section")]/'
                'p[contains(@class,"h4")]/text()'
            )[0]
            title_name = doc.xpath(
                '//div[contains(@class,"media-object-section")]/h1/text()'
            )[0]

            # removes the title that is prepended to the name
            name = re.sub(r"^Councilmember ", "", title_name)

            if "chairman" in descriptor.lower():
                district = "Chairman"
            elif "at-large" in descriptor.lower():
                district = "At-Large"
            else:
                district = descriptor.split("&bullet;")[1].strip()

            # party
            party = get_field(doc, "Political Affiliation")
            if "Democratic" in party:
                party = "Democratic"
            elif "Republican" in party:
                party = "Republican"
            else:
                party = "Independent"

            photo_url = doc.xpath("//figure/a/img/@src")
            if photo_url:
                photo_url = photo_url[0]
            else:
                photo_url = ""

            office_address = get_field(doc, "Office")

            faxes = doc.xpath('//p[@class="byline"]/text()')
            fax = faxes[-1].strip()

            email = (
                doc.xpath('//p[@class="byline"]/a[@class="contact-link"]')[0]
                .text_content()
                .strip()
            )
            phone = (
                doc.xpath('//p[@class="byline"]/a[@class="contact-link"]')[1]
                .text_content()
                .strip()
            )

            bio = "\n".join(
                doc.xpath('//div[contains(@class,"js-hide")]/p/text()')
            ).strip()
            if doc.xpath('//p[contains(@class,"page-summary")]'):
                short_bio = (
                    doc.xpath('//p[contains(@class,"page-summary")]')[0]
                    .text_content()
                    .strip()
                )

            person = Person(
                name=name,
                party=party,
                image=photo_url,
                primary_org="legislature",
                district=str(district),
                biography=bio,
                summary=short_bio,
            )

            person.add_source(url)
            person.add_link(url)

            if office_address:
                person.add_contact_detail(
                    type="address", value=office_address, note="Capitol Office"
                )
            if phone:
                person.add_contact_detail(
                    type="voice", value=phone, note="Capitol Office"
                )
            if fax:
                person.add_contact_detail(type="fax", value=fax, note="Capitol Office")
            if email:
                person.add_contact_detail(
                    type="email", value=email, note="Capitol Office"
                )

            yield person
