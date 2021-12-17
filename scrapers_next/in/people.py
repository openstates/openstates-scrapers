from spatula import HtmlListPage, XPath, CSS, URL, HtmlPage  # , SelectorError
from openstates.models import ScrapePerson
import re


class BlueSenDetail(HtmlPage):
    def process_page(self):
        p = self.input

        titles = CSS("h2").match(self.root)
        if len(titles) > 9:
            title = titles[0].text_content()
            p.extras["title"] = title

        assistant = (
            CSS("div .fusion-text.fusion-text-2 p").match(self.root)[0].text_content()
        )
        assistant = re.search(r"Legislative Assistant:\s(.+)", assistant).groups()[0]

        phones = (
            CSS("div .fusion-text.fusion-text-2 p").match(self.root)[1].text_content()
        )
        phone1, phone2 = re.search(
            r"Phone:\s(\d{3}-\d{3}-\d{4})\s\|\s(.+)", phones
        ).groups()

        media_contact = (
            CSS("div .fusion-text.fusion-text-2 p").match(self.root)[3].text_content()
        )
        media_contact_name, media_contact_email = re.search(
            r"Media Contact:\s(\w+\s\w+)\s\|\s(.+)", media_contact
        ).groups()
        addr = (
            XPath("//div/div[3]/div/div[2]/div/div[1]/text()")
            .match(self.root)[0]
            .strip()
        )

        twitter = CSS("div .fusion-social-links a").match(self.root)[0].get("href")
        twitter_id = re.search(r"https://twitter\.com/(.+)", twitter).groups()[0]

        fb = CSS("div .fusion-social-links a").match(self.root)[1].get("href")
        fb_id = (
            re.search(r"https://(www\.)?facebook\.com/(.+)", fb).groups()[1].rstrip("/")
        )

        p.capitol_office.address = addr
        p.capitol_office.voice = phone1
        p.extras["second phone"] = phone2

        p.extras["assistant"] = assistant
        p.extras["media contact name"] = media_contact_name
        p.extras["media contact email"] = media_contact_email

        p.ids.twitter = twitter_id
        p.ids.facebook = fb_id

        return p


class RedSenDetail(HtmlPage):
    def process_page(self):
        p = self.input

        email = CSS("div.sen-contact a").match(self.root)[0].get("href")
        email = re.search(r"mailto:(.+)", email).groups()[0]
        p.email = email

        addr = CSS("div.sen-contact p").match(self.root)[0].text_content()

        # no phone for this link
        if self.source.url == "https://www.indianasenaterepublicans.com/young":
            addr = addr
            phone1 = None
            phone2 = None
        else:
            addr, phone1, phone2 = re.search(
                r"(.+)Phone:\s(\d{3}-\d{3}-\d{4})\s?or\s(\d{3}-\d{3}-\d{4})", addr
            ).groups()

        p.capitol_office.address = addr
        if phone1:
            p.capitol_office.voice = phone1
        if phone2:
            p.extras["second phone"] = phone2

        if len(CSS("div.sen-contact p").match(self.root)) == 1:
            leg_assist = CSS("div.sen-contact p").match_one(self.root).text_content()
        else:
            leg_assist = CSS("div.sen-contact p").match(self.root)[1].text_content()

        if len(CSS("div.sen-contact p").match(self.root)) < 3:
            extra_contacts = leg_assist.split("Media Contact:")
            leg_assist = extra_contacts[0]
            media_contact = extra_contacts[1]
            leg_assist_name, leg_assist_phone, leg_assist_email = re.search(
                r"Legislative\sAssistant:?(.+)Phone:\s(.+)Email:\s(.+)", leg_assist
            ).groups()
            media_contact_name, media_contact_phone, media_contact_email = re.search(
                r"(.+)Phone:\s(.+)Email:\s(.+)", media_contact
            ).groups()
        elif (
            len(CSS("div.sen-contact p").match(self.root)) == 3
            or self.source.url == "https://www.indianasenaterepublicans.com/bray"
        ):
            leg_assist_name, leg_assist_phone, leg_assist_email = re.search(
                r"Legislative\sAssistant:?(.+)Phone:\s(.+)Email:\s(.+)", leg_assist
            ).groups()
            media_contact = CSS("div.sen-contact p").match(self.root)[2].text_content()
            media_contact_name, media_contact_phone, media_contact_email = re.search(
                r"Media\sContact:(.+)Phone:\s(.+)Email:\s(.+)", media_contact
            ).groups()
        else:
            leg_assist_name, leg_assist_phone, leg_assist_email = re.search(
                r"Legislative\sAssistant:?(.+)Phone:\s(.+)Email:\s(.+)", leg_assist
            ).groups()
            media_contact = CSS("div.sen-contact p").match(self.root)[3].text_content()
            media_contact_name, media_contact_phone, media_contact_email = re.search(
                r"Media\sContact:(.+)Phone:\s(.+)Email:\s(.+)", media_contact
            ).groups()

        p.extras["legislative assistant name"] = leg_assist_name
        p.extras["legislative assistant phone"] = leg_assist_phone
        p.extras["legislative assistant email"] = leg_assist_email
        p.extras["media contact name"] = media_contact_name
        p.extras["media contact phone"] = media_contact_phone
        p.extras["media contact email"] = media_contact_email

        """
        try:
            # need to deal with multi-lines of education
            print(
                XPath("//h3[contains(text(), 'Education')]")
                .match(self.root)[0]
                .getnext()
                .text_content()
            )
        except SelectorError:
            pass
        """

        return p


