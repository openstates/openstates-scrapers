import re
import lxml
from openstates.scrape import Person, Scraper
from utils import LXMLMixin, validate_email_address
from .utils import LXMLMixinOK


class OKPersonScraper(Scraper, LXMLMixin, LXMLMixinOK):

    _parties = {"R": "Republican", "D": "Democratic", "I": "Independent"}

    def _scrub(self, text):
        """Squish whitespace and kill \xa0."""
        return re.sub(r"[\s\xa0]+", " ", text)

    def _clean_office_info(self, office_info):
        office_info = list(map(self._scrub, office_info.itertext()))
        # Throw away anything after any email address, phone number, or
        # address lines.
        while office_info:
            last = office_info[-1]
            if (
                "@" not in last
                and ", OK" not in last
                and not re.search(r"[\d\-\(\) ]{7,}", last)
            ):
                office_info.pop()
            else:
                break
        return office_info

    def _extract_phone(self, office_info):
        phone = None

        for line in office_info:
            phone_match = re.search(
                r"""(\(\d{3}\) \d{3}-\d{4}|
                \d{3}.\d{3}.\d{4})""",
                line,
            )
            if phone_match is not None:
                phone = phone_match.group(1).strip()

        return phone

    def _get_rep_email(self, district):
        # Get the email address from an input on the contact page
        url = "https://www.okhouse.gov/Members/Contact.aspx?District=" + district
        page = self.curl_lxmlize(url)

        try:
            email_node = page.get_element_by_id("txtMemberEmail")
            email = email_node.value
        except KeyError:
            email = None

        if email and not validate_email_address(email):
            email = None

        return email

    def scrape(self, chamber=None):
        term = self.jurisdiction.legislative_sessions[-1]["identifier"]
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from getattr(self, "scrape_" + chamber + "_chamber")(term)

    def scrape_lower_chamber(self, term):
        url = "https://www.okhouse.gov/Members/Default.aspx"
        page = self.curl_lxmlize(url)

        legislator_nodes = self.get_nodes(
            page, '//table[@id="ctl00_ContentPlaceHolder1_RadGrid1_ctl00"]/tbody/tr'
        )

        for legislator_node in legislator_nodes:
            name_node = self.get_node(legislator_node, ".//td[1]/a")

            if name_node is not None:
                name_text = name_node.text.strip()

                # Handle seats with no current representative
                if re.search(r"District \d+", name_text):
                    continue

                last_name, delimiter, first_name = name_text.partition(",")

                if last_name is not None and first_name is not None:
                    first_name = first_name.strip()
                    last_name = last_name.strip()
                    name = " ".join([first_name, last_name])
                else:
                    raise ValueError("Unable to parse name: {}".format(name_text))

                if name.startswith("House District"):
                    continue

            district_node = self.get_node(legislator_node, ".//td[3]")

            if district_node is not None:
                district = district_node.text.strip()

            party_node = self.get_node(legislator_node, ".//td[4]")

            if party_node is not None:
                party_text = party_node.text.strip()

            party = self._parties[party_text]

            legislator_url = (
                "https://www.okhouse.gov/Members/District.aspx?District=" + district
            )
            legislator_page = self.curl_lxmlize(legislator_url)

            photo_url = self.get_node(
                legislator_page, '//a[@id="ctl00_ContentPlaceHolder1_imgHiRes"]/@href'
            )

            person = Person(
                primary_org="lower",
                district=district,
                name=name,
                party=party,
                image=photo_url,
            )
            person.extras["_scraped_name"] = name_text
            person.add_link(legislator_url)
            person.add_source(url)
            person.add_source(legislator_url)

            # Scrape offices.
            self.scrape_lower_offices(legislator_page, person, district)

            yield person

    def scrape_lower_offices(self, doc, person, district):
        email = self._get_rep_email(district)
        if email:
            person.add_contact_detail(type="email", value=email, note="Capitol Office")
            person.extras["email"] = email

        # Capitol offices:
        xpath = '//*[contains(text(), "Capitol Address")]'
        for bold in doc.xpath(xpath):

            # Get the address.
            address_div = next(bold.getparent().itersiblings())

            # Get the room number.
            xpath = '//*[contains(@id, "CapitolRoom")]/text()'
            room = address_div.xpath(xpath)
            if room:
                parts = map(self._scrub, list(address_div.itertext()))
                parts = [x.strip() for x in parts if x.strip()]
                phone = parts.pop()
                parts = [parts[0], "Room " + room[0], parts[-1]]
                address = "\n".join(parts)
            else:
                address = None
                phone = None

            if not phone:
                phone = None

            if phone:
                person.add_contact_detail(
                    type="voice", value=str(phone), note="Capitol Office"
                )
            if address:
                person.add_contact_detail(
                    type="address", value=address, note="Capitol Office"
                )

        # District offices only have address, no other information
        district_address = doc.xpath(
            '//span[@id="ctl00_Content' 'PlaceHolder1_lblDistrictAddress"]/text()'
        )
        if district_address:
            (district_city_state,) = doc.xpath(
                '//span[@id="ctl00_Content' 'PlaceHolder1_lblDistrictCity"]/text()'
            )
            district_address = "{}\n{}".format(district_address[0], district_city_state)
            if district_address:
                person.add_contact_detail(
                    type="address", value=district_address, note="District Office"
                )

    def scrape_upper_chamber(self, term):
        url = "http://oksenate.gov/Senators/Default.aspx"
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for a in doc.xpath("//table[@summary]")[0].xpath(
            './/td//a[contains(@href, "biographies")]'
        ):
            tail = a.xpath("..")[0].tail
            if tail:
                district = tail.split()[1]
            else:
                district = a.xpath("../../span")[1].text.split()[1]

            if a.text is None or a.text.strip() == "Vacant":
                self.warning("District {} appears to be empty".format(district))
                continue
            else:
                match = re.match(r"(.+) \(([A-Z])\)", a.text.strip())
                if match:
                    name, party = match.group(1), self._parties[match.group(2)]
                else:
                    self.warning(
                        "District {} appears to have empty Representative name,party".format(
                            district
                        )
                    )
                    continue

            url = a.get("href")

            person = Person(
                primary_org="upper", district=district, name=name.strip(), party=party
            )
            person.add_link(url)
            person.add_source(url)
            self.scrape_upper_offices(person, url)
            yield person

    def scrape_upper_offices(self, person, url):
        url = url.replace("aspx", "html")
        html = self.get(url).text
        person.add_source(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        try:
            xpath = '//h3[contains(., "Office")]'
            for table in doc.xpath(xpath)[0].itersiblings():
                if table.tag == "table":
                    break
        except IndexError:
            self.warning("invalid bio page for %s", person)
            return

        col2 = None
        try:
            col1, col2 = table.xpath("tr[2]/td")
        except ValueError:
            (col1,) = table.xpath("tr[2]/td")

        lxml.etree.strip_tags(col1, "sup")
        capitol_office_info = self._clean_office_info(col1)

        # Set email on the leg object.
        if capitol_office_info:
            if "@" in capitol_office_info[-1]:
                email = capitol_office_info.pop()
                person.extras["email"] = email
            else:
                email = None

            capitol_phone = self._extract_phone(capitol_office_info)

            capitol_address_lines = map(
                lambda line: line.strip(),
                filter(
                    lambda string: re.search(r", OK|Lincoln Blvd|Room \d", string),
                    capitol_office_info,
                ),
            )

            if email:
                person.add_contact_detail(
                    type="email", value=email, note="Capitol Office"
                )
            if capitol_phone:
                person.add_contact_detail(
                    type="voice", value=str(capitol_phone), note="Capitol Office"
                )

            capitol_address = "\n".join(capitol_address_lines)
            if capitol_address:
                person.add_contact_detail(
                    type="address", value=capitol_address, note="Capitol Office"
                )

        if not col2:
            self.warning(
                "{} appears to have no district office address; skipping it".format(
                    person.name
                )
            )
            return
        if "use capitol address" in col2.text_content().lower():
            return
        lxml.etree.strip_tags(col2, "sup")
        district_office_info = self._clean_office_info(col2)
        # This probably isn't a valid district office at less than two lines.
        if len(district_office_info) < 2:
            self.warning(
                "{} appears to have no district office address; skipping it".format(
                    person.name
                )
            )
            return

        district_address_lines = []
        for line in district_office_info:
            district_address_lines.append(line.strip())
            if "OK" in line:
                break

        if "OK" in district_address_lines[-1]:
            district_address = "\n".join(
                filter(lambda line: line, district_address_lines)
            )
        else:
            district_address = None
        # self.logger.debug(district_address)

        district_phone = self._extract_phone(district_office_info)

        if district_phone:
            person.add_contact_detail(
                type="voice", value=str(district_phone), note="District Office"
            )
        if district_address:
            person.add_contact_detail(
                type="address", value=district_address, note="District Office"
            )
