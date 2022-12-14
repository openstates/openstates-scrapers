import re
import attr
from spatula import HtmlListPage, HtmlPage, CSS, URL
from openstates.models import ScrapePerson

background_image_re = re.compile(r"background-image:url\((.*?)\)")


@attr.s
class LegPartial:
    name = attr.ib()
    district = attr.ib()
    party = attr.ib()
    url = attr.ib()
    image = attr.ib()
    chamber = attr.ib()


class Senate(HtmlListPage):
    source = URL(
        "https://www.legislature.ohio.gov/legislators/senate-directory", timeout=30
    )
    selector = CSS(".mediaGrid a[target='_blank']", num_items=33)

    def process_item(self, item):
        name = CSS(".mediaCaptionTitle").match_one(item).text

        if name == "Vacant":
            self.skip("vacant")
        subtitle = CSS(".mediaCaptionSubtitle").match_one(item).text
        image = CSS(".photo").match_one(item).get("style")
        image = background_image_re.findall(image)[0]
        # e.g. District 25 | D
        district, party = subtitle.split(" | ")
        district = district.split()[1]
        party = {"D": "Democratic", "R": "Republican", "I": "Independent"}[party]

        return LegDetail(
            LegPartial(
                name=name,
                district=district,
                party=party,
                url=item.get("href"),
                chamber="upper",
                image=image,
            )
        )


class House(HtmlListPage):
    source = URL(
        "https://www.legislature.ohio.gov/legislators/house-directory", timeout=30
    )
    selector = CSS(".mediaGrid a[target='_blank']", num_items=99)

    def process_item(self, item):
        name = CSS(".mediaCaptionTitle").match_one(item).text

        if name == "Vacant":
            self.skip("vacant")
        subtitle = CSS(".mediaCaptionSubtitle").match_one(item).text
        image = CSS(".photo").match_one(item).get("style")
        image = background_image_re.findall(image)[0]
        # e.g. District 25 | D
        district, party = subtitle.split(" | ")
        district = district.split()[1]
        party = {"D": "Democratic", "R": "Republican", "I": "Independent"}[party]

        return LegDetail(
            LegPartial(
                name=name,
                district=district,
                party=party,
                url=item.get("href"),
                image=image,
                chamber="lower",
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
        p.add_source(self.input.url)
        p.add_link(self.input.url)

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
            """
                2022-07-18:
                 <div class="generalInfoModule">

                <div class="name">
                    Senator Rob McColley
                </div>

                <div class="address">
                    <span>Senate Building<br />1 Capitol Square<br />2nd Floor</span>
                    <div>Columbus, OH  43215</div>
                </div>

                <div class="hometown">
                    Hometown: Napoleon
                </div>

                <div class="phone">
                    <span>(614) 466-8150</span>
                </div>

                <div class="email">
                    <a href='../senators/mccolley/contact'>Email Senator McColley</a>
                </div>

                <div class='quickConnectModule'><div class='quickConnectLabel'>Connect:</div><div class='quickConnectLabelLinks'><a target='_blank' href='https://www.facebook.com/McColley4Ohio/'><img src='../Assets/Global/SocialMedia/Facebook.png' /></a><a target='_blank' href='https://twitter.com/Rob_McColley?lang=en'><img src='../Assets/Global/SocialMedia/Twitter.png' /></a><a target='_blank' href='https://www.youtube.com/user/ohiosenategop/videos'><img src='../Assets/Global/SocialMedia/YouTube.png' /></a></div></div>

            </div>
            """
            # Senate path

            # Senators *may* have social media stuff...let's try to grab it
            try:
                social = CSS(
                    ".quickConnectModule .quickConnectLabelLinks a[target='_blank']"
                ).match(self.root)
            except Exception:
                social = []
            for site in social:
                url = site.get("href").strip("/")
                if "facebook" in url:
                    p.ids.facebook = (
                        url.removeprefix("https://www.facebook.com/")
                        .split("?")[0]
                        .strip("/")
                    )
                elif "twitter" in url:
                    p.ids.twitter = url.removeprefix("https://twitter.com/").split("?")[
                        0
                    ]
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
            phone = (
                CSS(".generalInfoModule div.phone span")
                .match_one(self.root)
                .text_content()
            )
            p.capitol_office.voice = phone
            address1 = (
                CSS(".generalInfoModule div.address span")
                .match_one(self.root)
                .text_content()
            )
            address2 = (
                CSS(".generalInfoModule div.address div")
                .match_one(self.root)
                .text_content()
            )
            # <br /> turns into nothing, so we get some weird spacing...
            p.capitol_office.address = f"{address1} {address2}"

            hometown = (
                CSS(".generalInfoModule div.hometown")
                .match_one(self.root)
                .text_content()
                .strip()
                .removeprefix("Hometown: ")
            )
            p.extras["hometown"] = hometown

        return p
