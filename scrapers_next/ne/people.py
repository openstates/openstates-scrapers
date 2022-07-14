import attr
from openstates.models import ScrapePerson
from spatula import HtmlPage, HtmlListPage, CSS, URL


@attr.s
class LegPartial:
    name = attr.ib()
    district = attr.ib()
    url = attr.ib()


class LegPage(HtmlPage):
    input_type = LegPartial

    def get_source_from_input(self):
        return self.input.url

    def process_page(self):
        name = self.input.name
        district = self.input.district
        image = CSS("img#sen-image").match_one(self.root).get("src")
        addrlines = CSS("address").match_one(self.root).text_content()

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


class Legislature(HtmlListPage):
    source = URL(
        "https://nebraskalegislature.gov/senators/senator_list.php", timeout=30
    )
    selector = CSS("div.card ul.dist_list li.sen-list-item", min_items=49)

    def process_item(self, item):
        name = CSS("a div span").match(item)[0].text
        if "Speaker of the Legislature" in name:
            self.skip("not a person")
        if "Vacant" in name:
            self.skip("vacant")
        district = int(CSS("a div span").match(item)[1].text)
        return LegPage(
            LegPartial(
                name=name,
                district=district,
                url=f"http://news.legislature.ne.gov/dist{district:02d}/",
            )
        )
