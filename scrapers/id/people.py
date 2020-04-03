import re
import lxml.html
from openstates.scrape import Scraper, Person

BASE_URL = "https://legislature.idaho.gov/%s/membership/"
CHAMBERS = {"upper": "senate", "lower": "house"}
PARTY = {"(R)": "Republican", "(D)": "Democratic"}

phone_patterns = {
    "office": re.compile(r"Statehouse"),
    "business": re.compile(r"Bus"),
    "home": re.compile(r"Home"),
}

parse_phone_pattern = re.compile(r"tel:(?:\+1)?(\d{10}$)")
fax_pattern = re.compile(r"fax\s+\((\d{3})\)\s+(\d{3})-(\d{4})", re.IGNORECASE)
address_pattern = re.compile(r", \d{5}")
address_replace_pattern = re.compile(r"(\d{5})")


def get_phones(el):
    phones = {}
    for link in el.xpath('p/a[@class = "mob-tel"]'):
        prefix = link.getprevious().tail
        for label, pattern in phone_patterns.items():
            if pattern.search(prefix) is not None:
                phones[label] = parse_phone(link.get("href"))
    return phones


def parse_phone(phone):
    res = parse_phone_pattern.search(phone)
    if res is not None:
        return res.groups()[0]


def get_fax(el):
    res = fax_pattern.search(el.text_content())
    if res is not None:
        return "".join(res.groups())


def get_address(el):
    for br in el.xpath("p/br"):
        piece = (br.tail or "").strip()
        res = address_pattern.search(piece)
        if res is not None:
            return address_replace_pattern.sub(r"ID \1", piece).strip()


class IDPersonScraper(Scraper):
    """Legislator data seems to be available for the current term only."""

    jurisdiction = "id"

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        """
        Scrapes legislators for the current term only
        """
        # self.validate_term(term, latest_only=True)
        url = BASE_URL % CHAMBERS[chamber].lower()
        index = self.get(url).text
        html = lxml.html.fromstring(index)
        html.make_links_absolute(url)

        rows = html.xpath('//div[contains(@class, "row-equal-height")]')

        for row in rows:
            img_url = row.xpath(".//img/@src")[0]

            inner = row.xpath('.//div[@class="vc-column-innner-wrapper"]')[1]
            inner_text = inner.text_content()
            if "Resigned" in inner_text or "Substitute" in inner_text:
                continue

            name = inner.xpath("p/strong")[0].text.replace(u"\xa0", " ").strip()
            name = re.sub(r"\s+", " ", name)
            party = PARTY[inner.xpath("p/strong")[0].tail.strip()]
            email = inner.xpath("p/strong/a")[0].text
            district = inner.xpath("p/a")[0].text.replace("District ", "")

            person_url = inner.xpath("p/a/@href")[0]
            # skip roles for now
            role = ""
            # for com in inner.xpath('p/a[contains(@href, "committees")]'):
            #     role = com.tail.strip()

            person = Person(
                name=name,
                district=district,
                party=party,
                primary_org=chamber,
                image=img_url,
                role=role,
            )
            phones = get_phones(inner)
            phone = phones.get("home") or phones.get("business")
            office_phone = phones.get("office")
            address = get_address(inner)
            fax = get_fax(inner)
            if address:
                person.add_contact_detail(
                    type="address", value=address, note="District Office"
                )
            if phone:
                person.add_contact_detail(
                    type="voice", value=phone, note="District Office"
                )
            if fax:
                person.add_contact_detail(type="fax", value=fax, note="District Office")
            if email:
                person.add_contact_detail(
                    type="email", value=email, note="District Office"
                )
            if office_phone:
                person.add_contact_detail(
                    type="voice", value=office_phone, note="Capitol Office"
                )
            person.add_source(url)
            person.add_link(person_url)
            yield person
