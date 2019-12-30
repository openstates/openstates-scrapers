import re
import collections
import unicodedata
from operator import methodcaller

import lxml.html
from pupa.scrape import Scraper, Person


def parse_address(s, split=re.compile(r"[;,]\s{,3}").split):
    """
    Extract address fields from text.
    """
    # If the address isn't formatted correctly, skip for now.
    if ";" not in s:
        return []

    fields = "city state_zip phone".split()
    vals = split(s)
    res = []
    while True:
        try:
            _field = fields.pop()
            _value = vals.pop()
        except IndexError:
            break
        else:
            if _value.strip():
                res.append((_field, _value))
    if vals:
        res.append(("street", ", ".join(vals)))
    return res


class CAPersonScraper(Scraper):
    urls = {
        "upper": "http://senate.ca.gov/senators",
        "lower": "http://assembly.ca.gov/assemblymembers",
    }

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        url = self.urls[chamber]
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        if chamber == "lower":
            rows = doc.xpath("//table/tbody/tr")
            parse = self.parse_assembly
        else:
            rows = doc.xpath('//div[contains(@class, "views-row")]')
            parse = self.parse_senate

        for tr in rows:
            person = parse(tr, chamber)
            if person is None:
                continue
            if "Vacant" in person.name:
                continue

            person.add_source(url)

            yield person

    def parse_senate(self, div, chamber):
        name = div.xpath(".//h3/text()")[0]
        if name.endswith(" (R)"):
            party = "Republican"
        elif name.endswith(" (D)"):
            party = "Democratic"
        else:
            self.warning("skipping " + name)
            return None
        name = name.split(" (")[0]

        district = (
            div.xpath('.//div[contains(@class, "senator-district")]/div/text()')[0]
            .strip()
            .lstrip("0")
        )
        photo_url = div.xpath(".//img/@src")[0]

        person = Person(
            name=name,
            party=party,
            district=district,
            primary_org=chamber,
            image=photo_url,
        )

        url = div.xpath(".//a/@href")[0]
        person.add_link(url)

        # CA senators have working emails, but they're not putting them on
        # their public pages anymore
        email = self._construct_email(chamber, name)

        person.add_contact_detail(type="email", value=email, note="Senate Office")

        office_path = './/div[contains(@class, "{}")]//p'

        for addr in div.xpath(
            office_path.format("views-field-field-senator-capitol-office")
        ):
            note = "Senate Office"
            addr, phone = addr.text_content().split("; ")
            person.add_contact_detail(type="address", value=addr.strip(), note=note)
            person.add_contact_detail(type="voice", value=phone.strip(), note=note)

        n = 1
        for addr in div.xpath(
            office_path.format("views-field-field-senator-district-office")
        ):
            note = "District Office #{}".format(n)
            for addr in addr.text_content().strip().splitlines():
                try:
                    addr, phone = addr.strip().replace(u"\xa0", " ").split("; ")
                    person.add_contact_detail(
                        type="address", value=addr.strip(), note=note
                    )
                    person.add_contact_detail(
                        type="voice", value=phone.strip(), note=note
                    )
                except ValueError:
                    addr = addr.strip().replace(u"\xa0", " ")
                    person.add_contact_detail(
                        type="address", value=addr.strip(), note=note
                    )
            n += 1

        return person

    def parse_assembly(self, tr, chamber):
        """
        Given a tr element, get specific data from it.
        """

        strip = methodcaller("strip")

        xpath = 'td[contains(@class, "views-field-field-%s-%s")]%s'

        xp = {
            "url": [("lname-sort", '/a[not(contains(text(), "edit"))]/@href')],
            "district": [("district", "/text()")],
            "party": [("party", "/text()")],
            "name": [
                ("office-information", '/a[not(contains(text(), "edit"))]/text()')
            ],
            "address": [
                ("office-information", "/h3/following-sibling::text()"),
                ("office-information", "/p/text()"),
            ],
        }

        titles = {"upper": "senator", "lower": "member"}

        funcs = {
            "name": lambda s: re.sub(  # "Assembly" is misspelled once
                r"Contact Assembl?y Member", "", s
            ).strip(),
            "address": parse_address,
        }

        tr_xpath = tr.xpath
        res = collections.defaultdict(list)
        for k, xpath_info in xp.items():
            for vals in xpath_info:
                f = funcs.get(k, lambda _: _)
                vals = (titles[chamber],) + vals
                vals = map(f, map(strip, tr_xpath(xpath % vals)))
                res[k].extend(vals)

        # Photo.
        try:
            res["image"] = tr_xpath("td/p/img/@src")[0]
        except IndexError:
            pass

        # Remove junk from assembly member names.
        junk = "Contact Assembly Member "

        try:
            res["name"] = res["name"].pop().replace(junk, "")
        except IndexError:
            return

        # Normalize party.
        for party in res["party"][:]:
            if party:
                if party == "Democrat":
                    party = "Democratic"
                res["party"] = party
                break
            else:
                res["party"] = None

        # strip leading zero
        res["district"] = str(int(res["district"].pop()))

        person = Person(
            name=res["name"],
            district=res.get("district"),
            party=res.get("party"),
            image=res.get("image"),
            primary_org=chamber,
        )

        # Mariko Yamada also didn't have a url that lxml would parse
        # as of 3/22/2013.
        if res["url"]:
            person.add_link(res["url"].pop())

        # Addresses.
        addresses = res["address"]
        try:
            addresses = map(dict, filter(None, addresses))
        except ValueError:
            # Sometimes legislators only have one address, in which
            # case this awful hack is helpful.
            addresses = map(dict, filter(None, [addresses]))
        addresses = list(addresses)

        for address in addresses:
            # Toss results that don't have required keys.
            if not set(["street", "city", "state_zip"]) < set(address):
                if address in addresses:
                    addresses.remove(address)

        # Re-key the addresses
        offices = []
        if addresses:
            # Mariko Yamada's addresses wouldn't parse correctly as of
            # 3/23/2013, so here we're forced to test whether any
            # addresses were even found.
            addresses[0].update(type="capitol", name="Capitol Office")
            offices.append(addresses[0])

            # CA reps have working emails, but they're not putting them on
            # their public pages anymore
            offices[0]["email"] = self._construct_email(chamber, res["name"])

            for n, office in enumerate(addresses[1:]):
                office.update(type="district", name="District Office #{}".format(n + 1))
                offices.append(office)

            for office in offices:
                street = office["street"]
                state_zip = re.sub(r"\s+", " ", office["state_zip"])
                street = "%s\n%s, %s" % (street, office["city"], state_zip)
                office["address"] = street
                office["fax"] = None
                if "email" not in office:
                    office["email"] = None

                note = office["name"]
                person.add_contact_detail(
                    type="address", value=office["address"], note=note
                )
                if office["phone"]:
                    person.add_contact_detail(
                        type="voice", value=office["phone"], note=note
                    )
                if office["email"]:
                    person.add_contact_detail(
                        type="email", value=office["email"], note=note
                    )

        return person

    def _construct_email(self, chamber, name):
        suffix = [
            "Ph.D.",
            "Ret.",
            "Sr.",
            "Jr.",
            "Ed.D.",
            "II",
            "III",
            "IV",
            "V",
            "B.V.M.",
            "CFRE",
            "CLU",
            "CPA",
            "C.S.C.",
            "C.S.J.",
            "D.C.",
            "D.D.",
            "D.D.S.",
            "D.M.D.",
            "D.O.",
            "D.V.M.",
            "Inc.",
            "J.D.",
            "LL.D.",
            "Ltd.",
            "M.D.",
            "O.D.",
            "O.S.B.",
            "P.C.",
            "P.E.",
            "R.G.S",
            "R.N.",
            "R.N.C.",
            "S.H.C.J.",
            "S.J.",
            "S.N.J.M.",
            "S.S.M.O.",
            "USA",
            "USAF",
            "USAFR",
            "USAR",
            "USCG",
            "USMC",
            "USMCR",
            "USN",
            "USNR",
        ]
        if any(check in name for check in suffix):
            last_name = re.split(r"\s+", name)[-2].lower()
        else:
            last_name = re.split(r"\s+", name)[-1].lower()
        # translate accents to non-accented versions for use in an
        # email and drop apostrophes
        last_name = "".join(
            c
            for c in unicodedata.normalize("NFD", last_name)
            if unicodedata.category(c) != "Mn"
        )
        last_name = last_name.replace("'", "").replace(",", "")

        if chamber == "lower":
            return "assemblymember." + last_name + "@assembly.ca.gov"
        else:
            return "senator." + last_name + "@sen.ca.gov"
