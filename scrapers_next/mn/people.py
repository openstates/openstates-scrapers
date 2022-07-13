import re
from spatula import HtmlListPage, JsonPage, XPath, URL
from openstates.models import ScrapePerson

PARTIES = {"DFL": "Democratic-Farmer-Labor", "R": "Republican", "I": "Independent"}
SEN_HTML_URL = "http://www.senate.mn/members/index.php"


class Senators(JsonPage):
    source = URL("https://www.senate.mn/api/members", verify=False)

    def process_page(self):
        for row in self.data["members"]:
            yield self.process_item(row)

    def process_item(self, row):
        name = row["preferred_full_name"]
        party = PARTIES[row["party"]]
        leg = ScrapePerson(
            name=name,
            family_name=row["preferred_last_name"],
            email=row["email"],
            district=row["dist"].lstrip("0"),
            party=party,
            state="mn",
            chamber="upper",
            image="https://www.senate.mn/img/member_thumbnails/" + row["mem_bio_pic"],
        )
        leg.capitol_office.voice = row["full_phone_number"]
        leg.capitol_office.address = "; ".join(
            (row["office_address_first_line"], row["office_address_second_line"])
        )

        leg.add_link(
            f"https://www.senate.mn/members/member_bio.html?mem_id={row['mem_id']}"
        )
        leg.add_source(self.source.url)
        return leg


class Representatives(HtmlListPage):
    source = "http://www.house.leg.state.mn.us/members/hmem.asp"
    selector = XPath('//div[@id="Alpha"]//div[@class="media my-3"]')

    def process_item(self, item):
        photo_url = item.xpath("./img/@src")[0]
        url = item.xpath(".//h5/a/@href")[0]
        name_text = item.xpath(".//h5/a/b/text()")[0]

        name_match = re.match(r"^(.+)\(([0-9]{2}[AB]), ([A-Z]+)\)$", name_text)
        name = name_match.group(1).strip()
        district = name_match.group(2).lstrip("0").upper()
        party_text = name_match.group(3)
        party = PARTIES[party_text]

        info_texts = [
            x.strip()
            for x in item.xpath("./div/text()[normalize-space()]")
            if x.strip()
        ]
        address = "\n".join((info_texts[0], info_texts[1]))

        phone_text = info_texts[2]
        # if validate_phone_number(phone_text):
        phone = phone_text

        email_text = item.xpath(".//a/@href")[1].replace("mailto:", "").strip()
        # if validate_email_address(email_text):
        email = email_text

        rep = ScrapePerson(
            name=name,
            district=district,
            party=party,
            state="mn",
            chamber="lower",
            image=photo_url,
            email=email,
        )
        rep.add_link(url)
        rep.add_source(self.source.url)
        rep.capitol_office.address = address
        rep.capitol_office.voice = phone

        return rep
