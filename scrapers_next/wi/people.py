from spatula import URL, CSS, HtmlListPage, SelectorError, XPath, HtmlPage
from openstates.models import ScrapePerson
import re
from itertools import zip_longest


# source https://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        capitol_addr_lst = XPath(".//*[@id='district']/span[1]/text()").match(self.root)
        capitol_addr = ""
        for line in capitol_addr_lst:
            capitol_addr += line.strip()
            capitol_addr += " "
        p.capitol_office.address = capitol_addr.strip()

        try:
            fax = (
                CSS("span.info.fax")
                .match_one(self.root)
                .text_content()
                .strip()
                .split("\n")
            )
            fax = fax[-1].strip()
            p.capitol_office.fax = fax
        except SelectorError:
            pass

        try:
            staff_spans = CSS("span.info.staff span").match(self.root)
            for num, span in enumerate(grouper(staff_spans[1:], 2)):
                staff_name = span[0].text_content().strip()
                staff_email = span[1].text_content().strip()
                p.extras["staff" + str(num + 1)] = staff_name
                p.extras["staff_email" + str(num + 1)] = staff_email
        except SelectorError:
            pass

        return p


class Legislators(HtmlListPage):
    selector = CSS("div.box-content div")
    party_re = re.compile(r"\(([A-Z])\s-\s.+\)")

    def process_item(self, item):
        # skip header rows
        if item.get("class") not in ["rounded odd", "rounded even"]:
            self.skip("header row")

        name_dirty = (
            CSS("span.info strong").match(item)[0].text_content().strip().split(", ")
        )
        if len(name_dirty) > 1:
            name = f"{name_dirty[1]} {name_dirty[0]}"
        elif len(name_dirty) == 1:
            name = name_dirty[0]
        else:
            self.skip("empty name")
        if name == "Vacant":
            self.skip("vacant")

        party = CSS("span.info small").match(item)[0].text_content().strip()
        party = self.party_re.search(party).groups()[0]
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

        return LegDetail(p, source=detail_link)


class Senate(Legislators):
    source = URL("https://docs.legis.wisconsin.gov/2021/legislators/senate/")
    chamber = "upper"


class House(Legislators):
    source = URL("https://docs.legis.wisconsin.gov/2021/legislators/assembly/")
    chamber = "lower"
