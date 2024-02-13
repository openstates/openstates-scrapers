import datetime
import re
import attr
from spatula import HtmlPage, HtmlListPage, XPath, URL
from openstates.models import ScrapePerson

PARTY_MAP = {"R": "Republican", "D": "Democratic", "I": "Independent"}
party_district_pattern = re.compile(r"\((R|D|I)\) - (?:House|Senate) District\s+(\d+)")
name_elect_pattern = re.compile(r"(- Elect)$")


def get_party_district(text):
    return party_district_pattern.match(text).groups()


lis_id_patterns = {
    "upper": re.compile(r"(S[0-9]+$)"),
    "lower": re.compile(r"(H[0-9]+$)"),
}


def get_lis_id(chamber, url):
    """Retrieve LIS ID of legislator from URL."""
    match = re.search(lis_id_patterns[chamber], url)
    if match.groups:
        return match.group(1)


def clean_name(name):
    name = name_elect_pattern.sub("", name).strip()
    action, date = (None, None)
    match = re.search(r"-(Resigned|Member) (\d{1,2}/\d{1,2})?", name)
    if match:
        action, date = match.groups()
        name = name.rsplit("-")[0]
    return name, action, date


def maybe_date(text):
    try:
        date = datetime.datetime.strptime(text, "%Y-%d-%m")
        return date.strftime("%Y-%m-%d")
    except ValueError:
        return ""

    # TODO: restore when we do committees again
    # def get_committees(self, item):
    #     for com in item.xpath('//ul[@class="linkSect"][1]/li/a/text()'):
    #         key = (com, self.chamber)
    #         if key not in self.kwargs["committees"]:
    #             org = Organization(
    #                 name=com, chamber=self.chamber, classification="committee"
    #             )
    #             org.add_source(self.url)
    #             self.kwargs["committees"][key] = org

    #         self.obj.add_membership(
    #             self.kwargs["committees"][key],
    #             start_date=maybe_date(self.kwargs["session"].get("start_date")),
    #             end_date=maybe_date(self.kwargs["session"].get("end_date", "")),
    #         )


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    image: str = None


class MemberList(HtmlListPage):
    session_id = "241"  # 2024
    source = f"https://lis.virginia.gov/{session_id}/mbr/MBR.HTM"

    def process_item(self, item):
        name = item.text

        lname = name.lower()
        if "resigned" in lname or "vacated" in lname or "retired" in lname:
            return

        name, action, date = clean_name(name)

        return self.next_page_cls(
            PartialMember(name=name, url=item.get("href")),
            source=URL(item.get("href"), timeout=10),
        )


class MemberDetail(HtmlPage):
    input_type = PartialMember

    def process_page(self):
        party_district_text = self.root.xpath("//h3/font/text()")[0]
        party, district = get_party_district(party_district_text)
        p = ScrapePerson(
            name=self.input.name,
            state="va",
            chamber=self.chamber,
            party=party,
            district=district,
        )
        if self.input.image:
            p.image = self.input.image
        p.add_link(self.source.url)
        p.add_source(self.source.url)

        self.get_offices(p)

        return p

    def get_offices(self, person):
        # div[1] and div[2] is where contacted info is located
        for i in range(1, 3):
            for ul in self.root.xpath(f"/html/body/div/div[2]/div[2]/div[{i}]/ul"):
                address = []
                phone = None
                email = None
                for li in ul.getchildren():
                    text = li.text_content()
                    if re.match(r"\(\d{3}\)", text):
                        phone = text.strip()
                    elif text.startswith("email:"):
                        email = text.strip("email: ").strip()
                    else:
                        address.append(text.strip())

                    # the first contact block is capital
                    if i == 1:
                        office_obj = person.capitol_office

                    else:
                        office_obj = person.district_office

                office_obj.address = "; ".join(address)
                if phone:
                    # making sure we don't add the same phone number for district and capitol offices
                    if i != 1:
                        office_obj.voice = phone
                    else:
                        if phone == person.capitol_office.voice:
                            office_obj.voice = ""
                if email:
                    person.email = email


class SenateDetail(MemberDetail):
    input_type = PartialMember
    role = "Senator"
    chamber = "upper"


class SenatePhotoDetail(HtmlPage):
    input_type = PartialMember

    def get_source_from_input(self):
        lis_id = get_lis_id("upper", self.input.url)
        return f"http://apps.senate.virginia.gov/Senator/memberpage.php?id={lis_id}"

    def process_page(self):
        src = self.root.xpath('.//img[@class="profile_pic"]/@src')
        img = src[0] if src else None
        if img and img.startswith("//"):
            img = "https:" + img
        self.input.image = img
        return SenateDetail(self.input, source=self.input.url)


class DelegateDetail(MemberDetail):
    role = "Delegate"
    chamber = "lower"

    def process_page(self):
        p = super().process_page()
        lis_id = get_lis_id(self.chamber, self.input.url)
        if lis_id:
            lis_id = "{}{:04d}".format(lis_id[0], int(lis_id[1:]))
            p.image = f"http://memdata.virginiageneralassembly.gov/images/display_image/{lis_id}"
        return p


class Senate(MemberList):
    chamber = "upper"
    selector = XPath('//div[@class="lColRt"]/ul/li/a')
    next_page_cls = SenatePhotoDetail


class House(MemberList):
    chamber = "lower"
    selector = XPath('//div[@class="lColLt"]/ul/li/a')
    next_page_cls = DelegateDetail
