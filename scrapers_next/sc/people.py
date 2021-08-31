from spatula import URL, CSS, HtmlListPage, HtmlPage, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
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
        if not re.search(r"SC", line2):
            zipcode = re.search(r"Columbia,?\s\s?(\d{5})", line2).groups()[0]
            line2 = "Columbia, SC " + zipcode
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
            if not re.search(r"SC", home_line2):
                city, h_zip = re.search(r"(.+),?\s(\d{5})", home_line2).groups()
                home_line2 = city + ", SC " + h_zip
            home_addr += home_line2
            p.district_office.address = home_addr
        except SelectorError:
            pass

        cap_phones = XPath(
            "//*[@id='contentsection']/div[1]/div[3]/p/span[contains(text(), 'Phone')]"
        ).match(self.root)
        if len(cap_phones) > 1:
            p.extras[cap_phones[1].text_content().strip()] = cap_phones[1].tail.strip()
        if cap_phones[0].text_content().strip() == "Business Phone":
            p.capitol_office.voice = cap_phones[0].tail.strip()
        else:
            p.extras[cap_phones[0].text_content().strip()] = cap_phones[0].tail.strip()

        try:
            home_phones = XPath(
                "//*[@id='contentsection']/div[1]/div[4]/p/span[contains(text(), 'Phone')]"
            ).match(self.root)
            if len(home_phones) > 1 and len(cap_phones) > 1:
                if home_phones[0].tail.strip() not in [
                    cap_phones[0].tail.strip(),
                    cap_phones[1].tail.strip(),
                ]:
                    p.extras[home_phones[0].text_content().strip()] = home_phones[
                        0
                    ].tail.strip()
                if home_phones[1].tail.strip() not in [
                    cap_phones[0].tail.strip(),
                    cap_phones[1].tail.strip(),
                ]:
                    p.district_office.voice = home_phones[1].tail.strip()
            elif len(home_phones) > 1:
                if home_phones[0].tail.strip() != cap_phones[0].tail.strip():
                    p.extras[home_phones[0].text_content().strip()] = home_phones[
                        0
                    ].tail.strip()
                if home_phones[1].tail.strip() != cap_phones[0].tail.strip():
                    p.district_office.voice = home_phones[1].tail.strip()
            elif home_phones[0].text_content().strip() == "Business Phone":
                p.district_office.voice = home_phones[0].tail.strip()
            else:
                p.extras[home_phones[0].text_content().strip()] = home_phones[
                    0
                ].tail.strip()
        except SelectorError:
            pass

        title = (
            XPath("//*[@id='contentsection']/div[1]/div[1]/p")
            .match(self.root)[1]
            .text_content()
        )
        if not re.search(r"(Republican|Democrat|Committee)", title):
            print(title)
            p.extras["title"] = title.strip()

        return p


class Legislators(HtmlListPage):
    selector = CSS("div.member")

    def process_item(self, item):
        name = CSS("a.membername").match_one(item).text_content()
        name = re.search(r"(Senator|Representative)\s(.+)", name).groups()[1]

        party = CSS("a.membername").match_one(item).tail.strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"

        district = CSS("div.district a").match_one(item).text_content().strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

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

        return LegDetail(p, source=detail_link)


class Senate(Legislators):
    source = URL("https://www.scstatehouse.gov/member.php?chamber=S")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.scstatehouse.gov/member.php?chamber=H")
    chamber = "lower"
