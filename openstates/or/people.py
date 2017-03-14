# -*- coding: utf-8 -*-
import re
import unicodedata
from pupa.scrape import Person, Scraper
from openstates.utils import LXMLMixin


def itergraphs(elements, break_):
    buf = []
    for element in elements:
        if element.tag == break_:
            yield buf
            buf = []
            continue
        buf.append(element)
    if buf:
        yield buf


class ORPersonScraper(Scraper, LXMLMixin):
    jurisdiction = 'or'

    URLs = {
        "lower": "http://www.oregonlegislature.gov/house/Pages/RepresentativesAll.aspx",
        "upper": "http://www.oregonlegislature.gov/senate/Pages/SenatorsAll.aspx",
    }

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber('upper')
            yield from self.scrape_chamber('lower')

    def scrape_chamber(self, chamber):
        url = self.URLs[chamber]
        page = self.lxmlize(url)

        for block in page.xpath("//div[@class='ms-rtestate-field']")[1:-1]:
            # Each legislator block.

            photo_block = block.xpath("ancestor::td/preceding-sibling::td")
            if len(photo_block) == 0:
                continue

            h2s = block.xpath(".//h2/a")
            if len(h2s) != 1:
                # We've got a Vacant person.
                print("Found a Vacant position. Skipping block.")
                continue

            h2, = h2s
            name = h2.text
            # Need to remove weird Unicode spaces from their names
            if not isinstance(name, str):
                name = "".join(c for c in name
                               if unicodedata.category(c)[0] != "C")

            name = " ".join(name.split())
            name = re.sub(r'^\W?(Senator|Representative)\W?(?=[A-Z])',
                          "", name)
            photo_block, = photo_block
            # (The <td> before ours was the photo)
            img, = photo_block.xpath("*")
            img = img.attrib['src']

            info = {}
            # Right, now let's get info out of their little profile box.
            for entry in block.xpath(".//p"):
                key = None
                for kvpair in itergraphs(entry.xpath("./*"), 'br'):
                    # OK. We either get the tail or the next element
                    # (usually an <a> tag)
                    if len(kvpair) == 1:
                        key, = kvpair
                        value = key.tail.strip() if key.tail else None
                        if value:
                            value = re.sub("\s+", " ", value).strip()
                    elif len(kvpair) == 2:
                        key, value = kvpair
                        if value.text_content().strip() == "arty:":
                            key = value
                            value = value.tail
                    elif len(kvpair) == 3:
                        k1, k2, value = kvpair
                        # As seen with a <stong><strong>Email:</strong></strong>
                        t = lambda x: x.text_content().strip()
                        assert t(k1) == "" or t(k2) == ""
                        if t(k1) != "":
                            key = k1
                        else:
                            key = k2
                    else:
                        # Never seen text + an <a> tag, perhaps this can happen.
                        raise ValueError("Too many elements. Something changed")

                    key = key.text_content().strip(" :")
                    if value is None:
                        # A page has the value in a <strong> tag. D'oh.
                        key, value = (x.strip() for x in key.rsplit(":", 1))

                    key = re.sub("\s+", " ", key).strip()
                    key = key.replace(":", "")
                    if key == "arty":
                        key = "Party"

                    info[key] = value

            info['District'] = str(int(info['District'].encode(
                'ascii', 'ignore').strip()))
            info['Party'] = info['Party'].strip(": ").replace(u"\u00a0","")



            # scrape legislator details
            phone = info.get('Capitol Phone', info.get('apitol Phone'))
            if hasattr(phone, 'text_content'):
                phone = phone.text_content()
            address = info['Capitol Address']
            email = info['Email'].attrib['href'].replace("mailto:","")
            website = info['Website'].attrib['href']

            # save legislator
            person = Person(name=name,
                            primary_org=chamber,
                            party=info['Party'],
                            district=info['District'],
                            image=img)

            person.add_source(url)
            person.add_link(h2.attrib['href'])

            if phone:
                person.add_contact_detail(type='voice', value=phone,
                                          note='Capitol Office')
            if address:
                person.add_contact_detail(type='address', value=address,
                                          note='Capitol Office')
            if email:
                person.add_contact_detail(type='email', value=email)
            if website:
                person.add_contact_detail(type='url', value=website)

            yield person
