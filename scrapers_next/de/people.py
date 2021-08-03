from spatula import JsonPage, URL, HtmlPage, CSS
from openstates.models import ScrapePerson


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("img").match_one(self.root).get("src")
        p.image = img

        addr = CSS("div .info-vertical div div").match(self.root)[0].text_content()
        addr += " "
        addr += (
            CSS("div .info-vertical div div").match(self.root)[1].text_content().strip()
        )
        print(addr)
        p.capitol_office.address = addr

        p.capitol_office.voice = (
            CSS("div .info-vertical div div").match(self.root)[2].text_content()
        )

        p.email = CSS("div .info-vertical div div").match(self.root)[3].text_content()

        return p


class LegList(JsonPage):
    def process_page(self):
        for item in self.data["Data"]:
            name = item["PersonFullName"]
            party_code = item["PartyCode"]
            party_dict = {"D": "Democratic", "R": "Republican", "I": "Independent"}
            party = party_dict[party_code]
            district = item["DistrictNumber"]

            p = ScrapePerson(
                name=name,
                state="de",
                party=party,
                chamber=self.chamber,
                district=district,
            )

            p.add_source(self.source.url)
            detail_link = URL(
                f"https://legis.delaware.gov/LegislatorDetail?personId={item['PersonId']}"
            )
            p.add_source(detail_link.url)

            yield LegDetail(p, source=detail_link.url)


class Senate(LegList):
    source = URL("https://legis.delaware.gov/json/Senate/GetSenators", method="POST")
    chamber = "upper"


class House(LegList):
    source = URL(
        "https://legis.delaware.gov/json/House/GetRepresentatives", method="POST"
    )
    chamber = "lower"
