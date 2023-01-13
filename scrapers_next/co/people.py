from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError
from openstates.models import ScrapePerson


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        name = CSS("main header h1").match_one(self.root).text_content()
        p.name = name

        img = CSS("main img").match_one(self.root).get("src")
        p.image = img

        capitol_addr1 = CSS("div .thoroughfare").match_one(self.root).text_content()

        try:
            capitol_addr2 = CSS("div .premise").match_one(self.root).text_content()
        except SelectorError:
            capitol_addr2 = None

        capitol_addr3 = (
            CSS("div .addressfield-container-inline.locality-block.country-US")
            .match_one(self.root)
            .text_content()
        )

        if capitol_addr2:
            capitol_addr = f"{capitol_addr1} {capitol_addr2} {capitol_addr3}"
        else:
            capitol_addr = f"{capitol_addr1} {capitol_addr3}"
        p.capitol_office.address = capitol_addr
        # most of them have the same capitol_addr. just a mailing address?

        if len(CSS("div .legislator-content > div").match(self.root)) > 2:
            title = (
                CSS("div .legislator-content > div .field-items div")
                .match(self.root)[2]
                .text_content()
            )
            p.extras["title"] = title

        counties = CSS("div .counties div .field-items div").match(self.root)
        counties_rep = []
        for county in counties:
            counties_rep.append(county.text_content())
        p.extras["counties represented"] = counties_rep

        return p


class LegList(HtmlListPage):
    source = "http://leg.colorado.gov/legislators"
    selector = CSS("tbody tr", min_items=100)

    def process_item(self, item):
        title = CSS("td").match(item)[0].text_content().strip()
        if title == "Representative":
            chamber = "lower"
        elif title == "Senator":
            chamber = "upper"

        district = CSS("td").match(item)[2].text_content()

        party = CSS("td").match(item)[3].text_content()
        if party == "Democrat":
            party = "Democratic"

        p = ScrapePerson(
            name="",
            state="co",
            party=party,
            chamber=chamber,
            district=district,
        )

        p.capitol_office.voice = CSS("td").match(item)[4].text_content().strip()
        p.email = CSS("td").match(item)[5].text_content().strip()

        detail_link = CSS("td a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return LegDetail(p, source=URL(detail_link, timeout=30))
