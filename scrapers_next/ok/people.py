from spatula import HtmlListPage, HtmlPage, SimilarLink, CSS
from openstates.models import ScrapePerson


class Senate(HtmlListPage):
    selector = SimilarLink("https://oksenate.gov/senators/", min_items=45, max_items=48)
    source = "https://oksenate.gov/senators"

    def process_item(self, item):
        party, _, district, name = item.text_content().split(maxsplit=3)
        return SenateDetail(
            {"party": party, "district": district, "name": name.strip()},
            source=item.get("href"),
        )


class House(HtmlListPage):
    selector = SimilarLink(
        r"https://www.okhouse.gov/Members/District.aspx\?District=", num_items=101
    )
    source = "https://www.okhouse.gov/Members/Default.aspx"

    def process_item(self, item):
        return HouseDetail({"name": item.text.strip()}, source=item.get("href"))


class HouseDetail(HtmlPage):
    image_selector = SimilarLink("https://www.okhouse.gov/Members/Pictures/HiRes/")
    prefix = "#ctl00_ContentPlaceHolder1_lbl"
    name_css = CSS(prefix + "Name")
    district_css = CSS(prefix + "District")
    party_css = CSS(prefix + "Party")

    def process_page(self):
        name = self.name_css.match_one(self.root).text.split(maxsplit=1)
        if len(name) < 2:
            # empty seat
            return None
        name = name[1]
        p = ScrapePerson(
            name=name,
            state="ok",
            chamber="lower",
            party=self.party_css.match_one(self.root).text,
            district=self.district_css.match_one(self.root).text.split()[1],
        )
        p.image = self.image_selector.match_one(self.root).get("href")

        contact_url = self.source.url.replace("District.aspx", "Contact.aspx")
        assert contact_url.startswith(
            "https://www.okhouse.gov/Members/Contact.aspx?District="
        )
        p.add_link(contact_url, note="Contact Form")

        # capitol address
        check_capitol_address = (
            CSS(".districtheadleft").match(self.root)[0].text_content().strip()
        )
        if check_capitol_address == "Capitol Address:":
            capitol_address_div = (
                CSS(".districtheadleft + div")
                .match(self.root)[0]
                .text_content()
                .strip()
                .splitlines()
            )
            p.capitol_office.address = "; ".join(
                [ln.strip() for ln in capitol_address_div[:-1]]
            )
            p.capitol_office.voice = capitol_address_div[-1].strip()
        return p


class SenateDetail(HtmlPage):
    name_css = CSS(".field--name-title")
    image_css = CSS(".bSenBio__media-btn")
    district_css = CSS(".bDistrict h2")
    address_css = CSS(".bSenBio__address p")
    phone_css = CSS(".bSenBio__tel a")
    contact_link_sel = SimilarLink(r"https://oksenate.gov/contact-senator\?sid=")

    def process_page(self):
        for bio in CSS(".bSenBio__infoIt").match(self.root):
            if "Party:" in bio.text_content():
                party = bio.text_content().split(":")[1].strip()
        p = ScrapePerson(
            name=self.name_css.match_one(self.root).text,
            state="ok",
            chamber="upper",
            party=party,
            image=self.image_css.match_one(self.root).get("href"),
            district=self.district_css.match_one(self.root).text.strip().split()[1],
        )
        p.capitol_office.address = self.address_css.match_one(self.root).text
        p.capitol_office.voice = self.phone_css.match_one(self.root).text
        p.add_link(
            self.contact_link_sel.match_one(self.root).get("href"), "Contact Form"
        )

        return p
