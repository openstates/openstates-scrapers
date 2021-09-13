from spatula import URL, XmlPage, HtmlPage, CSS
from openstates.models import ScrapePerson

# from .apiclient import OregonLegislatorODataClient
# from .utils import SESSION_KEYS


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        # this guy's image is different
        if p.name == "Rob Wagner":
            img = "https://www.oregonlegislature.gov/wagner/PublishingImages/member_photo.jpg"
        else:
            img = CSS("h1 img").match_one(self.root).get("src")
        print(img)
        p.image = img

        return p


class LegList(XmlPage):
    source = URL(
        "https://api.oregonlegislature.gov/odata/odataservice.svc/LegislativeSessions('2021R1')/Legislators"
    )

    def process_page(self):
        legislators = self.root[4:]
        for leg in legislators:
            content = leg[9]

            first_name = content[0][2].text
            last_name = content[0][3].text
            name = first_name.strip() + " " + last_name.strip()
            # this guy's website is messed up
            if name == "Daniel Bonham":
                continue

            chamber = content[0][7].text
            if chamber.strip() == "H":
                chamber = "lower"
            elif chamber.strip() == "S":
                chamber = "upper"

            party = content[0][8].text
            if party.strip() == "Democrat":
                party = "Democratic"

            district = content[0][9].text

            p = ScrapePerson(
                name=name,
                state="or",
                chamber=chamber,
                district=district,
                party=party,
            )

            p.add_source(self.source.url)

            p.family_name = last_name.strip()
            p.given_name = first_name.strip()

            cap_address = content[0][4].text
            p.capitol_office.address = cap_address.strip()

            cap_phone = content[0][5].text
            if cap_phone:
                p.capitol_office.voice = cap_phone.strip()

            title = content[0][6].text
            if title.strip() not in ["Senator", "Representative"]:
                p.extras["title"] = title.strip()

            email = content[0][10].text
            p.email = email.strip()

            website = content[0][11].text
            p.add_link(website, note="homepage")
            p.add_source(website)

            yield LegDetail(p, source=website)
