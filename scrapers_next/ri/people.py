import re
from spatula import HtmlListPage, CSS, XPath
from ..common.people import ScrapePerson


class LegList(HtmlListPage):
    def process_item(self, item):
        name = (
            CSS("td")
            .match(item)[1]
            .text_content()
            .strip()
            .lstrip(r"[Senator\s|Rep.\s]")
        )
        district = CSS("td").match(item)[0].text_content()
        email = CSS("td").match(item)[2].text_content()

        p = ScrapePerson(
            name=name,
            state="ri",
            party="Democratic",
            district=district,
            chamber=self.chamber,
        )

        bio = CSS("td center a").match_one(item).get("href")
        image = self.image(bio)
        p.image = image

        p.email = email
        p.add_link(bio)
        p.add_source(self.source.url, note="Contact Web Page")
        p.add_source(self.url, note="Detail Excel Source")

        # image = self.get_image(name)
        # p.image = image

        return p

    def image(self, bio):
        # if re.search("ciccon", bio):
        # print(bio)
        img = bio.strip(r"(\/default\.aspx)$")
        # print(img)
        last_name = img.split("/")[-1]
        # print(last_name)
        img = img.rstrip(last_name)
        # print(img)
        img += "Pictures/"
        # print(img)
        img += last_name
        # print(img)
        img += ".jpg"
        # print(img)

        # something weird is happening with Ciccone
        # Rep. Mary Ann Shallcross Smith
        return img

    def get_image(self, name):
        if self.chamber == "upper":
            img = "https://www.rilegislature.gov/senators/Pictures/"
        else:
            img = "https://www.rilegislature.gov/representatives/Pictures/"

        last_name = name.split()
        if len(last_name) > 3 or re.search(",", name):
            print(last_name)
            return ""

        last_name = last_name[-1].lower()
        # does not work for
        # Frank A. Ciccone III
        # Walter S. Felag Jr.
        # Jessica de la Cruz
        # Frank Lombardo, III
        # Rep. Joseph J. Solomon, Jr.
        # Rep. Robert E. Craven, Sr.
        # Rep. Edward T. Cardillo, Jr.
        # Rep. Mary Ann Shallcross Smith

        img += last_name
        img += ".jpg"
        return img


class AssemblyList(LegList):
    source = "http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=75)
    chamber = "lower"
    url = "http://www.rilegislature.gov/SiteAssets/MailingLists/Representatives.xls"


class SenList(LegList):
    source = "http://webserver.rilegislature.gov/Email/SenEmailListDistrict.asp"
    selector = XPath("//tr[@valign='TOP']", num_items=38)
    chamber = "upper"
    url = "http://www.rilegislature.gov/SiteAssets/MailingLists/Senators.xls"
