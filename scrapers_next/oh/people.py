import re
import attr
from spatula import HtmlListPage, HtmlPage, CSS, URL, SelectorError
from openstates.models import ScrapePerson
import requests
import lxml.html

background_image_re = re.compile(r"background-image:url\((.*?)\)")
senate_cap_sq_re = re.compile(r"(Sen.+Building)(1.+Square)(.+)(Col.+43215)")
senate_no_cap_sq_re = re.compile(r"(Sen.+Building)(.+)(Col.+43215)")
statehouse_cap_sq_re = re.compile(r"(Statehouse)(1.+Square)(.+)(Col.+43215)")
statehouse_no_cap_sq_re = re.compile(r"(Statehouse)(.+)(Col.+43215)")


@attr.s
class LegPartial:
    name = attr.ib()
    district = attr.ib()
    party = attr.ib()
    url = attr.ib()
    image = attr.ib()
    chamber = attr.ib()
    list_page_url = attr.ib()


class LegList(HtmlListPage):
    def process_item(self, item):
        try:
            name = CSS(".media-overlay-caption-text-line-1").match_one(item).text
        except SelectorError:
            self.skip("vacant")

        if "vacant" in name.lower():
            self.skip("vacant")
        subtitle = CSS(".media-overlay-caption-text-line-2").match_one(item)
        # e.g. District 25 | D
        district, party = subtitle.text_content().split(" | ")
        district = district.split()[1]
        party = {"D": "Democratic", "R": "Republican", "I": "Independent"}[party]

        image = CSS(".media-thumbnail-image").match_one(item).get("style")
        image = background_image_re.findall(image)[0]

        return LegDetail(
            LegPartial(
                name=name,
                district=district,
                party=party,
                url=item.get("href"),
                image=image,
                chamber=self.chamber,
                list_page_url=self.source.url,
            )
        )


class LegDetail(HtmlPage):
    input_type = LegPartial

    def get_source_from_input(self):
        return self.input.url

    def process_page(self):
        # construct person from the details from above
        p = ScrapePerson(
            state="oh",
            chamber=self.input.chamber,
            district=self.input.district,
            name=self.input.name,
            party=self.input.party,
            image=self.input.image,
        )
        p.add_source(self.input.url, "member details page")
        p.add_source(self.input.list_page_url, "member list page")

        if self.input.chamber == "lower":
            # House path
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

        elif self.input.chamber == "upper":
            # Senators *may* have social media stuff...let's try to grab it
            try:
                social = CSS(".communications a[target='_blank']").match(self.root)
            except SelectorError:
                social = []

            for site in social:
                url = site.get("href").strip("/").lower()
                if "facebook" in url:
                    p.ids.facebook = (
                        url.removeprefix("https://www.facebook.com/")
                        .split("?")[0]
                        .strip("/")
                    )

                elif "twitter" in url:
                    if "https" in url:
                        twit_pref = "https://twitter.com/"
                    else:
                        twit_pref = "http://www.twitter.com/"
                    p.ids.twitter = url.removeprefix(twit_pref).split("?")[0]

                elif "youtube" in url:
                    if "user" in url:
                        p.ids.youtube = url.removeprefix(
                            "https://www.youtube.com/user/"
                        ).removesuffix("/videos")
                    elif "channel" in url:
                        p.ids.youtube = url.removeprefix(
                            "https://www.youtube.com/channel/"
                        )
                elif "instagram" in url:
                    p.ids.instagram = (
                        url.removeprefix("https://www.instagram.com/")
                        .split("?")[0]
                        .strip("/")
                    )

                else:
                    self.logger.info(f"SOCIAL NOT MATCHED: {url}")

            # Senators only have address and phone listed on Contact page
            contact_url = f"{self.input.url}/contact"
            response = requests.get(contact_url)
            content = lxml.html.fromstring(response.content)

            info_bar = content.xpath(".//div[@class='member-info-bar-value']")
            info_list = [x.text_content().strip() for x in info_bar]
            address, phone = info_list[:-1]

            p.capitol_office.voice = phone

            # Regex patterns compiled at top of file
            #  used to fix unusual and tricky spacing in address
            patterns = [
                senate_cap_sq_re,
                senate_no_cap_sq_re,
                statehouse_cap_sq_re,
                statehouse_no_cap_sq_re,
            ]
            for pattern in patterns:
                address_match = pattern.search(address)
                if address_match:
                    address = ", ".join(address_match.groups())
                    break

            p.capitol_office.address = address

        return p


class House(LegList):
    source = URL(
        "https://www.legislature.ohio.gov/legislators/house-directory", timeout=100
    )
    selector = CSS(".media-container a[target='_blank']", num_items=99)
    chamber = "lower"


class Senate(LegList):
    source = URL(
        "https://www.legislature.ohio.gov/legislators/senate-directory", timeout=100
    )
    selector = CSS(".media-container a[target='_blank']", num_items=33)
    chamber = "upper"
