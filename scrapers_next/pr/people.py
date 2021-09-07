from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError
from openstates.models import ScrapePerson
import re
from dataclasses import dataclass


@dataclass
class PartialSen:
    name: str
    party: str
    source: str


class SenDetail(HtmlPage):
    input_type = PartialSen

    def process_page(self):
        district = (
            CSS(
                "span#DeltaPlaceHolderMain section div.row.profile-container div ul li a"
            )
            .match(self.root)[1]
            .text_content()
            .strip()
        )
        if district == "Senador por Acumulación":
            district = "At-Large"
        elif district == "Senadora por Distrito":
            # most are missing a district number
            try:
                district = (
                    CSS("div.module-distrito")
                    .match(self.root)[0]
                    .text_content()
                    .strip()
                )
                # print(district)
            except SelectorError:
                pass

        p = ScrapePerson(
            name=self.input.name,
            state="pr",
            chamber="upper",
            district="",
            party=self.input.party,
        )

        p.add_source(self.input.source)
        p.add_source(self.source.url)
        p.add_link(self.source.url, note="homepage")

        try:
            img = CSS("div.avatar img").match_one(self.root).get("src")
            p.image = img
        except SelectorError:
            pass

        email = (
            CSS("a.contact-data.email")
            .match_one(self.root)
            .text_content()
            .replace("\u200b", "")
            .strip()
        )
        p.email = email

        title = CSS("span.position").match_one(self.root).text_content().strip()
        if title != "":
            p.extras["title"] = title

        # all have same phone number
        phone = CSS("a.contact-data.tel").match_one(self.root).text_content().strip()
        p.capitol_office.voice = phone

        addresses = CSS("div.pre-footer div div div div p").match(self.root)
        cap_addr = CSS("br").match(addresses[0])
        capitol_address = ""
        for line in cap_addr:
            if line.tail.strip() != "":
                capitol_address += line.tail.strip()
                capitol_address += " "
        p.capitol_office.address = capitol_address.strip()

        mail_addr = CSS("br").match(addresses[1])
        mailing_address = ""
        for line in mail_addr:
            if line.tail.strip() != "":
                mailing_address += line.tail.strip()
                mailing_address += " "
        p.extras["Mailing address"] = mailing_address.strip()

        return p


class Senate(HtmlListPage):
    source = URL("https://senado.pr.gov/Pages/Senadores.aspx")
    selector = CSS("ul.senadores-list li", num_items=27)

    def process_item(self, item):
        # Convert names to title case as they are in all-caps
        name = CSS("span.name").match_one(item).text_content().strip()
        name = re.sub(r"^Hon\.", "", name, flags=re.IGNORECASE).strip().title()

        party = CSS("span.partido").match_one(item).text_content().strip()
        # Translate to English since being an Independent is a universal construct
        if party == "Independiente":
            party = "Independent"

        detail_link = CSS("a").match_one(item).get("href")

        partial = PartialSen(name=name, party=party, source=self.source.url)

        return SenDetail(partial, source=detail_link)


# class House(HtmlListPage):
#     source = URL("http://www.tucamarapr.org/dnncamara/ComposiciondelaCamara/Biografia.aspx")
#     selector = CSS("ul.list-article li")

#     def process_item(self, item):

# p = ScrapePerson(
#     name=name,
#     state="pr",
#     chamber="lower",
#     district=district,
#     party=party,
# )

# return p