class BlueRepDetail(HtmlPage):
    def process_page(self):
        p = self.input
        assistant_info = (
            CSS("aside section p").match(self.root)[0].text_content().split("\n")
        )
        assist_name = assistant_info[1]
        assist_phone1 = assistant_info[2]
        assist_phone2 = assistant_info[3]
        assist_addr1 = assistant_info[4]
        assist_addr2 = assistant_info[5]
        assist_addr = assist_addr1 + " " + assist_addr2

        p.extras["assistant name"] = assist_name
        p.extras["assistant phone1"] = assist_phone1
        p.extras["assistant phone2"] = assist_phone2
        p.extras["assistant address"] = assist_addr

        return p


class BlueSenList(HtmlListPage):
    def process_item(self, item):
        name = CSS("div a").match(item)[1].text_content()
        district = (
            CSS("div .esg-content.eg-senators-grid-element-1")
            .match_one(item)
            .text_content()
            .split("|")[1]
            .strip()
            .lower()
        )
        district = re.search(r"district\s(\d+)", district).groups()[0]
        img = CSS("div img").match_one(item).get("data-lazysrc")

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district=district,
            party=self.party,
            image=img,
        )

        city = (
            CSS("div .esg-content.eg-senators-grid-element-27")
            .match_one(item)
            .text_content()
        )
        p.extras["city"] = city

        detail_link = CSS("div a").match(item)[1].get("href")
        p.add_link(detail_link, note="homepage")
        p.add_source(self.source.url)
        p.add_source(detail_link)
        return BlueSenDetail(p, source=detail_link)


class RedSenList(HtmlListPage):
    def process_item(self, item):
        name = CSS("h3").match_one(item).text_content()
        district = CSS("p.list-district").match_one(item).text_content()
        district = re.search(r"District\s(\d+)", district).groups()[0]

        img = CSS("img").match_one(item).get("src")

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district=district,
            party=self.party,
            image=img,
        )

        if len(CSS("p").match(item)) > 2:
            title = CSS("p").match(item)[0].text_content()
            p.extras["title"] = title

        detail_link = CSS("a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")
        return RedSenDetail(p, source=detail_link)


class BlueRepList(HtmlListPage):
    def process_item(self, item):
        name = CSS("header").match_one(item).text_content()
        district = CSS("div.district").match_one(item).text_content()
        district = re.search(r"House\sDistrict\s(\d+)", district).groups()[0]

        img = CSS("img").match_one(item).get("src")

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district=district,
            party=self.party,
            image=img,
        )

        p.extras["city"] = CSS("div.city").match_one(item).text_content()

        detail_link = item.get("href")
        p.add_link(detail_link, note="homepage")
        detail_link_full = detail_link + "/full"
        p.add_source(detail_link_full)

        p.add_source(self.source.url)

        return BlueRepDetail(p, source=detail_link_full)


class RedRepDetail(HtmlPage):
    def process_page(self):
        p = self.input

        district = CSS("div.hidden-xs.mem-info h3").match_one(self.root).text_content()
        title, district = re.search(r"(.+)\s\|\sDistrict\s(\d+)", district).groups()
        p.district = district
        if title != "Representative":
            p.extras["title"] = title

        assistant = CSS("div.hidden-xs.mem-info a").match(self.root)[0]
        assistant_name = assistant.text_content()
        assistant_email = assistant.get("href")
        assistant_email = re.search(r"mailto:(.+)", assistant_email).groups()[0]
        assistant_phones = (
            CSS("div.hidden-xs.mem-info p.no-margin").match(self.root)[1].text_content()
        )
        phone1, phone2 = re.search(r"Phone:\s(.+)\s\|\s(.+)", assistant_phones).groups()

        p.extras["assistant name"] = assistant_name
        p.extras["assistant email"] = assistant_email
        p.extras["assistant phone1"] = phone1
        p.extras["assistant phone2"] = phone2

        press_name = (
            CSS("div.hidden-xs.mem-info div.small-block.last p")
            .match(self.root)[0]
            .text_content()
        )
        press_phone = (
            CSS("div.hidden-xs.mem-info div.small-block.last p")
            .match(self.root)[1]
            .text_content()
        )
        press_phone = re.search(r"Phone:\s(.+)", press_phone).groups()[0]
        press_email = (
            CSS("div.hidden-xs.mem-info div.small-block.last a")
            .match_one(self.root)
            .text_content()
        )

        p.extras["press contact name"] = press_name
        p.extras["press contact phone"] = press_phone
        p.extras["press contact email"] = press_email

        return p


class RedRepList(HtmlListPage):
    def process_item(self, item):
        name = CSS("h2").match_one(item).text_content()
        img = CSS("img").match_one(item).get("src")

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district="",
            party=self.party,
            image=img,
        )

        detail_link = item.get("href")
        p.add_link(detail_link, note="homepage")
        p.add_source(detail_link)
        p.add_source(self.source.url)

        return RedRepDetail(p, source=URL(detail_link, timeout=10))


class RepublicanHouse(RedRepList):
    source = URL("https://www.indianahouserepublicans.com/members/", timeout=10)
    selector = CSS("div.member-list a", num_items=30)
    chamber = "lower"
    party = "Republican"


class DemocraticHouse(BlueRepList):
    source = URL("https://indianahousedemocrats.org/members")
    selector = CSS("section.member-listing a", num_items=29)
    chamber = "lower"
    party = "Democratic"


class DemocraticSenate(BlueSenList):
    source = URL("https://www.indianasenatedemocrats.org/senators/")
    selector = CSS(
        "article ul li",
        num_items=11,
    )
    chamber = "upper"
    party = "Democratic"


class RepublicanSenate(RedSenList):
    source = URL("https://www.indianasenaterepublicans.com/senators")
    selector = CSS("div.senator-list div.senator-item", num_items=39)
    chamber = "upper"
    party = "Republican"
