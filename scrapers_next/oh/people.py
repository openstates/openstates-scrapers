import re
import attr
from spatula import HtmlListPage, HtmlPage, CSS
from ..common.people import ScrapePerson

background_image_re = re.compile(r"background-image:url\((.*?)\)")


@attr.s
class HousePartial:
    name = attr.ib()
    district = attr.ib()
    party = attr.ib()
    url = attr.ib()
    image = attr.ib()


class House(HtmlListPage):
    source = "https://www.legislature.ohio.gov/legislators/house-directory"
    selector = CSS(".mediaGrid a[target='_blank']", num_items=99)

    def process_item(self, item):
        name = CSS(".mediaCaptionTitle").match_one(item).text
        subtitle = CSS(".mediaCaptionSubtitle").match_one(item).text
        image = CSS(".photo").match_one(item).get("style")
        image = background_image_re.findall(image)[0]
        # e.g. District 25 | D
        district, party = subtitle.split(" | ")
        district = district.split()[1]
        party = {"D": "Democratic", "R": "Republican"}[party]

        return HouseDetail(
            HousePartial(
                name=name,
                district=district,
                party=party,
                url=item.get("href"),
                image=image,
            )
        )


class HouseDetail(HtmlPage):
    input_type = HousePartial

    def process_page(self):
        # construct person from the details from above
        p = ScrapePerson(
            state="oh",
            chamber="lower",
            district=self.input.district,
            name=self.input.name,
            party=self.input.party,
            image=self.input.image,
        )
        p.add_source(self.input.url)
        p.add_link(self.input.url)

        divs = CSS(".member-info-bar-module").match(self.root)
        # last div is contact details
        contact_details = CSS(".member-info-bar-value").match(divs[-1])
        for div in contact_details:
            dtc = div.text_content()
            if ", OH" in dtc:
                # join parts of the div together to make whole address
                children = div.getchildren()
                p.capitol_office.address = "; ".join(
                    [
                        children[0].text.strip(),
                        children[0].tail.strip(),
                        children[1].tail.strip(),
                    ]
                )
            elif "Phone:" in dtc:
                p.capitol_office.voice = dtc.split(": ")[1]
            elif "Fax:" in dtc:
                p.capitol_office.fax = dtc.split(": ")[1]

        return p
