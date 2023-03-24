import re
from spatula import (
    HtmlListPage,
    HtmlPage,
    XPath,
    SimilarLink,
    CSS,
    SelectorError,
    SkipItem,
)
from openstates.models import ScrapePerson


class PersonDetail(HtmlPage):
    def parse_address_block(self, block):
        state = "address"
        # group lines by type
        values = {"address": [], "phone": [], "fax": [], "toll-free": []}
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("Phone"):
                state = "phone"
            elif line.startswith("Fax"):
                state = "fax"
            elif line.startswith("Toll-free"):
                state = "toll-free"
            else: state = "address"

            values[state].append(line)

        # postprocess values

        result = {}
        phones = []
        for line in values["phone"]:
            for match in re.findall(r"\d{3}-\d{3}-\d{4}", line):
                phones.append(match)
        if len(phones) > 0:
            result["voice"] = phones[0]

        faxes = []
        for line in values["fax"]:
            for match in re.findall(r"\d{3}-\d{3}-\d{4}", line):
                faxes.append(match)
        if len(faxes) > 0:
            result["fax"] = faxes[0]

        result["address"] = ";".join(values["address"])
        return result

    def extract_dd(self, name):
        return (
            XPath(f"//dt[text()='{name}']/following-sibling::dd[1]")
            .match_one(self.root)
            .text_content()
        )

    image_sel = CSS("img.details-page-image-padding")


    def process_page(self):
        annapolis_text = (
            XPath("//dt[text()='Annapolis Info']/following-sibling::dd[1]")
            .match_one(self.root)
             .text_content()
        )
        annapolis_info = self.parse_address_block(annapolis_text)
        annapolis_info["classification"] = "capitol"
        # interim_text = (
        #    XPath("//dt[text()='Interim Info']/following-sibling::dd[1]")
        #    .match_one(self.root)
        #    .text_content()
        # )
        # interim_info = self.parse_address_block(interim_text)

        # email is formatted mailto:<addr>?body...
        try:
            email = SimilarLink("mailto:").match_one(self.root).get("href")
            email = email.split(":", 1)[1].split("?")[0]
        except SelectorError:
            email = ""

        p = ScrapePerson(
            name=CSS("h2").match_one(self.root).text.split(" ", 1)[1],
            state="md",
            image=self.image_sel.match_one(self.root).get("src"),
            party=self.extract_dd("Party"),
            district=self.extract_dd("District"),
            chamber=self.input["chamber"],
            email=email,
        )

        p.capitol_office = annapolis_info
        p.add_link(self.source.url)
        p.add_source(self.source.url)
        return p


class PersonList(HtmlListPage):
    selector = XPath(
        "//div[@id='myDIV']//div[@class='p-0 member-index-cell col-print-6']"
    )

    def process_item(self, item):
        dd_text = XPath(".//dd/text()").match(item)
        district = dd_text[2].strip().split()[1]
        party = dd_text[4].strip()
        url = str(XPath(".//dd/a[1]/@href").match_one(item))
        if "Details" not in url:
            raise SkipItem(f"skipping {url}")
        return PersonDetail(
            dict(
                chamber="upper" if "senate" in self.source.url else "lower",
                district=district,
                party=party,
            ),
            source=url,
        )


class DelegateList(PersonList):
    source = "http://mgaleg.maryland.gov/mgawebsite/Members/Index/house"


class SenatorList(PersonList):
    source = "http://mgaleg.maryland.gov/mgawebsite/Members/Index/senate"
