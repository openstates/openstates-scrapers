from openstates.scrape import Person, Scraper
import lxml.html
import re


class NDPersonScraper(Scraper):
    def scrape(self, chamber=None):

        # figuring out starting year from metadata
        start_year = self.jurisdiction.legislative_sessions[-1]["start_date"][:4]
        term = self.jurisdiction.legislative_sessions[-1]["identifier"]
        root = "http://www.legis.nd.gov/assembly"
        main_url = "%s/%s-%s/members/members-by-district" % (root, term, start_year)

        page = self.get(main_url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(main_url)
        for idx, person_url in enumerate(
            page.xpath(
                '//div[contains(@class, "all-members")]/' 'div[@class="name"]/a/@href'
            )
        ):
            political_party = page.xpath(
                '//div[contains(@class, "all-members")]/' 'div[@class="party"]/text()'
            )[idx].strip()
            yield from self.scrape_legislator_page(term, person_url, political_party)

    def scrape_legislator_page(self, term, url, political_party):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        name = page.xpath("//h1[@id='page-title']/text()")[0]
        name = re.sub(r"^(Representative|Senator)\s", "", name)
        district = page.xpath("//a[contains(@href, 'district')]/text()")[0]
        district = district.replace("District", "").strip()

        photo = page.xpath("//div[@class='field-person-photo']/img/@src")
        photo = photo[0] if len(photo) else None

        address = page.xpath("//div[@class='adr']")
        if address:
            address = address[0]
            address = re.sub("[ \t]+", " ", address.text_content()).strip()
        else:
            address = None

        item_mapping = {
            "email": "email",
            "home telephone": "home-telephone",
            "cellphone": "cellphone",
            "office telephone": "office-telephone",
            "political party": "party",
            "chamber": "chamber",
            "fax": "fax",
        }
        metainf = {}
        headings = page.xpath('//div[contains(@class, "pane-content")]//strong')
        metainf["district"] = (
            headings[0].xpath("following-sibling::a/text()")[0].strip()
        )
        metainf["political party"] = (
            headings[1].xpath("following-sibling::text()")[0].strip()
        )
        metainf["chamber"] = headings[2].xpath("following-sibling::text()")[0].strip()
        for block in page.xpath("//div[contains(@class, 'field-label-inline')]"):
            label, items = block.xpath("./*")
            key = label.text_content().strip().lower()
            if key.endswith(":"):
                key = key[:-1]
            metainf[item_mapping[key]] = items.text_content().strip()

        chamber = {"Senate": "upper", "House": "lower"}[metainf["chamber"]]
        party = {"Democrat": "Democratic", "Republican": "Republican"}[political_party]
        person = Person(
            primary_org=chamber, district=district, name=name, party=party, image=photo
        )
        person.add_link(url)
        for key, person_key in [
            ("email", "email"),
            ("fax", "fax"),
            ("office-telephone", "voice"),
        ]:
            if key in metainf:
                if metainf[key].strip():
                    person.add_contact_detail(
                        type=person_key, value=metainf[key], note="Capitol Office"
                    )
        if address:
            person.add_contact_detail(
                type="address", value=address, note="District Office"
            )
        if "cellphone" in metainf:
            person.add_contact_detail(
                type="voice", value=metainf["cellphone"], note="District Office"
            )
        if "home-telephone" in metainf:
            person.add_contact_detail(
                type="voice", value=metainf["home-telephone"], note="District Office"
            )

        person.add_source(url)
        yield person
