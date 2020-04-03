from openstates.scrape import Scraper, Person
import lxml.html


class NCPersonScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        chamber_letter = dict(lower="H", upper="S")[chamber]
        url = "https://www.ncleg.gov/Members/MemberTable/{}".format(chamber_letter)

        data = self.get(url).text
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute("http://www.ncleg.net")
        rows = doc.xpath('//table[@id="memberTable"]/tbody/tr')
        self.warning("rows found: {}".format(len(rows)))

        for row in rows:
            party, district, _, _, full_name, counties = row.getchildren()

            party = party.text_content().strip()
            party = dict(D="Democratic", R="Republican")[party]

            district = district.text_content().strip()

            notice = full_name.xpath("span")
            if notice:
                notice = notice[0].text_content()
                # skip resigned legislators
                if "Resigned" in notice or "Deceased" in notice:
                    continue
            else:
                notice = None
            link = full_name.xpath("a/@href")[0]
            full_name = full_name.xpath("a")[0].text_content()
            full_name = full_name.replace(u"\u00a0", " ")

            # scrape legislator page details
            lhtml = self.get(link).text
            ldoc = lxml.html.fromstring(lhtml)
            ldoc.make_links_absolute("http://www.ncleg.net")
            photo_url = ldoc.xpath("//figure/a/@href")[0]

            address_xpath = '//h6[@class="mt-3"]/following-sibling::p'
            address = "\n".join(
                [element.text_content() for element in ldoc.xpath(address_xpath)]
            )
            self.warning(address)

            link_xpath = '//a[starts-with(@href, "{}:")]'
            email = ldoc.xpath(link_xpath.format("mailto"))[0].text
            phone = ldoc.xpath(link_xpath.format("tel"))[0].text

            # save legislator
            person = Person(
                name=full_name,
                district=district,
                party=party,
                primary_org=chamber,
                image=photo_url,
            )
            person.extras["counties"] = counties.text_content().split(", ")
            person.extras["notice"] = notice
            person.add_link(link)
            person.add_source(link)
            self.warning(photo_url)
            self.warning(address)
            self.warning(phone)
            self.warning(email)

            if address:
                person.add_contact_detail(
                    type="address", value=address, note="Capitol Office"
                )
            if phone:
                person.add_contact_detail(
                    type="voice", value=phone, note="Capitol Office"
                )
            if email:
                person.add_contact_detail(
                    type="email", value=email, note="Capitol Office"
                )
            yield person
