from spatula import URL, HtmlPage, CSS, SelectorError, XPath, JsonPage
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_error_response(self, response):
        self.logger.warning(response)
        pass

    def process_page(self):
        p = self.input

        # this guy's html/image is different
        if p.name == "Rob Wagner":
            img = "https://www.oregonlegislature.gov/wagner/PublishingImages/member_photo.jpg"
        elif p.name == "Kathleen Taylor":
            img = "https://www.oregonlegislature.gov/taylor/PublishingImages/member_photo.jpg"
        else:
            img = CSS("h1 img").match_one(self.root).get("src")
        p.image = img

        try:
            district_info = XPath("//p//strong[contains(text(), 'District')]").match(
                self.root
            )
            for tag in district_info:
                if re.search(r"District\sPhone:", tag.text_content()):
                    if tag.tail is None and p.name == "Boomer Wright":
                        p.district_office.voice = (
                            tag.getnext().getnext().text_content().strip()
                        )
                    elif tag.tail is None:
                        p.district_office.voice = tag.getnext().text_content().strip()
                    else:
                        p.district_office.voice = tag.tail.strip()
                elif re.search(
                    r"District(\s|\xa0)(Mailing)?\s?Address:", tag.text_content()
                ):
                    if tag.tail is None or tag.tail.strip() == "":
                        p.district_office.address = tag.getnext().text_content().strip()
                    else:
                        p.district_office.address = tag.tail.strip()
                else:
                    if (
                        tag.getnext() is not None
                        and tag.getnext().text_content().strip() == "Phone:"
                    ):
                        p.district_office.voice = tag.getnext().tail.strip()
                    elif tag.tail is not None and tag.tail.strip() == "Address:":
                        p.district_office.address = tag.getparent().tail.strip()
        except SelectorError:
            pass

        return p


class LegList(JsonPage):
    source = URL(
        "https://api.oregonlegislature.gov/odata/odataservice.svc/LegislativeSessions('2021R1')/Legislators",
        headers={"Accept": "application/json"},
    )

    def process_page(self):
        legislators = self.data["value"]
        for leg in legislators:
            first_name = leg["FirstName"].strip()
            last_name = leg["LastName"].strip()
            name = f"{first_name} {last_name}"

            chamber = leg["Chamber"].strip()
            if chamber == "H":
                chamber = "lower"
            elif chamber == "S":
                chamber = "upper"

            party = leg["Party"].strip()
            if party == "Democrat":
                party = "Democratic"

            district = leg["DistrictNumber"].strip()

            p = ScrapePerson(
                name=name,
                state="or",
                chamber=chamber,
                district=district,
                party=party,
            )

            p.add_source(self.source.url)

            p.family_name = last_name
            p.given_name = first_name

            cap_address = leg["CapitolAddress"].strip()
            p.capitol_office.address = cap_address

            cap_phone = leg["CapitolPhone"]
            if cap_phone:
                p.capitol_office.voice = cap_phone.strip()

            title = leg["Title"].strip()
            if title not in ["Senator", "Representative"]:
                p.extras["title"] = title

            email = leg["EmailAddress"].strip()
            p.email = email

            website = leg["WebSiteUrl"]
            p.add_link(website, note="homepage")
            p.add_source(website)

            # this guy's website is messed up
            if p.name == "Daniel Bonham":
                p.image = "https://www.oregonlegislature.gov/bonham/PublishingImages/member_photo.jpg"
                yield p
            else:
                yield LegDetail(p, source=website)
