import re
import attr
from spatula import HtmlListPage, HtmlPage, XPath, URL
from openstates.models import ScrapePerson


def fix_name(name):
    if ", " not in name:
        return name
    if name.endswith(", Jr."):
        last, first, suffix = name.split(", ")
        return f"{first} {last}, {suffix}"
    else:
        # handles cases like Watson, Jr., Clovis
        last, first = name.rsplit(", ", 1)
        return f"{first} {last}"


@attr.s(auto_attribs=True)
class PartialPerson:
    name: str
    party: str
    district: str
    url: str
    image: str = ""  # default empty, required for Rep


class Senators(HtmlListPage):
    source = "https://flsenate.gov/Senators/"
    selector = XPath("//a[@class='senatorLink']")

    def process_item(self, item):
        name = " ".join(item.xpath(".//text()"))
        name = re.sub(r"\s+", " ", name).replace(" ,", ",").strip()

        if "Vacant" in name:
            self.skip()

        district = item.xpath("string(../../td[1])")
        party = item.xpath("string(../../td[2])")
        leg_url = item.get("href")

        # retired members have missing fields
        if not district or not party or not leg_url:
            self.skip()

        return SenDetail(
            PartialPerson(name=name, party=party, district=district, url=leg_url)
        )


class SenDetail(HtmlPage):
    contact_xpath = XPath('//h4[contains(text(), "Office")]')
    input_type = PartialPerson

    def get_source_from_input(self):
        return URL(self.input.url, timeout=30)

    def process_page(self):
        email = (
            self.root.xpath('//a[contains(@href, "mailto:")]')[0]
            .get("href")
            .split(":")[-1]
        )
        p = ScrapePerson(
            state="fl",
            chamber="upper",
            name=fix_name(self.input.name),
            party=str(self.input.party),
            district=str(self.input.district),
            email=email,
            image=str(self.root.xpath('//div[@id="sidebar"]//img/@src').pop()),
        )

        for item in self.contact_xpath.match(self.root):
            self.handle_office(item, p)

        return p

    def handle_office(self, office, person):
        (name,) = office.xpath("text()")
        if name == "Tallahassee Office":
            obj_office = person.capitol_office
        else:
            obj_office = person.district_office

        address_lines = [
            x.strip()
            for x in office.xpath("following-sibling::div[1]")[0]
            .text_content()
            .splitlines()
            if x.strip()
        ]

        clean_address_lines = []
        fax = phone = ""
        PHONE_RE = r"\(\d{3}\)\s\d{3}\-\d{4}"
        after_phone = False

        for line in address_lines:
            if re.search(r"(?i)open\s+\w+day", address_lines[0]):
                continue
            elif "FAX" in line:
                fax = line.replace("FAX ", "")
                after_phone = True
            elif re.search(PHONE_RE, line):
                phone = line
                after_phone = True
            elif not after_phone:
                clean_address_lines.append(line)

        address = "; ".join(clean_address_lines)
        address = re.sub(r"\s{2,}", " ", address)
        obj_office.address = address
        obj_office.voice = phone
        obj_office.fax = fax


class RepContact(HtmlPage):
    input_type = PartialPerson

    def get_source_from_input(self):
        """
        Transform from
            /Sections/Representatives/details.aspx?MemberId=#&LegislativeTermId=#
        to:
            /Sections/Representatives/contactmember.aspx?MemberId=#&SessionId=#
        """
        return self.input.url.replace("details.aspx", "contactmember.aspx")

    def process_page(self):
        p = ScrapePerson(
            state="fl",
            chamber="lower",
            name=fix_name(self.input.name),
            party=str(self.input.party),
            district=str(self.input.district),
            image=self.input.image,
        )
        for otype in ("district", "capitol"):
            odoc = self.root.xpath(f"//h3[@id='{otype}-office']/following-sibling::ul")
            if odoc:
                odoc = odoc[0]
            else:
                continue
            spans = odoc.xpath(".//span")

            office = p.capitol_office if otype == "capitol" else p.district_office
            office.address = "; ".join(
                line.strip()
                for line in spans[0].text_content().strip().splitlines()
                if line.strip()
            )
            office.voice = spans[1].text_content().strip()

        return p


class Representatives(HtmlListPage):
    source = "https://myfloridahouse.gov/Representatives"
    # kind of wonky xpath to not get the partial term people at the bottom of the page
    selector = XPath("(//div[@class='team-page'])[1]//div[@class='team-box']")

    IMAGE_BASE = "https://www.myfloridahouse.gov/"

    def process_item(self, item):
        name = item.xpath("./a/div[@class='team-txt']/h5/text()")[0].strip()

        # hack for empty chairs
        if name == "Pending, Election":
            self.skip()

        party = item.xpath("./a/div[@class='team-txt']/p[1]/text()")[0].split()[0]
        district = item.xpath("./a/div[@class='team-txt']/p[1]/span/text()")[0].split()[
            -1
        ]
        image = self.IMAGE_BASE + item.xpath(".//img")[0].attrib["data-src"]
        link = str(item.xpath("./a/@href")[0])

        return RepContact(
            PartialPerson(
                name=name,
                party=str(party),
                district=str(district),
                image=image,
                url=link,
            )
        )
