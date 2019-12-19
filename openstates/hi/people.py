from pupa.scrape import Person, Scraper, Organization
import lxml.html


HI_BASE_URL = "http://capitol.hawaii.gov"


def get_legislator_listing_url(chamber):
    chamber = {"lower": "H", "upper": "S"}[chamber]

    return "%s/members/legislators.aspx?chamber=%s" % (HI_BASE_URL, chamber)


class HIPersonScraper(Scraper):
    def get_page(self, url):
        html = self.get(url).text
        page = lxml.html.fromstring(html)
        return page

    def scrape_homepage(self, url):
        page = self.get_page(url)
        ret = {"source": url, "ctty": []}

        table = page.xpath("//table[@id='ContentPlaceHolderCol1_GridViewMemberof']")
        if len(table) > 0:
            table = table[0]
        else:
            table = None

        chamber = page.xpath("//span[contains(@id, 'LabelChamber')]")
        if chamber == []:
            raise Exception("Can't find the chamber label")

        chamber = chamber[0].text_content()
        ret["chamber"] = chamber

        if table is not None:
            cttys = table.xpath("./tr/td/a")
            for ctty in cttys:
                ret["ctty"].append(
                    {
                        "name": ctty.text,
                        "page": "%s/%s" % (HI_BASE_URL, ctty.attrib["href"]),
                    }
                )
        return ret

    def scrape_leg_page(self, url):
        page = self.get_page(url)
        people = page.xpath("//table[@id='ContentPlaceHolderCol1_GridView1']")[0]
        people = people.xpath("./tr")[1:]
        display_order = {"image": 0, "contact": 1, "district": 2}

        ret = []

        for person in people:
            image = person[display_order["image"]]
            contact = person[display_order["contact"]]
            district = person[display_order["district"]]
            metainf = self.scrape_contact_info(contact)
            district = self.scrape_district_info(district)
            homepage = self.scrape_homepage(metainf["homepage"])

            image = "%s/%s" % (HI_BASE_URL, image.xpath("./*/img")[0].attrib["src"])

            pmeta = {
                "image": image,
                "source": [url],
                "district": district,
                "chamber": None,
            }

            if homepage is not None:
                pmeta["source"].append(homepage["source"])
                pmeta["ctty"] = homepage["ctty"]
                pmeta["chamber"] = homepage["chamber"]

            if pmeta["chamber"] is None:
                raise Exception("No chamber found.")

            for meta in metainf:
                pmeta[meta] = metainf[meta]

            ret.append(pmeta)
        return ret

    def br_split(self, contact):
        cel = []
        els = [cel]

        # krufty HTML requires stupid hacks
        elements = contact.xpath("./*")
        for element in elements:
            if element.tag == "br":
                cel = []
                els.append(cel)
            else:
                cel.append(element)
        return els

    def scrape_district_info(self, district):
        return district[2].text_content()

    def scrape_contact_info(self, contact):
        homepage = "%s/%s" % (  # XXX: Dispatch a read on this page
            HI_BASE_URL,
            contact.xpath("./a")[0].attrib["href"],
        )

        els = self.br_split(contact)

        def _scrape_title(els):
            return els[0].text_content()

        def _scrape_name(els):
            lName = els[0].text_content()
            fName = els[2].text_content()
            return "%s %s" % (fName, lName)

        def _scrape_party(els):
            party = {"(D)": "Democratic", "(R)": "Republican"}

            try:
                return party[els[4].text_content()]
            except KeyError:
                return "Other"

        def _scrape_addr(els):
            room_number = els[1].text_content()
            slug = els[0].text_content()
            return "%s %s" % (slug, room_number)

        def _scrape_room(els):
            return els[1].text_content()

        def _scrape_phone(els):
            return els[1].text_content()

        def _scrape_fax(els):
            return els[1].text_content()

        def _scrape_email(els):
            return els[1].text_content()

        contact_entries = {
            "title": (0, _scrape_title),
            "name": (1, _scrape_name),
            "party": (1, _scrape_party),
            "addr": (2, _scrape_addr),
            "room": (2, _scrape_room),
            "phone": (3, _scrape_phone),
            "fax": (4, _scrape_fax),
            "email": (5, _scrape_email),
        }

        ret = {"homepage": homepage}

        for entry in contact_entries:
            index, callback = contact_entries[entry]
            ret[entry] = callback(els[index])
        return ret

    def scrape_chamber(self, chamber=None):
        metainf = self.scrape_leg_page(get_legislator_listing_url(chamber))
        for leg in metainf:
            try:
                chamber = {"House": "lower", "Senate": "upper"}[leg["chamber"]]
            except KeyError:
                print("")
                print("  ERROR: Bad Legislator page.")
                print("    -> " + "\n    -> ".join(leg["source"]))
                print("")
                print("  Added this workaround because of a bad legislator")
                print("  page, while they filled their info out.")
                print("")
                print("  Emailed webmaster. Told to wait.")
                print("   - PRT, Jun 23, 2014")
                print("")
                continue

            person = Person(
                name=leg["name"],
                district=leg["district"],
                party=leg["party"],
                primary_org=chamber,
                image=leg["image"],
            )

            for source in leg["source"]:
                person.add_source(source)

            try:
                for ctty in leg["ctty"]:
                    flag = "Joint Legislative"
                    if ctty["name"][: len(flag)] == flag:
                        ctty_chamber = "joint"
                    else:
                        ctty_chamber = chamber

                    comm = Organization(
                        name=ctty["name"],
                        classification="committee",
                        chamber=ctty_chamber,
                    )
                    comm.add_member(person, role="member")

            except KeyError:
                self.warn("%s has no scraped Committees" % leg["name"])

            person.add_link(leg["homepage"])

            if leg["addr"]:
                person.add_contact_detail(
                    type="address", value=leg["addr"], note="Capitol Office"
                )
            if leg["phone"]:
                person.add_contact_detail(
                    type="voice", value=leg["phone"], note="Capitol Office"
                )
            if leg["email"]:
                person.add_contact_detail(
                    type="email", value=leg["email"], note="Capitol Office"
                )
            if leg["fax"]:
                person.add_contact_detail(
                    type="fax", value=leg["fax"], note="Capitol Office"
                )
            yield person

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")
