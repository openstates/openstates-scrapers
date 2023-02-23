from spatula import HtmlListPage, JsonListPage, HtmlPage, CSS
from openstates.models import ScrapePerson
import requests
import lxml.html
import re


class UnexpectedImageError(BaseException):
    def __init__(self, img_src):
        super().__init__(f"Unexpected img src format {img_src}")


class FamilyNameMatchError(BaseException):
    def __init__(self, family_name):
        super().__init__(f"Family name '{family_name}' found in multiple src")


def get_gop_senate_images(url):
    """
    Helper function called at the initialization of Senate() class.

    Takes in the `url` string for the MI Senate Republicans, processes photos
    of each member listed on the homepage, and returns a dictionary: `images`.

    The keys of the dict are modified versions the member's names extracted
    from the `alt` attribute of the `<img>` elements.

    The corresponding values are the `src` attribute of the `<img>` elements.
    """
    source = url
    response = requests.get(source)
    content = lxml.html.fromstring(response.content)

    images = {}
    for img in content.xpath(".//img"):
        raw_alt = img.get("alt")
        if "Senator" in raw_alt:
            alt_name_split = raw_alt.replace("Senator ", "").split()

            #   Thomas A. Albert --> thalbert
            #   Ed McBroom --> edmcbroom
            alt = f"{(alt_name_split[0][0:2] + alt_name_split[-1]).lower()}"
            images[alt] = img.get("src")
    return images


# TODO: utilize below prior work as documentation to write solution for getting
#  image url paths for all Democratic House members
"""
**Note: the below work attempted to parse JSON data containing the HTML that is
ultimately rendered by JavaScript on the page at path `dem_url` below.**

To be added in initialization of House():

    dem_url = "https://housedems.com/members/"
    dem_images = get_dem_house_images(dem_url)

This was failed attempt at finding the src for each member image:

    for img_src in self.dem_images:
        if p.family_name.lower() in img_src.lower():
            p.image = img_src
            break
    if not p.image:
        logging.warning(f"No image for {p.name}")


def get_dem_house_images(url):
    first_response = requests.get(url)
    first_page = lxml.html.fromstring(first_response.content)
    links = first_page.xpath(".//link")
    second_url = ""
    for link in links:
        href = link.get("href")
        if "wp/v2/pages/" in href:
            second_url = href
            break
    second_response = requests.get(second_url)
    second_page = second_response.json()
    rendered = second_page["content"]["rendered"]
    raw_urls = [x for x in rendered.split() if ".jpg" in x]
    http_re = # pattern grabbing srcs that start http and end .jpg
    images = set()
    for raw_url in raw_urls:
        match = http_re.match(raw_url)
        if match:
            images.add(raw_url)
    return images


This helper function was called in an attempt to more simply get img src from
individual member pages, but does not work in many cases due to inconsistencies
across these pages:

def get_member_dem_house_image(url):
    response = requests.get(url)
    content = lxml.html.fromstring(response.content)
    image_div = content.xpath(".//div[@class='background background-image']")[0]
    image = image_div.get("style")
    return image
"""


def split_name(name):
    """
    Helper function called in House().

    Takes in the name string for member, and returns a dictionary with
    key-value pairs for "given_name", "family_name", and "name" attributes
    to be stored in ScrapePerson() object.
    """
    commas = name.count(",")
    if commas == 0:
        first, last = name.split(" ", 1)  # special case for one legislator right now
    elif commas == 1:
        last, first = name.split(", ")
    else:
        raise ValueError(name)

    if re.search("Dr.", first):
        first = re.sub("Dr.", "", first)

    return {"given_name": first, "family_name": last, "name": f"{first} {last}"}


# def ord_suffix(str_num):
#     num = int(str_num) % 100
#     if 4 <= num <= 20:
#         return "th"
#     return {1: "st", 2: "nd", 3: "rd"}.get(num % 10, "th")


class DemSenateMemberImage(HtmlPage):
    """
    Gets `<img>` `src` attribute for member photo from member's bio page.
    """

    example_source1 = "https://senatedems.com/geiss/bio/"

    def process_page(self):
        p = self.input
        member_img = self.root.xpath(".//img")[1]
        img_src = member_img.get("src")
        if "wp-content/uploads/sites" not in img_src:
            raise UnexpectedImageError(img_src)
        p.image = img_src
        return p


