# -*- coding: utf-8 -*-
import re
from pupa.scrape import Person, Scraper
from openstates.utils import LXMLMixin, validate_phone_number


class PRPersonScraper(Scraper, LXMLMixin):
    def scrape(self, chamber=None):
        term = self.jurisdiction.legislative_sessions[-1]["identifier"]
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from getattr(self, "scrape_" + chamber + "_chamber")(term)

    def scrape_upper_chamber(self, term):
        url = "https://senado.pr.gov/Pages/Senadores.aspx"

        doc = self.lxmlize(url)
        links = self.get_nodes(doc, '//ul[@class="senadores-list"]/li/a/@href')

        for link in links:
            senator_page = self.lxmlize(link)
            profile_links = self.get_nodes(
                senator_page, '//ul[@class="profiles-links"]/li'
            )

            name_text = (
                self.get_node(senator_page, '//span[@class="name"]')
                .text_content()
                .strip()
            )
            # Convert to title case as some names are in all-caps
            name = re.sub(r"^Hon\.", "", name_text, flags=re.IGNORECASE).strip().title()
            party = profile_links[0].text_content().strip()
            # Translate to English since being an Independent is a universal construct
            if party == "Independiente":
                party = "Independent"

            photo_url = self.get_node(senator_page, '//div[@class="avatar"]//img/@src')

            if profile_links[1].text_content().strip() == "Senador por Distrito":
                district_text = self.get_node(
                    senator_page,
                    '//div[@class="module-distrito"]//span[@class="headline"]',
                ).text_content()
                district = (
                    district_text.replace("DISTRITO", "", 1)
                    .replace("\u200b", "")
                    .strip()
                )
            elif profile_links[1].text_content().strip() == "Senador por Acumulación":
                district = "At-Large"

            phone_node = self.get_node(senator_page, '//a[@class="contact-data tel"]')
            phone = phone_node.text_content().strip()
            email_node = self.get_node(senator_page, '//a[@class="contact-data email"]')
            email = email_node.text_content().replace("\u200b", "").strip()

            person = Person(
                primary_org="upper",
                district=district,
                name=name,
                party=party,
                image=photo_url,
            )
            person.add_contact_detail(type="email", value=email, note="Capitol Office")
            person.add_contact_detail(type="voice", value=phone, note="Capitol Office")
            person.add_link(link)
            person.add_source(link)

            yield person

    def scrape_lower_chamber(self, term):
        # E-mail contact is now hidden behind webforms. Sadness.

        party_map = {
            "PNP": "Partido Nuevo Progresista",
            "PPD": u"Partido Popular Democr\xe1tico",
            "PIP": u"Partido Independentista Puertorrique\u00F1o",
        }

        url = "http://www.tucamarapr.org/dnncamara/ComposiciondelaCamara/Biografia.aspx"
        page = self.lxmlize(url)

        member_nodes = self.get_nodes(page, '//li[@class="selectionRep"]')
        for member_node in member_nodes:
            member_info = member_node.text_content().strip().split("\n")

            name = re.sub(r"^Hon\.", "", member_info[0]).strip()
            district_text = member_info[-1].strip()
            if district_text == "Representante por Acumulación":
                district = "At-Large"
            else:
                district = district_text.replace(
                    "Representante del Distrito ", ""
                ).strip()
            photo_url = self.get_node(member_node, ".//img/@src")

            rep_link = self.get_node(member_node, ".//a/@href")
            rep_page = self.lxmlize(rep_link)

            party_node = self.get_node(rep_page, '//span[@class="partyBio"]')
            # Albelo doesn't seem to have a "partyBio" as an independent, but we
            # expect this to exist for all other members.
            if not party_node and name == "Manuel A. Natal Albelo":
                party = "Independent"
            else:
                party_text = party_node.text_content().strip()
                party = party_map[party_text]

            address = (
                self.get_node(rep_page, "//h6").text.strip().split("\n")[0].strip()
            )

            # Only grabs the first validated phone number found.
            # Typically, representatives have multiple phone numbers.
            phone_node = self.get_node(
                rep_page, '//span[@class="data-type" and contains(text(), "Tel.")]'
            )
            phone = None
            possible_phones = phone_node.text.strip().split("\n")
            for phone_attempt in possible_phones:
                # Don't keep searching phone numbers if a good one is found.
                if phone:
                    break

                phone_text = re.sub(r"^Tel\.[\s]*", "", phone_attempt).strip()
                if validate_phone_number(phone_text):
                    phone = phone_text

            fax_node = self.get_node(
                rep_page, '//span[@class="data-type" and contains(text(), "Fax.")]'
            )
            fax = None
            if fax_node:
                fax_text = fax_node.text.strip()
                fax_text = re.sub(r"^Fax\.[\s]*", "", fax_text).strip()
                if validate_phone_number(fax_text):
                    fax = fax_text

            person = Person(
                primary_org="lower",
                district=district,
                name=name,
                party=party,
                image=photo_url,
            )

            person.add_link(rep_link)
            person.add_source(rep_link)
            person.add_source(url)

            if address:
                person.add_contact_detail(
                    type="address", value=address, note="Capitol Office"
                )
            if phone:
                person.add_contact_detail(
                    type="voice", value=phone, note="Capitol Office"
                )
            if fax:
                person.add_contact_detail(type="fax", value=fax, note="Capitol Office")

            yield person
