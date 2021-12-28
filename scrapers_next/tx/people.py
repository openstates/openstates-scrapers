import re
import attr
from spatula import HtmlListPage, HtmlPage, XPath
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    district: int
    image: str
    party: str = ""


_phone_pattern = r"\(?\d+\)?[- ]?\d{3}[-.]\d{4}"
_phone_re = re.compile(_phone_pattern + "(?! Fax)", re.IGNORECASE)
_fax_re = re.compile(
    r"(?<=Fax: )%s|%s(?= \(f\)| Fax)" % (_phone_pattern, _phone_pattern), re.IGNORECASE
)
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


def extract_phone(string):
    return next(iter(_phone_re.findall(string)), None)


def extract_fax(string):
    return next(iter(_fax_re.findall(string)), None)


def process_address(details, p, office):
    match = address_re.search(details)
    if match is not None:
        address = re.sub(
            " +$",
            "",
            match.group().replace("\r", "").replace("\n", " ").replace("  ", " "),
            flags=re.MULTILINE,
        )

        if address is not None:
            if office["type"] == "Capitol Address":
                p.capitol_office.address = address
            elif office["type"] == "District Address":
                p.district_office.address = address

    phone_number = extract_phone(details)
    fax_number = extract_fax(details)

    if phone_number:
        if office["type"] == "Capitol Address":
            p.capitol_office.voice = phone_number
        elif office["type"] == "District Address":
            p.district_office.voice = phone_number
    if fax_number:
        if office["type"] == "Capitol Address":
            p.capitol_office.fax = fax_number
        elif office["type"] == "District Address":
            p.district_office.fax = fax_number

    return p


class SenatorList(HtmlListPage):
    source = "https://senate.texas.gov/members.php"
    selector = XPath('//div[@class="mempicdiv"]', num_items=31)

    def process_item(self, item):
        name = item[2].text.replace("  ", " ")
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

        office_ids = []
        # Get offices based on table headers
        for th_tag in self.root.xpath('//table[@class="memdir"]/tr/th'):
            id = th_tag.xpath("@id")[0] if th_tag.xpath("@id") else ""
            label = th_tag.xpath("text()")[0].strip() if th_tag.xpath("text()") else ""
            if id != "" and label != "":
                office_ids.append({"id": id, "label": label, "type": label})

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

            process_address(details, p, office)

        return p


class HouseParties(HtmlListPage):
    source = (
        "https://lrl.texas.gov/legeLeaders/members/membersearch.cfm?leg=87&chamber=H"
    )
    selector = XPath('//table[@id="tableToSort"]/tbody/', num_items=1)

    def process_page(self):
        tds = self.root.xpath(
            '//table[@id="tableToSort"]//td[contains(@class, ' '"results")]',
        )

        party_map = {"D": "Democratic", "R": "Republican"}
        parties = {}
        for td_index, td in enumerate(tds):
            # 0, 2nd and 6th column
            if td_index % 9 == 0:
                name = td.text_content().strip()
            if td_index % 9 == 2:
                district = td.text_content().strip()
            if td_index % 9 == 6:
                party_code = td.text_content().strip()
                if len(party_code) > 1:
                    party_code = re.search(r"[A-Z]", party_code)[0]
                if party_code == "":
                    continue
                party = party_map[party_code]
                parties[district] = {"name": name, "party": party}
        return parties


class RepresentativeList(HtmlListPage):
    source = "https://house.texas.gov/members/"
    selector = XPath('//td[@class="members-img-center"]', num_items=150)
    dependencies = {"party_mapping": HouseParties()}

    def process_item(self, item):
        url = item[1].get("href")
        district = re.search(r"rict=(\d+)", url)[1]
        party = self.party_mapping[district]["party"]
        name = self.party_mapping[district]["name"]
        image = item[1][0].get("src")
        return RepresentativeDetail(
            PartialMember(name, url, district, image, party), source=url
        )


class RepresentativeDetail(HtmlPage):
    input_type = PartialMember

    def process_page(self):
        p = ScrapePerson(
            name=self.input.name,
            state="tx",
            party=self.input.party,
            district=self.input.district,
            chamber="lower",
            image=self.input.image,
        )

        def office_name(element):
            """Returns the office address type."""
            return element.xpath("preceding-sibling::h4[1]/text()")[0].rstrip(":")

        offices_text = [
            {
                "label": office_name(p_tag),
                "type": office_name(p_tag),
                "details": p_tag.text_content(),
            }
            for p_tag in self.root.xpath(
                '//h4/following-sibling::p[@class="double-space"]'
            )
        ]

        for office_text in offices_text:
            details = office_text["details"].strip()

            # A few member pages have blank office listings:
            if details == "":
                continue

            # At the time of writing, this case of multiple district
            # offices occurs exactly once, for the representative at
            # District 4:
            if details.count("Office") > 1:
                district_offices = [
                    district_office.strip()
                    for district_office in re.findall(
                        r"(\w+ Office.+?(?=\w+ Office|$))", details, flags=re.DOTALL
                    )
                ]
                offices_text += [
                    {
                        "label": re.match(r"\w+ Office", office).group(),
                        "type": "District Address",
                        "details": re.search(
                            r"(?<=Office).+(?=\w+ Office|$)?", office, re.DOTALL
                        ).group(),
                    }
                    for office in district_offices
                ]

            process_address(details, p, office_text)

        return p
