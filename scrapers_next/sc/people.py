from spatula import URL, CSS, HtmlListPage, HtmlPage, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    zipcode_re = re.compile(r"Columbia,?\s\s?(\d{5})")
    zip2_re = re.compile(r"(.+),?\s(\d{5})")

    def process_page(self):
        p = self.input

        cap_addr_path = (
            XPath(
                "//*[@id='contentsection']/div[1]/div[3]/h2[contains(text(), 'Columbia Address')]"
            )
            .match_one(self.root)
            .getnext()
        )
        cap_addr = cap_addr_path.text
        cap_addr += " "
        line2 = cap_addr_path.getchildren()[0].tail
        if " SC " not in line2:
            zipcode = self.zipcode_re.search(line2).groups()[0]
            line2 = f"Columbia, SC {zipcode}"
        cap_addr += line2
        p.capitol_office.address = cap_addr

        try:
            home_addr_path = (
                XPath(
                    "//*[@id='contentsection']/div[1]/div[4]/h2[contains(text(), 'Home Address')]"
                )
                .match_one(self.root)
                .getnext()
            )
            home_addr = home_addr_path.text
            home_addr += " "
            home_line2 = home_addr_path.getchildren()[0].tail
            if " SC " not in home_line2:
                city, h_zip = self.zip2_re.search(home_line2).groups()
                home_line2 = f"{city}, SC {h_zip}"
            home_addr += home_line2
            p.district_office.address = home_addr
        except SelectorError:
            pass

        phone_dict = {
            "Columbia Address": {
                "Home Phone": None,
                "Business Phone": None,
                "Cell Phone": None,
            },
            "Home Address": {
                "Home Phone": None,
                "Business Phone": None,
                "Cell Phone": None,
            },
            "Home Information": {
                "Home Phone": None,
                "Business Phone": None,
                "Cell Phone": None,
            },
        }
        phone_spans = XPath("//*[@id='contentsection']/div[1]/div/p/span").match(
            self.root
        )[1:]
        for phone_span in phone_spans:
            parent = (
                phone_span.getparent()
                .getparent()
                .getchildren()[0]
                .text_content()
                .strip()
            )
            title = phone_span.text_content().strip()
            number = phone_span.tail.strip()
            phone_dict[parent][title] = number

        for parent, mini_phone_dict in phone_dict.items():
            if parent == "Columbia Address":
                for title, phone in mini_phone_dict.items():
                    if title == "Home Phone" and phone:
                        p.extras["Columbia Address " + title] = phone
                    elif title == "Business Phone" and phone:
                        p.capitol_office.voice = phone
                    elif title == "Cell Phone" and phone:
                        p.extras["Columbia Address " + title] = phone
            elif parent == "Home Address" or parent == "Home Information":
                for title, phone in mini_phone_dict.items():
                    if title == "Home Phone" and phone:
                        p.extras["Home Address " + title] = phone
                    elif title == "Business Phone" and phone:
                        p.district_office.voice = phone
                    elif title == "Cell Phone" and phone:
                        p.extras["Home Address " + title] = phone

        title = (
            XPath("//*[@id='contentsection']/div[1]/div[1]/p")
            .match(self.root)[1]
            .text_content()
        )
        if not re.search(r"(Republican|Democrat|Committee)", title):
            p.extras["title"] = title.strip()

        p.extras["counties represented"] = (
            XPath("//*[@id='contentsection']/div[1]/div[1]/p/span")
            .match(self.root)[0]
            .text_content()
        )

        return p


class Legislators(HtmlListPage):
    selector = CSS("div.member")
    district_re = re.compile(r"District\s(.+)")
    title_re = re.compile(r"(Senator|Representative)\s(.+)")

    def process_item(self, item):
        name = CSS("a.membername").match_one(item).text_content()
        name = self.title_re.search(name).groups()[1]

        party = CSS("a.membername").match_one(item).tail.strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"

        district = CSS("div.district a").match_one(item).text_content().strip()
        district = self.district_re.search(district).groups()[0]

        p = ScrapePerson(
            name=name,
            state="sc",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("div.district a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        img = CSS("img").match_one(item).get("src")
        p.image = img

        return LegDetail(p, source=URL(detail_link, timeout=60))


class Senate(Legislators):
    source = URL("https://www.scstatehouse.gov/member.php?chamber=S", timeout=30)
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.scstatehouse.gov/member.php?chamber=H", timeout=30)
    chamber = "lower"
