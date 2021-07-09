import re
from spatula import HtmlListPage, HtmlPage, XPath, SimilarLink, CSS
from openstates.models import ScrapePerson


class PersonDetail(HtmlPage):
    def parse_address_block(self, block):
        state = "address"
        # group lines by type
        values = {"address": [], "phone": [], "fax": []}
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("Phone"):
                state = "phone"
            elif line.startswith("Fax"):
                state = "fax"

            values[state].append(line)

        # postprocess values

        phones = []
        for line in values["phone"]:
            for match in re.findall(r"\d{3}-\d{3}-\d{4}", line):
                phones.append(match)

        faxes = []
        for line in values["fax"]:
            for match in re.findall(r"\d{3}-\d{3}-\d{4}", line):
                faxes.append(match)

        return {
            "address": "; ".join(values["address"]),
            "phones": phones,
            "faxes": faxes,
        }

    def extract_dd(self, name):
        return (
            XPath(f"//dt[text()='{name}']/following-sibling::dd[1]")
            .match_one(self.root)
            .text_content()
        )

    image_sel = CSS("img.details-page-image-padding")

    def process_page(self):
        # annapolis_info = (
        #     XPath("//dt[text()='Annapolis Info']/following-sibling::dd[1]")
        #     .match_one(self.root)
        #     .text_content()
        # )
        # interim_info = (
        #     XPath("//dt[text()='Interim Info']/following-sibling::dd[1]")
        #     .match_one(self.root)
        #     .text_content()
        # )

        # email is formatted mailto:<addr>?body...
        email = SimilarLink("mailto:").match_one(self.root).get("href")
        email = email.split(":", 1)[1].split("?")[0]

        p = ScrapePerson(
            name=CSS("h2").match_one(self.root).text.split(" ", 1)[1],
            state="md",
            image=self.image_sel.match_one(self.root).get("src"),
            party=self.extract_dd("Party"),
            district=self.extract_dd("District"),
            chamber=None,
            email=email,
        )
        p.add_link(self.source.url)
        p.add_source(self.source.url)
        return p


class PersonList(HtmlListPage):
    selector = XPath("//div[@id='myDIV']//div[@class='p-0 member-index-cell']")

    def process_item(self, item):
        dd_text = XPath(".//dd/text()").match(item)
        district = dd_text[2].strip().split()[1]
        party = dd_text[4].strip()
        return PersonDetail(
            dict(
                chamber="upper" if "senate" in self.source.url else "lower",
                district=district,
                party=party,
            ),
            source=str(XPath(".//dd/a[1]/@href").match_one(item)),
        )


delegates = PersonList(
    source="http://mgaleg.maryland.gov/mgawebsite/Members/Index/house"
)
senators = PersonList(
    source="http://mgaleg.maryland.gov/mgawebsite/Members/Index/senate"
)
