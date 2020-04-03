import lxml.html

from openstates_core.scrape import Person, Scraper


class KYPersonScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        url = (
            "https://legislature.ky.gov/Legislators/senate"
            if chamber == "upper"
            else "https://legislature.ky.gov/Legislators/house-of-representatives"
        )
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for link in page.xpath('//a[contains(@class, "Legislator-Card")]'):
            if "Vacant Seat" in link.text_content():
                continue
            yield from self.scrape_member(chamber, link.get("href"))

    def scrape_member(self, chamber, member_url):
        member_page = self.get(member_url).text
        doc = lxml.html.fromstring(member_page)
        doc.make_links_absolute(member_url)

        photo_url = doc.xpath('//a[@class="download"]/@href')[0]

        name_pieces = doc.xpath('//div[@class="row profile-top"]/h2/text()')[0].split()

        full_name = " ".join(name_pieces[1:-1]).strip()

        party = name_pieces[-1]
        if party == "(R)":
            party = "Republican"
        elif party == "(D)":
            party = "Democratic"
        elif party == "(I)":
            party = "Independent"

        sidebar = doc.xpath('//div[@class="relativeContent col-sm-4 col-xs-12"]')[0]

        district = sidebar.xpath('//div[@class="circle"]/h3/text()')[0]
        district = district.lstrip("0")

        person = Person(
            name=full_name,
            district=district,
            party=party,
            primary_org=chamber,
            image=photo_url,
        )
        person.add_source(member_url)
        person.add_link(member_url)

        info = {}
        sidebar_items = iter(sidebar.getchildren())
        for item in sidebar_items:
            if item.tag == "p":
                info[item.text] = next(sidebar_items)

        address = "\n".join(info["Legislative Address"].xpath("./text()"))

        phone = None
        fax = None
        phone_numbers = info["Phone Number(s)"].xpath("./text()")
        for num in phone_numbers:
            kind, num = num.split(": ")
            if kind == "LRC":
                if num.endswith(" (fax)"):
                    fax = num.replace(" (fax)", "")
                else:
                    phone = num

        email = info["Email"].text

        if phone:
            person.add_contact_detail(type="voice", value=phone, note="Capitol Office")

        if fax:
            person.add_contact_detail(type="fax", value=fax, note="Capitol Office")

        if email:
            person.add_contact_detail(type="email", value=email, note="Capitol Office")

        if address.strip() == "":
            self.warning("Missing Capitol Office!!")
        else:
            person.add_contact_detail(
                type="address", value=address, note="Capitol Office"
            )

        yield person
