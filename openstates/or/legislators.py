from billy.scrape.legislators import LegislatorScraper, Legislator
import lxml.html
import re


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


class ORLegislatorScraper(LegislatorScraper):
    jurisdiction = 'or'

    URLs = {
        "lower": "http://www.oregonlegislature.gov/house/Pages/RepresentativesAll.aspx",
        "upper": "http://www.oregonlegislature.gov/senate/Pages/SenatorsAll.aspx",
    }

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def scrape(self, chamber, term):
        url = self.URLs[chamber]
        page = self.lxmlize(url)

        for block in page.xpath("//div[@class='ms-rtestate-field']")[1:-1]:
            # Each legislator block.

            photo_block = block.xpath("ancestor::td/preceding-sibling::td")
            if len(photo_block) == 0:
                continue

            photo_block, = photo_block
            # (The <td> before ours was the photo)
            img, = photo_block.xpath("*")
            img = img.attrib['src']

            h2, = block.xpath(".//h2/a")
            name = h2.text

            info = {}
            # Right, now let's get info out of their little profile box.
            for entry in block.xpath(".//p"):
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
                    else:
                        # Never seen text + an <a> tag, perhaps this can happen.
                        raise ValueError("Too many elements. Something changed")

                    key = key.text_content().strip(" :")
                    if value is None:
                        # A page has the value in a <strong> tag. D'oh.
                        key, value = (x.strip() for x in key.rsplit(":", 1))

                    key = re.sub("\s+", " ", key).strip()

                    info[key] = value

            info['District'] = info['District'].encode(
                'ascii', 'ignore').strip()

            info['Party'] = info['Party'].strip(": ")

            leg = Legislator(term=term,
                             url=h2.attrib['href'],
                             chamber=chamber,
                             full_name=name,
                             party=info['Party'],
                             district=info['District'],
                             photo_url=img)
            leg.add_source(url)

            phone = info.get('Capitol Phone', info.get('apitol Phone'))
            if hasattr(phone, 'text_content'):
                phone = phone.text_content()

            leg.add_office(type='capitol',
                           name='Capitol Office',
                           address=info['Capitol Address'],
                           phone=phone,
                           email=info['Email'].attrib['href'].replace("mailto:",""))

            self.save_legislator(leg)
