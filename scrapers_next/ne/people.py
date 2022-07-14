from spatula import HtmlPage, ListPage, NullSource, CSS
from openstates.models import ScrapePerson


class LegPage(HtmlPage):
    name_css = CSS("h1.mt-0")
    district_css = CSS(".col-9 h2")
    image_css = CSS("img#sen-image")
    address_css = CSS("address")

    def process_page(self):
        district = self.district_css.match_one(self.root).text.split()[1]
        name = self.name_css.match_one(self.root).text.replace("Sen. ", "").strip()
        if name == "Vacant":
            self.logger.warning(f"Vacant seat in {district}")
            return
        image = self.image_css.match_one(self.root).get("src")
        addrlines = self.address_css.match_one(self.root).text_content()

        # example:
        # Room 11th Floor
        # P.O. Box 94604
        # Lincoln, NE 68509
        # (402) 471-2733
        # Email: jslama@leg.ne.gov
        mode = "address"
        address = []
        phone = None
        email = None
        for line in addrlines.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("(402)"):
                phone = line
                mode = None
            if line.startswith("Email:"):
                email = line.replace("Email: ", "")
            if mode == "address":
                address.append(line)

        p = ScrapePerson(
            chamber="legislature",
            party="Nonpartisan",
            state="ne",
            district=district,
            image=image,
            name=name,
            email=email,
        )
        p.capitol_office.address = "; ".join(address)
        p.capitol_office.voice = phone
        p.add_source(self.source.url)
        p.add_link(self.source.url)
        return p


class LegPageGenerator(ListPage):
    source = NullSource()
    """
    NE is an interesting test case for Spatula, since there are individual senator pages
    but no real index that's useful at all.  Right now this is using a dummy source page
    to spawn the 49 subpage scrapers.
    """

    def process_page(self):
        for n in range(1, 50):
            res = LegPage(source=f"http://news.legislature.ne.gov/dist{n:02d}/")
            if res:
                yield res