class Senate(JsonListPage):
    source = "https://senate.michigan.gov/senators/SenatorData.json"

    sen_gop_url = "https://www.misenategop.com"
    gop_images = get_gop_senate_images(sen_gop_url)

    def process_item(self, item):
        p = ScrapePerson(
            state="mi",
            chamber="upper",
            name=f"{item['firstName']} {item['lastName']}",
            given_name=item["firstName"],
            family_name=item["lastName"],
            email=item["email"] if item.get("email") else "",
            party="Democratic" if item["party"] == "D" else "Republican",
            district=item["district"],
        )

        p.capitol_office.address = (
            f"{item['address']} Building, " f"201 Townsend St, Lansing, MI 48933"
        )
        p.capitol_office.voice = item["phone"]

        p.add_link(item["website"], note="Member Page")
        if item.get("contactURL"):
            p.add_link(item["contactURL"], "Member Contact Page")

        p.add_source(self.source.url, note="Members List JSON Data Page")
        p.add_source(
            "https://senate.michigan.gov/senators/senatorinfo_list.html",
            note="Members List HTML page",
        )

        if "senatedems" in item["website"]:
            return DemSenateMemberImage(p, source=f"{item['website']}/bio/")
        else:
            # Creates name key to match key created in get_gop_senate_images()
            name_key = f"{(p.given_name[0:2] + p.family_name).lower()}"
            p.image = self.sen_gop_url + self.gop_images[f"{name_key}"]

        return p


class GOPHouseMemberPhotos(HtmlPage):
    """
    Example sources range in format including:
        https://www.house.mi.gov/repdetail/repGregoryAlexander
        http://repbeeler.com
        https://gophouse.org/member/repandrewbeeler/posts
    """

    gop_class = "rounded w-25 h-25"

    def process_page(self):
        p = self.input
        try:
            image_elem = self.root.xpath(f".//img[@class='{self.gop_class}']")[0]
        except IndexError:
            image_elem = self.root.xpath(f".//img[contains(@alt, '{p.family_name}')]")[
                0
            ]
        img = image_elem.get("src")
        p.image = img
        return p


class House(HtmlListPage):
    source = "https://www.house.mi.gov/AllRepresentatives"
    selector = CSS("#allreps .list-item", num_items=110)
    office_names = {
        "SHOB": "South House Office Building",
        "NHOB": "North House Office Building",
        "CB": "Capitol Building",
    }

    def process_item(self, item):
        if "vacant" in item.text_content().lower():
            self.skip("vacant")

        link = ""
        url = ""
        try:
            link = item.xpath("./div[1]/div/a")[0]
            url = item.xpath("./div[1]/div/a")[0].get("href")
        except IndexError:
            link = item.xpath("./div[1]/div/div")[0]
        finally:
            (
                name,
                party,
                district,
            ) = re.match(r"\s+([^\(]+)\((\w+)\)\s+District-(\d+)", link.text).groups()

        contact = item.getchildren()[1].getchildren()[0:3]
        office = contact[0].text_content().strip()
        phone = contact[1].text_content().strip()
        email = contact[2].text_content().strip()

        # Editing the office strings so that they match with what's on legislators' page
        office_prefix = office.split(" ")[0]
        office_suffix = office.split("-")[-1]
        if office_prefix == "SHOB" or office_prefix == "NHOB":
            office_prefix = office_prefix[0]
            office = office_prefix + "-" + office_suffix + " House Office Building"
        else:
            office = office_prefix + "-" + office_suffix

        p = ScrapePerson(
            **split_name(name),
            state="mi",
            chamber="lower",
            district=district,
            party=party,
            email=email,
        )

        if url.startswith("http:/r"):
            url = url.replace("http:/", "http://")
        p.add_source(url, "Member Details Page")
        p.add_source(self.source.url, "Members List Page")
        p.capitol_office.voice = phone
        p.capitol_office.address = office

        if p.party == "Democratic":
            return p
        else:
            return GOPHouseMemberPhotos(p, source=url)
