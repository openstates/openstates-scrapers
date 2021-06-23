import re
import attr
from spatula import HtmlListPage, HtmlPage, XPath
from ..common.people import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    district: int
    image: str


_phone_pattern = r"\(?\d+\)?[- ]?\d{3}[-.]\d{4}"
_phone_re = re.compile(_phone_pattern + "(?! Fax)", re.IGNORECASE)
_fax_re = re.compile(
    r"(?<=Fax: )%s|%s(?= \(f\)| Fax)" % (_phone_pattern, _phone_pattern), re.IGNORECASE
)


def extract_phone(string):
    return next(iter(_phone_re.findall(string)), None)


def extract_fax(string):
    return next(iter(_fax_re.findall(string)), None)


class SenatorList(HtmlListPage):
    source = "https://senate.texas.gov/members.php"
    selector = XPath('//div[@class="mempicdiv"]', num_items=31)

    def process_item(self, item):
        name = item[2].text
        url = item[0].get("href")
        district = re.match(r"District (\d+)", item[4].text)[1]
        image = item[0][0].get("src")
        return SenatorDetail(PartialMember(name, url, district, image), source=url)


class SenatorDetail(HtmlPage):
    input_type = PartialMember

    def process_page(self):
        party = self.root.xpath('//*[@id="mempg_top"]/div[2]/p[last()]/text()')[
            0
        ].strip()

        p = ScrapePerson(
            name=self.input.name,
            state="tx",
            party=party,
            district=self.input.district,
            chamber="upper",
            image=self.input.image,
        )
        p.add_link(self.source.url)
        p.add_source(self.source.url)
        address_re = re.compile(
            (
                # Every representative's address starts with a room number,
                # street number, or P.O. Box:
                r"(?:Room|\d+|P\.?\s*O)"
                # Just about anything can follow:
                + ".+?"
                # State and zip code (or just state) along with idiosyncratic
                # comma placement:
                + "(?:"
                + "|".join([r", +(?:TX|Texas)(?: +7\d{4})?", r"(?:TX|Texas),? +7\d{4}"])
                + ")"
            ),
            flags=re.DOTALL | re.IGNORECASE,
        )

        office_ids = []
        # Get offices based on table headers
        for th_tag in self.root.xpath('//table[@class="memdir"]/tr/th'):
            id = th_tag.xpath("@id")[0] if th_tag.xpath("@id") else ""
            label = th_tag.xpath("text()")[0].strip() if th_tag.xpath("text()") else ""
            if id != "" and label != "":
                office_ids.append({"id": id, "label": label})

        for office in office_ids:
            row = self.root.xpath(
                f'//table[@class="memdir"]/tr/td[@headers="{office["id"]}"]'
            )
            # A few member pages have broken ids for office listings:
            if len(row) == 0:
                row = self.root.xpath('//table[@class="memdir"]/tr/td[@headers="dDA1"]')
            if len(row) > 0:
                details = " ".join(row[0].xpath("text()")).strip()
                details = details.replace("\r", "").replace("\n", "")
            # A few member pages have blank office listings:
            if details == "":
                continue

            match = address_re.search(details)
            if match is not None:
                address = re.sub(
                    " +$",
                    "",
                    match.group().replace("\r", "").replace("\n", ""),
                    flags=re.MULTILINE,
                )
            else:
                # No valid address found in the details.
                continue

            phone_number = extract_phone(details)
            fax_number = extract_fax(details)

            if address:
                if office["label"] == "Capitol Address":
                    p.capitol_office.address = address
                elif office["label"] == "District Address":
                    p.district_office.address = address
            if phone_number:
                if office["label"] == "Capitol Address":
                    p.capitol_office.voice = phone_number
                elif office["label"] == "District Address":
                    p.district_office.voice = phone_number
            if fax_number:
                if office["label"] == "Capitol Address":
                    p.capitol_office.fax = fax_number
                elif office["label"] == "District Address":
                    p.district_office.fax = fax_number

        return p


class RepList(HtmlListPage):
    source = "https://house.texas.gov/members/"
    selector = XPath('//td[@class="members-img-center"]', num_items=150)

    def process_item(self, item):
        name = item[1][2].text
        # scraped = re.match(r'Rep\.\s(.+), (.+)', scraped_name).groups()
        #
        # name = f'{scraped[1]} {scraped[0]}'
        url = item[1].get("href")
        district = re.match(r"=(\d+)", url)
        image = item[1][0].get("src")
        return print(name, url, district, image)
