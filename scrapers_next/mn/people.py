import collections
import re
from spatula import HtmlListPage, CsvListPage, HtmlPage, XPath
from ..common.people import Person, PeopleWorkflow

PARTIES = {"DFL": "Democratic-Farmer-Labor", "R": "Republican", "I": "Independent"}
SEN_HTML_URL = "http://www.senate.mn/members/index.php"


class SenExtraInfo(HtmlPage):
    source = SEN_HTML_URL

    def process_page(self):
        extra_info = collections.defaultdict(dict)

        xpath = '//div[@id="alphabetically"]' '//div[@class="media my-3"]'
        for div in self.root.xpath(xpath):
            main_link, email_link = filter(
                lambda link: link.get("href"), div.xpath(".//a")
            )
            name = main_link.text_content().split(" (")[0]
            leg = extra_info[name]
            leg["office_phone"] = next(
                filter(
                    lambda string: re.match(r"\d{3}-\d{3}-\d{4}", string.strip()),
                    div.xpath(".//text()"),
                )
            ).strip()
            leg["url"] = main_link.get("href")
            leg["image"] = div.xpath(".//img/@src")[0]
            if "mailto:" in email_link.get("href"):
                leg["email"] = email_link.get("href").replace("mailto:", "")

        print("collected preliminary data on {} legislators".format(len(extra_info)))
        return extra_info


class SenList(CsvListPage):
    source = "http://www.senate.mn/members/member_list_ascii.php?ls="
    dependencies = {
        "extra_info": SenExtraInfo(),
    }

    def process_item(self, row):
        if not row["First Name"]:
            return
        name = "{} {}".format(row["First Name"], row["Last Name"])
        party = PARTIES[row["Party"]]
        leg = Person(
            name=name,
            district=row["District"].lstrip("0"),
            party=party,
            state="mn",
            chamber="upper",
            image=self.extra_info[name]["image"],
        )

        if "url" in self.extra_info[name]:
            leg.add_link(self.extra_info[name]["url"])
        if "office_phone" in self.extra_info[name]:
            leg.capitol_office.voice = self.extra_info[name]["office_phone"]
        if "email" in self.extra_info[name]:
            leg.email = self.extra_info[name]["email"]

        row["Zipcode"] = row["Zipcode"].strip()
        if (
            a in row["Address2"]
            for a in ["95 University Avenue W", "100 Rev. Dr. Martin Luther King"]
        ):
            address = "{Address}\n{Address2}\n{City}, {State} {Zipcode}".format(**row)
            if "Rm. Number" in row:
                address = "{0} {1}".format(row["Rm. Number"], address)
        leg.capitol_office.address = address
        leg.add_source(self.source.url)
        leg.add_source(SEN_HTML_URL)
        return leg


class RepList(HtmlListPage):
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

        rep = Person(
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
        rep.capitol_office.phone = phone

        return rep


reps = PeopleWorkflow(RepList)
sens = PeopleWorkflow(SenList)
