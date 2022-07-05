import re
import lxml.etree
from spatula import HtmlListPage, HtmlPage, CSS, SelectorError, URL
from openstates.models import ScrapePerson


class PartyAugmentation(HtmlPage):
    """
    NY Assembly does not have partisan information on their site.

    In the past we scraped NYBOE, but that broke.  This is our best option
    besides hard-coding... and it isn't good.
    """

    source = URL("https://en.wikipedia.org/wiki/New_York_State_Assembly")

    def find_rows(self):
        # the first table on the page that has a bunch of rows
        for table in CSS("table.wikitable").match(self.root):
            rows = CSS("tr").match(table)
            if len(rows) >= 150:
                return rows

    def process_page(self):
        mapping = {}
        rows = self.find_rows()
        for row in rows[1:]:
            tds = row.getchildren()
            dist = tds[0].text_content().strip()
            name = tds[2].text_content().strip()
            # get the last 6 characters off the background-color to see if it's red or blue
            party_style = tds[1].get("style")[-6:]
            party = "Democrat" if party_style == "3333FF" else "Republican"
            mapping[dist] = (name, party)
        return mapping


# TODO: consider turning these common hacks into spatula.utils


def innerhtml(elem):
    return (elem.text or "") + "\n".join(
        [lxml.etree.tostring(child).decode() for child in elem.iterchildren()]
    )


def block_to_text(elem):
    return re.sub("<br/?>", "\n", innerhtml(elem))


def parse_address_lines(text):
    """
    a fairly common occurence, a bunch of lines like
    addr line 1
    addr line 2
    addr line 3?
    phone: 555-333-3333
    fax: 555-333-3333
    maybe junk down here
    """
    phone_re = re.compile(r"\d{3}-\d{4}")
    email_re = re.compile(r"\w+@\w+\.\w+")
    mode = "address"
    address = []
    email = fax = phone = None

    for line in text.splitlines():
        line = line.strip()
        line_lower = line.lower()
        if not line:
            continue

        # check for mode-changing lines
        if (
            line_lower.startswith("phone:")
            or phone_re.findall(line_lower)
            and "fax" not in line_lower
        ):
            phone = line_lower.replace("phone:", "").strip()
            mode = None
        elif line_lower.startswith("email:") or email_re.findall(line_lower):
            email = line_lower.replace("email:", "").strip()
            mode = None
        elif line_lower.startswith("fax:"):
            fax = line_lower.replace("fax:", "").strip()
            if len(fax) == 8:
                fax = "518-" + fax
            mode = None
        elif mode == "address":
            address.append(line)

    return {"address": "; ".join(address), "fax": fax, "phone": phone, "email": email}


class Assembly(HtmlListPage):
    source = URL("https://assembly.state.ny.us/mem/")
    selector = CSS("section.mem-item", num_items=150)
    dependencies = {"party_mapping": PartyAugmentation()}

    def process_addresses(self, item):
        # 1-3 address blocks, last is always Capitol
        address_blocks = CSS(".full-addr").match(item, min_items=1, max_items=3)

        # district address #1
        district = parse_address_lines(block_to_text(address_blocks[0]))
        # capitol address
        capitol = parse_address_lines(block_to_text(address_blocks[-1]))
        # TODO: handle district address #2 if it exists

        return district, capitol

    def process_item(self, item):
        # strip leading zero
        district = str(int(item.get("id")))
        image = CSS(".mem-pic a img").match_one(item).get("src")
        name = CSS(".mem-name a").match_one(item)

        district_addr, capitol_addr = self.process_addresses(item)

        # email, twitter, facebook are all sometimes present
        try:
            email = CSS(".mem-email a").match_one(item).text.strip()
        except SelectorError:
            email = ""
        try:
            twitter = CSS(".fa-twitter").match_one(item)
            twitter = twitter.getparent().get("href").split("/")[-1]
        except SelectorError:
            twitter = ""
        try:
            facebook = CSS(".fa-facebook").match_one(item)
            facebook = facebook.getparent().get("href").split("/")[-1]
        except SelectorError:
            facebook = ""

        party = self.party_mapping[district][1]

        p = ScrapePerson(
            state="ny",
            chamber="lower",
            image=image,
            party=party,
            district=district,
            name=name.text.strip(),
            email=email,
        )
        p.add_link(url=name.get("href"))
        p.add_source(url=name.get("href"))
        if twitter:
            p.ids.twitter = twitter
        if facebook:
            p.ids.facebook = facebook
        p.district_office.address = district_addr["address"]
        p.district_office.voice = district_addr["phone"] or ""
        p.district_office.fax = district_addr["fax"] or ""
        p.capitol_office.address = capitol_addr["address"]
        p.capitol_office.voice = capitol_addr["phone"] or ""
        p.capitol_office.fax = capitol_addr["fax"] or ""
        return p
