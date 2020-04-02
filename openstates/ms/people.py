import lxml.etree

from openstates_core.scrape import Person, Scraper

import scrapelib
import os.path


CAP_ADDRESS = """P. O. Box 1018
Jackson, MS 39215"""


class MSLegislatorScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_legs(chamber)
        else:
            yield from self.scrape_legs("upper")
            yield from self.scrape_legs("lower")

    def scrape_legs(self, chamber):
        if chamber == "upper":
            url = "http://billstatus.ls.state.ms.us/members/ss_membs.xml"
            range_num = 5
        else:
            url = "http://billstatus.ls.state.ms.us/members/hr_membs.xml"
            range_num = 6

        leg_dir_page = self.get(url)
        root = lxml.etree.fromstring(leg_dir_page.content)
        for mr in root.xpath("//LEGISLATURE/MEMBER"):
            for num in range(1, range_num):
                leg_path = "string(M%s_NAME)" % num
                leg_link_path = "string(M%s_LINK)" % num
                leg = mr.xpath(leg_path)
                leg_link = mr.xpath(leg_link_path)
                role = ""
                yield from self.scrape_details(chamber, leg, leg_link, role)

        # TODO: come back and do roles correctly at some point

        if chamber == "lower":
            chair_name = root.xpath("string(//CHAIR_NAME)")
            chair_link = root.xpath("string(//CHAIR_LINK)")
            yield from self.scrape_details(chamber, chair_name, chair_link, role)
            chair_name = root.xpath("string(//PROTEMP_NAME)")
            chair_link = root.xpath("string(//PROTEMP_LINK)")
            yield from self.scrape_details(chamber, chair_name, chair_link, role)
            # role = root.xpath('string(//CHAIR_TITLE)')
        # else:
        # Senate Chair is the Governor. Info has to be hard coded
        # chair_name = root.xpath('string(//CHAIR_NAME)')
        # role = root.xpath('string(//CHAIR_TITLE)')
        # TODO: if we're going to hardcode the governor, do it better
        # district = "Governor"
        # leg = Legislator(term_name, chamber, district, chair_name,
        #                 first_name="", last_name="", middle_name="",
        #                 party="Republican", role=role)

        # disabling this since it creates duplicates right now
        # protemp_name = root.xpath('string(//PROTEMP_NAME)')
        # protemp_link = root.xpath('string(//PROTEMP_LINK)')
        # role = root.xpath('string(//PROTEMP_TITLE)')
        # yield from self.scrape_details(chamber, protemp_name, protemp_link, role)

    def scrape_details(self, chamber, leg_name, leg_link, role):
        if not leg_link:
            # Vacant post, likely:
            if "Vacancy" in leg_name:
                return
            raise Exception("leg_link is null. something went wrong")
        try:
            url = "http://billstatus.ls.state.ms.us/members/%s" % leg_link
            url_root = os.path.dirname(url)
            details_page = self.get(url)
            root = lxml.etree.fromstring(details_page.content)
            party = root.xpath("string(//PARTY)")

            district = root.xpath("string(//DISTRICT)")

            photo = "%s/%s" % (url_root, root.xpath("string(//IMG_NAME)"))

            home_phone = root.xpath("string(//H_PHONE)")

            home_address = root.xpath("string(//H_ADDRESS)")
            home_address2 = root.xpath("string(//H_ADDRESS2)")
            home_city = root.xpath("string(//H_CITY)")
            home_zip = root.xpath("string(//H_ZIP)")

            home_address_total = ""
            if home_address and home_city:
                if not home_address2:
                    home_address_total = "%s\n%s, MS %s" % (
                        home_address,
                        home_city,
                        home_zip,
                    )
                else:
                    home_address_total = "%s\n%s\n%s, MS %s" % (
                        home_address,
                        home_address2,
                        home_city,
                        home_zip,
                    )

            # bis_phone = root.xpath('string(//B_PHONE)')
            capital_phone = root.xpath("string(//CAP_PHONE)")
            # other_phone = root.xpath('string(//OTH_PHONE)')
            org_info = root.xpath("string(//ORG_INFO)")
            email_name = root.xpath("string(//EMAIL_ADDRESS)").strip()
            cap_room = root.xpath("string(//CAP_ROOM)")

            if leg_name in ("Lataisha Jackson", "John G. Faulkner"):
                assert not party, (
                    "Remove special-casing for this Democrat without a "
                    "listed party: {}"
                ).format(leg_name)
                party = "Democratic"
            elif leg_name in ("James W. Mathis", "John Glen Corley"):
                assert not party, (
                    "Remove special-casing for this Republican without"
                    " a listed party: {}"
                ).format(leg_name)
                party = "Republican"
            elif party == "D":
                party = "Democratic"
            elif party == "R":
                party = "Republican"
            elif party == "I":
                party = "Independent"
            else:
                raise AssertionError(
                    "A member with no identifiable party was found: {}".format(leg_name)
                )
            leg = Person(
                primary_org=chamber,
                district=district,
                party=party,
                image=photo,
                name=leg_name,
                role=role,
            )
            leg.extras["org_info"] = org_info
            leg.add_source(url)
            leg.add_link(url)

            if email_name != "":
                if "@" in email_name:
                    email = email_name
                else:
                    email = "%s@%s.ms.gov" % (
                        email_name,
                        {"upper": "senate", "lower": "house"}[chamber],
                    )
                leg.add_contact_detail(type="email", value=email, note="Capitol Office")

            if capital_phone != "":
                leg.add_contact_detail(
                    type="voice", value=capital_phone, note="Capitol Office"
                )

            if cap_room != "":
                address = "Room %s\n%s" % (cap_room, CAP_ADDRESS)
            else:
                address = CAP_ADDRESS
            leg.add_contact_detail(type="address", value=address, note="Capitol Office")

            if home_phone != "":
                leg.add_contact_detail(
                    type="voice", value=home_phone, note="District Office"
                )

            if home_address_total != "":
                leg.add_contact_detail(
                    type="address", value=home_address_total, note="District Office"
                )

            yield leg
        except scrapelib.HTTPError as e:
            self.warning(str(e))
