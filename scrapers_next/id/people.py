from spatula import CSS, HtmlListPage, URL, XPath
from openstates.models import ScrapePerson
import re


class LegList(HtmlListPage):
    selector = CSS(
        "div .row-equal-height.padding-two-top.sm-padding-two-top.xs-padding-two-top.hcode-inner-row"
    )

    def process_item(self, item):
        img = CSS("img").match(item)[0].get("src")
        name = CSS("p strong").match(item)[0].text_content()
        email = CSS("p strong").match(item)[1].text_content()
        district_full = CSS("p a").match(item)[1].text_content()
        try:
            district = re.search(r"District\s(.+)", district_full).groups()[0]
        except AttributeError:
            self.skip(f"skipping {name}, likely an alternate?")

        all_text = CSS("p").match(item)[1].text_content()
        party_letter = re.search(r"(.+)(\(([A-Z])\))(.+)", all_text).groups()[2]
        party_dict = {"D": "Democratic", "R": "Republican", "I": "Independent"}
        party = party_dict[party_letter]

        p = ScrapePerson(
            name=name,
            state="id",
            party=party,
            chamber=self.chamber,
            district=district,
            image=img,
            email=email,
        )
        addr1 = XPath(".//p/text()").match(item)[5].strip()
        addr2 = XPath(".//p/text()").match(item)[6].strip()
        addr3 = XPath(".//p/text()").match(item)[7].strip()
        if re.search(r"^(\d|P\.?O)", addr1):
            addr = addr1
        elif re.search(r"^(\d|P\.?O)", addr2):
            addr = addr2
        else:
            addr = addr3
        p.district_office.address = addr

        if re.search(r"Home", all_text):
            phones = re.search(
                r"(.+)Home(.+)Statehouse(.+)\(Session\sOnly\)", all_text
            ).groups()
            district_phone = phones[1].strip()
            captiol_phone = phones[2].strip()
            if re.search(r"Bus", district_phone):
                district_phone = district_phone.split("Bus")[0].strip()
            p.district_office.voice = district_phone
        else:
            phones = re.search(
                r"(.+)Statehouse(.+)\(Session\sOnly\)", all_text
            ).groups()
            captiol_phone = phones[1].strip()
        p.capitol_office.voice = captiol_phone

        possible_title = CSS("p strong").match(item)[2].text_content().strip()
        if not re.search(r"Committees:", possible_title):
            p.extras["title"] = possible_title

        if re.search(r"FAX", all_text):
            fax = re.search(
                r"(.+)FAX\s(\(\d{3}\)\s\d{3}-\d{4})(.+)", all_text
            ).groups()[1]
            p.capitol_office.fax = fax

        district_link = CSS("p a").match(item)[1].get("href")
        p.add_source(self.source.url)
        p.add_link(district_link, note="homepage")

        return p


class Senate(LegList):
    source = URL("https://legislature.idaho.gov/senate/membership/")
    chamber = "upper"


class House(LegList):
    source = URL("https://legislature.idaho.gov/house/membership/")
    chamber = "lower"
