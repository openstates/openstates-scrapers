from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError
from openstates.models import ScrapePerson
import re
from dataclasses import dataclass


@dataclass
class PartialSen:
    name: str
    party: str
    source: str


@dataclass
class PartialRep:
    name: str
    district: str
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
        # hard code?
        phone = CSS("a.contact-data.tel").match_one(self.root).text_content().strip()
        p.capitol_office.voice = phone

        # all have same capitol and mailing addresses
        # hard code?
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


class RepDetail(HtmlPage):
    input_type = PartialRep

    def process_page(self):
        party_map = {
            "PNP": "Partido Nuevo Progresista",
            "PPD": u"Partido Popular Democr\xe1tico",
            "PIP": u"Partido Independentista Puertorrique\u00F1o",
        }

        try:
            party = CSS("span.partyBio").match_one(self.root).text_content().strip()
            party = party_map[party]
        except SelectorError:
            # HON. LISIE J. BURGOS MUÑIZ, HON. JOSÉ B. MÁRQUEZ REYES, HON. MARIANA NOGALES MOLINELLI
            # do not have their parties listed
            party = "Independent"

        p = ScrapePerson(
            name=self.input.name,
            state="pr",
            chamber="lower",
            district=self.input.district,
            party=party,
        )

        p.add_source(self.input.source)
        p.add_source(self.source.url)
        p.add_link(self.source.url, note="homepage")

        img = CSS("div.container-biography img").match(self.root)[0].get("src")
        p.image = img

        title = CSS("span.name br").match_one(self.root).tail.strip()
        if title != "":
            p.extras["title"] = title

        phones = (
            CSS("h6 span span span")
            .match(self.root)[0]
            .text_content()
            .strip()
            .split("\n")
        )
        phone1 = re.search(r"Tel\.\s(.+)", phones[0]).groups()[0]
        phone2 = re.search(r"Tel\.\s?(.+)?", phones[1]).groups()[0]
        # http://www.tucamarapr.org/dnncamara/ComposiciondelaCamara/biografia.aspx?rep=251 has an incomplete phone
        if phone1.strip() != "" and phone1.strip() != "(787":
            p.extras["phone1"] = phone1.strip()
        if phone2 and phone2.strip() != "":
            p.extras["phone2"] = phone2.strip()

        fax = (
            CSS("h6 span span span")
            .match(self.root)[1]
            .text_content()
            .strip()
            .split("\n")
        )
        fax1 = re.search(r"Fax\.\s(.+)", fax[0]).groups()[0]
        if fax1.strip() != "":
            p.extras["fax"] = fax1
            print(fax1)
        tty = re.search(r"TTY\.\s?(.+)?", fax[1]).groups()[0]
        if tty and tty.strip() != "":
            p.extras["TTY"] = tty
            print(tty)
            # what is tty?

        return p


class House(HtmlListPage):
    source = URL(
        "http://www.tucamarapr.org/dnncamara/ComposiciondelaCamara/Biografia.aspx"
    )
    selector = CSS("ul.list-article li")

    def process_item(self, item):
        bio_info = (
            CSS("div.biodiv a").match_one(item).text_content().strip().split("\n")
        )
        name = bio_info[0].strip()
        name = re.sub(r"^Hon\.", "", name, flags=re.IGNORECASE).strip()

        district = bio_info[2].strip()
        if district == "Representante por Acumulación":
            district = "At-Large"
        else:
            district = re.search(
                r"Representante\sdel\sDistrito\s(.+)", district
            ).groups()[0]

        partial = PartialRep(name=name, district=district, source=self.source.url)

        detail_link = CSS("a").match_one(item).get("href")

        return RepDetail(partial, source=detail_link)
