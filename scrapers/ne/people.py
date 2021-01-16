import re
import scrapelib

from openstates.scrape import Person, Scraper

from utils import LXMLMixin


class NEPersonScraper(Scraper, LXMLMixin):
    def scrape(self):
        base_url = "http://news.legislature.ne.gov/dist"

        # there are 49 districts
        for district in range(1, 50):
            rep_url = base_url + str(district).zfill(2)

            full_name = None
            address = None
            phone = None
            email = None
            photo_url = None

            try:
                page = self.lxmlize(rep_url)

                info_node = self.get_node(
                    page,
                    '//div[@class="container view-front"]'
                    '//div[@class="col-sm-4 col-md-3 ltc-col-right"]'
                    '/div[@class="block-box"]',
                )

                full_name = self.get_node(info_node, "./h2/text()[normalize-space()]")
                full_name = re.sub(r"^Sen\.[\s]+", "", full_name).strip()
                if full_name == "Seat Vacant":
                    continue

                address_node = self.get_node(
                    info_node, './address[@class="feature-content"]'
                )

                email = self.get_node(
                    address_node, './a[starts-with(@href, "mailto:")]/text()'
                )

                contact_text_nodes = self.get_nodes(
                    address_node, "./text()[following-sibling::br]"
                )

                address_sections = []
                for text in contact_text_nodes:
                    text = text.strip()

                    if not text:
                        continue

                    phone_match = re.search(r"Phone:", text)

                    if phone_match:
                        phone = re.sub(r"^Phone:[\s]+", "", text)
                        continue

                    # If neither a phone number nor e-mail address.
                    address_sections.append(text)

                address = "\n".join(address_sections)

                photo_url = (
                    "http://www.nebraskalegislature.gov/media/images/blogs"
                    "/dist{:2d}.jpg"
                ).format(district)

                # Nebraska is offically nonpartisan.
                party = "Nonpartisan"

                person = Person(
                    name=full_name,
                    district=str(district),
                    party=party,
                    image=photo_url,
                    primary_org="legislature",
                )

                person.add_link(rep_url)
                person.add_source(rep_url)

                note = "Capitol Office"
                person.add_contact_detail(type="address", value=address, note=note)
                if phone:
                    person.add_contact_detail(type="voice", value=phone, note=note)
                if email:
                    person.add_contact_detail(type="email", value=email, note=note)

                yield person
            except scrapelib.HTTPError:
                self.warning("could not retrieve %s" % rep_url)
