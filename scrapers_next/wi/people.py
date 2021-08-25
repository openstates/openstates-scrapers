from spatula import URL, CSS, HtmlListPage, SelectorError, XPath
from openstates.models import ScrapePerson
import re


class Legislators(HtmlListPage):
    selector = CSS("div.box-content div")

    def process_item(self, item):
        if item.get("class") not in ["rounded odd", "rounded even"]:
            self.skip()

        name_dirty = (
            CSS("span.info strong").match(item)[0].text_content().strip().split(", ")
        )
        name = name_dirty[1] + " " + name_dirty[0]

        party = CSS("span.info small").match(item)[0].text_content().strip()
        party = re.search(r"\(([A-Z])\s-\s.+\)", party).groups()[0]
        if party == "D":
            party = "Democratic"
        elif party == "R":
            party = "Republican"
        elif party == "I":
            party = "Independent"

        district = CSS("span small").match(item)[1].text_content().strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        p = ScrapePerson(
            name=name,
            state="wi",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        # which one should be 'homepage'?
        # https://legis.wisconsin.gov/senate/16/agard, website currently adding to extras
        # https://docs.legis.wisconsin.gov/2021/legislators/senate/2251, detail_link adding as source and scraping
        # some are the same url and some are not

        website = CSS("span.info strong a").match_one(item).get("href")
        p.extras["website"] = website

        detail_link = (
            XPath(".//span[1]/span[3]/a[contains(text(), 'Details')]")
            .match_one(item)
            .get("href")
        )

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        try:
            title = (
                CSS("span.info span span strong").match_one(item).text_content().strip()
            )
            p.extras["title"] = title
        except SelectorError:
            pass

        email = CSS("span.info.email a").match_one(item).text_content().strip()
        p.email = email
        img = CSS("img").match_one(item).get("src")
        p.image = img

        phones = (
            CSS("span.info.telephone")
            .match_one(item)
            .text_content()
            .strip()
            .split("\n")
        )
        phones = re.search(
            r"(\(\d{3}\)\s\d{3}-\d{4})(\(?\d{0,3}\)?\s?\d{0,3}-?\d{0,4})", phones[1]
        ).groups()
        p.capitol_office.voice = phones[0]
        if len(phones) > 1:
            p.extras["extra phone"] = phones[1]

        try:
            district_phone = (
                CSS("span.info.district_phone")
                .match_one(item)
                .text_content()
                .split("\n")[2]
                .strip()
            )
            p.district_office.voice = district_phone
        except SelectorError:
            pass

        return p


class Senate(Legislators):
    source = URL("https://docs.legis.wisconsin.gov/2021/legislators/senate/")
    chamber = "upper"


class House(Legislators):
    source = URL("https://docs.legis.wisconsin.gov/2021/legislators/assembly/")
    chamber = "lower"
