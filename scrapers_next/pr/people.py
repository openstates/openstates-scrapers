from spatula import URL, CSS, HtmlListPage, HtmlPage, SelectorError, XPath
from openstates.models import ScrapePerson
import re
from dataclasses import dataclass


@dataclass
class PartialSen:
    name: str
    party: str
    source: str


# @dataclass
# class PartialRep:
#     name: str
#     district: str
#     source: str


@dataclass
class PartialRep:
    name: str
    image: str
    district: str
    email: str
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
            # every Senator except for this link are missing a district number
            # https://senado.pr.gov/Pages/Senators/HON--MIGDALIA-PADILLA-ALVELO.aspx
            district = ""
            try:
                district = (
                    CSS("div.module-distrito span.headline")
                    .match_one(self.root)
                    .text_content()
                    .strip()
                )
                district = re.sub("​DISTRITO", "", district)
                district = re.sub("\u200b", "", district)
                district = district.strip()
            except SelectorError:
                pass

        p = ScrapePerson(
            name=self.input.name,
            state="pr",
            chamber="upper",
            district=district,
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


class RepDetail(HtmlPage):
    # example_source = "https://www.camara.pr.gov/team/rafael-hernandez-montanez/"

    input_type = PartialRep

    def process_page(self):
        party_map = {
            "PNP": "Partido Nuevo Progresista",
            "PPD": "Partido Popular Democr\xe1tico",
            "PIP": "Partido Independentista Puertorrique\u00F1o",
            "PD": "Proyecto Dignidad",
            "MVC": "Movimiento Victoria Ciudadana",
        }
        party = CSS(".ova-experience span").match_one(self.root).text_content().strip()
        party = party_map[party]

        p = ScrapePerson(
            name=self.input.name,
            state="pr",
            chamber="lower",
            district=self.input.district,
            party=party,
            email=self.input.email,
            image=self.input.image,
        )

        try:
            phone = CSS(".ova-phone a").match_one(self.root).text_content().strip()
            p.capitol_office.voice = phone
        except SelectorError:
            pass

        try:
            role = CSS(".job").match_one(self.root).text_content().strip()
            p.extras["role"] = role
        except SelectorError:
            pass

        try:
            socials = CSS(".ova-social li a").match(self.root)
            for link in socials:
                social_link = link.get("href")
                split_social_link = social_link.split(".com/")[1]
                if "twitter" in social_link:
                    p.ids.twitter = split_social_link
                elif "facebook" in social_link:
                    p.ids.facebook = split_social_link
                elif "instagram" in social_link:
                    p.ids.instagram = split_social_link
        except SelectorError:
            pass

        resumen = CSS(".resumen-financiero a").match_one(self.root).get("href")
        p.add_link(resumen, note="resumen financiero")

        try:
            committees = (
                CSS(".ova-excerpt-team")
                .match_one(self.root)
                .text_content()
                .replace("\r\n", "")
                .strip()
                .split("Comisiones:-")
            )
            p.extras["committees"] = committees[1].strip()
        except IndexError:
            pass

        p.add_source(self.input.source)
        p.add_source(self.source.url)
        p.add_link(self.source.url, note="homepage")

        return p


class House(HtmlListPage):
    source = URL("https://www.camara.pr.gov/page-team/")
    selector = XPath(
        "//div[@class='items elementor-items']//div[@class='content_info']"
    )

    def process_item(self, item):
        name = (
            XPath(".//a[@class='name second_font']")
            .match_one(item)
            .text_content()
            .strip()
        )
        district = (
            CSS(".ova-info-content .ova-expertise span")
            .match_one(item)
            .text_content()
            .strip()
            .split("-")[0]
        )
        email = (
            CSS(".ova-info-content .ova-email").match_one(item).text_content().strip()
        )
        image = CSS(".ova-media a img").match_one(item).get("src")
        detail_link = CSS(".ova-media a").match_one(item).get("href")

        partial = PartialRep(
            name=name,
            image=image,
            district=district,
            email=email,
            source=self.source.url,
        )

        return RepDetail(partial, source=detail_link)
