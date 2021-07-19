from spatula import (
    HtmlListPage,
    XPath,
    CSS,
    URL,
    HtmlPage,
)
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        titles = CSS("h2").match(self.root)
        if len(titles) > 9:
            title = titles[0].text_content()
            print(title)
            p.extras["title"] = title

        assistant = (
            CSS("div .fusion-text.fusion-text-2 p").match(self.root)[0].text_content()
        )
        assistant = re.search(r"Legislative Assistant:\s(.+)", assistant).groups()[0]

        phones = (
            CSS("div .fusion-text.fusion-text-2 p").match(self.root)[1].text_content()
        )
        phone1, phone2 = re.search(
            r"Phone:\s(\d{3}-\d{3}-\d{4})\s\|\s(.+)", phones
        ).groups()

        email = (
            CSS("div .fusion-text.fusion-text-2 p a").match(self.root)[0].text_content()
        )

        media_contact = (
            CSS("div .fusion-text.fusion-text-2 p").match(self.root)[3].text_content()
        )
        media_contact_name, media_contact_email = re.search(
            r"Media Contact:\s(\w+\s\w+)\s\|\s(.+)", media_contact
        ).groups()
        addr = (
            XPath("//div/div[3]/div/div[2]/div/div[1]/text()")
            .match(self.root)[0]
            .strip()
        )

        twitter = CSS("div .fusion-social-links a").match(self.root)[0].get("href")
        fb = CSS("div .fusion-social-links a").match(self.root)[1].get("href")

        # print(phone1)
        # print(phone2)
        # print(addr)
        p.district_office.voice = phone1
        p.capitol_office.address = addr
        p.capitol_office.voice = phone2

        p.email = email

        p.extras["assistant"] = assistant
        p.extras["media contact name"] = media_contact_name
        p.extras["media contact email"] = media_contact_email
        p.extras["twitter"] = twitter
        p.extras["facebook"] = fb

        return p


class LegList(HtmlListPage):
    def process_item(self, item):
        name = CSS("div a").match(item)[1].text_content()
        # print(name)
        district = (
            CSS("div .esg-content.eg-senators-grid-element-1")
            .match_one(item)
            .text_content()
            .split("|")[1]
            .strip()
            .lower()
        )
        district = re.search(r"district\s(\d+)", district).groups()[0]
        # print(district)
        img = CSS("div img").match_one(item).get("data-lazysrc")
        # print(img)

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district=district,
            party=self.party,
            image=img,
        )

        detail_link = CSS("div a").match(item)[1].get("href")
        p.add_link(detail_link, note="homepage")
        p.add_source(self.source.url)
        p.add_source(detail_link)
        return LegDetail(p, source=detail_link)


class RedRepList(LegList):
    source = "https://www.indianahouserepublicans.com/members/"
    # selector = CSS("", num_items=)
    chamber = "lower"
    party = "Republican"


class BlueRepList(LegList):
    source = URL("https://indianahousedemocrats.org/members")
    # selector = CSS("", num_items=)
    chamber = "lower"
    party = "Democratic"


class BlueSenList(LegList):
    source = "https://www.indianasenatedemocrats.org/senators/"
    # selector = XPath(".//*[@id='esg-grid-10-1']/div/ul/li")
    # selector = CSS("ul .mainul li")
    selector = CSS(
        "body main section div div div.fusion-fullwidth.fullwidth-box.fusion-builder-row-2.nonhundred-percent-fullwidth.non-hundred-percent-height-scrolling article ul li",
        num_items=11,
    )
    chamber = "upper"
    party = "Democratic"


class RedSenList(LegList):
    source = "https://www.indianasenaterepublicans.com/senators"
    selector = CSS("div.senator-list div.senator-item", num_items=39)
    chamber = "upper"
    party = "Republican"
