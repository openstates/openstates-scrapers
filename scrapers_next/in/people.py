from spatula import HtmlListPage, CSS, URL, HtmlPage
from openstates.models import ScrapePerson
import re


class NewDetailFieldEncountered(BaseException):
    pass


class BlueSenDetail(HtmlPage):
    def process_page(self):
        p = self.input

        phone_pattern = re.compile(r"\d{3}-\d{3}-\d{4}")
        try:
            title = CSS("div.fusion-title-3 h4").match_one(self.root).text_content()
            p.extras["title"] = title
        except Exception:
            pass

        details_block = CSS(
            "div.fusion_builder_column_2_5 div div div.tab-content div"
        ).match(self.root)
        info_div = CSS("p").match(details_block[0])

        p.extras["Legislative Assistant"] = info_div[1].text_content().strip()
        phones = info_div[3].text_content().strip()
        phones = phone_pattern.findall(info_div[3].text_content().strip())
        if phones:
            p.capitol_office.voice = phones[0]
        extra_num = 1
        for extra_phone in phones[1:]:
            p.extras[f"Additional Phone {extra_num}"] = extra_phone
        p.capitol_office.address = info_div[5].text_content().strip()
        """
        press_div = CSS("p").match(details_block[1])
        p.extras["Media Contact Name"] = press_div[1].text_content().strip()

        #socials = ["facebook", "instagram", "twitter", "youtube"]
        handles = {x: None for x in socials}
        patterns = {x: re.compile(rf"(.+)({x}.com/)(.+)") for x in socials}

        social_links = CSS("div .fusion-social-links a").match(self.root)
        for link in social_links:
            href = link.get("href").lower()
            for soc in socials:
                if soc in href:
                    pattern = patterns[soc]
                    raw_handle = pattern.search(href).groups()[-1]
                    handle = re.sub("/", "", raw_handle)
                    handles[soc] = handle

        if handles["facebook"]:
            p.ids.facebook = handles["facebook"]
        if handles["instagram"]:
            p.ids.instagram = handles["instagram"]
        if handles["twitter"]:
            p.ids.twitter = handles["twitter"]
        if handles["youtube"]:
            p.ids.youtube = handles["youtube"]
        """

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

        columns = CSS("div.fusion-title").match(item)
        name = CSS("h2").match_one(columns[1]).text_content()
        district = CSS("p").match_one(columns[2]).text_content()

        # special titles applied before the district name
        if "|" in district:
            district = district.split("|")[1].strip()
        district = district.strip().removeprefix("District ")
        img = CSS("div.fusion-image-element div span a img").match_one(item).get("src")

        p = ScrapePerson(
            name=name,
            state="in",
            chamber=self.chamber,
            district=district,
            party=self.party,
            image=img,
        )

        detail_link = (
            CSS("div.fusion-image-element div span a").match_one(item).get("href")
        )
        # all dem Senator emails are of a similar format, but otherwise protected from scraping
        p.email = f"s{district}@iga.in.gov"
        p.add_link(f"https://indianasenatedemocrats.org{detail_link}", note="homepage")
        p.add_source(self.source.url)
        p.add_source(detail_link)
        return BlueSenDetail(p, source=URL(detail_link, timeout=30))


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
        return RedSenDetail(p, source=URL(detail_link, timeout=30))


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

        return BlueRepDetail(p, source=URL(detail_link_full, timeout=30))


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
        p.add_source(self.source.url.split("?")[0])

        return RedRepDetail(p, source=URL(detail_link, timeout=30))


class RepublicanHouse(RedRepList):
    source = URL(
        "https://www.indianahouserepublicans.com/members/?pos=0,100,100", timeout=30
    )
    selector = CSS("div.member-list a", min_items=60, max_items=100)
    chamber = "lower"
    party = "Republican"


class DemocraticHouse(BlueRepList):
    source = URL("https://indianahousedemocrats.org/members", timeout=30)
    selector = CSS("section.member-listing a", min_items=29)
    chamber = "lower"
    party = "Democratic"


class DemocraticSenate(BlueSenList):
    source = URL("https://www.indianasenatedemocrats.org/senators/", timeout=30)
    selector = CSS(
        "div.post-content div.fusion_builder_column_1_3",
        min_items=10,
    )
    chamber = "upper"
    party = "Democratic"


class RepublicanSenate(RedSenList):
    source = URL("https://www.indianasenaterepublicans.com/senators")
    selector = CSS("div.senator-list div.senator-item", min_items=39)
    chamber = "upper"
    party = "Republican"
