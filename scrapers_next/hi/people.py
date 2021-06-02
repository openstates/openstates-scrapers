import lxml.html
from spatula import CSS, SelectorError, HtmlListPage
from ..common.people import Person, PeopleWorkflow


class FormSource:
    """ a WIP generic source for POSTing a form, and getting back results """

    def __init__(self, url, form_xpath, button_label):
        self.url = url
        self.form_xpath = form_xpath
        self.button_label = button_label

    def process_page(self, scraper):
        resp = scraper.get(self.url)
        root = lxml.html.fromstring(resp.content)
        form = root.xpath(self.form_xpath)[0]
        inputs = form.xpath(".//input")
        # build list of all of the inputs of the form, clicking the button we need to click
        data = {}
        for inp in inputs:
            name = inp.get("name")
            value = inp.get("value")
            inptype = inp.get("type")
            if inptype == "submit":
                if value == self.button_label:
                    data[name] = value
            else:
                data[name] = value

        # do second request
        resp = scraper.post(self.url, data)
        return resp.content

    def __str__(self):
        return f"FormSource('{self.url}', '{self.form_xpath}', '{self.button_label}')"


class HawaiiLegislators(HtmlListPage):
    source = FormSource(
        "https://www.capitol.hawaii.gov/members/legislators.aspx", "//form", "Show All"
    )
    selector = CSS("#ctl00_ContentPlaceHolderCol1_GridView1 tr")

    LABELS = {
        "first_name": "LabelFirst",
        "party": "LabelParty",
        "room": "LabelRoom2",
        "voice": "LabelPhone2",
        "fax": "LabelFAX2",
        "email": "HyperLinkEmail",
        "chamber": "LabelDis",
        "district": "LabelDistrict",
    }

    def process_item(self, item):
        try:
            link = CSS("a").match(item)[1]
        except SelectorError:
            self.skip()
        data = {
            "last_name": link.text_content(),
            "url": link.get("href"),
        }
        for key, label in self.LABELS.items():
            data[key] = CSS(f"[id$={label}]").match_one(item).text_content().strip()

        party = {"(D)": "Democratic", "(R)": "Republican"}[data["party"]]
        address = "Hawaii State Capitol, Room " + data["room"]
        chamber = "upper" if data["chamber"] == "S" else "lower"

        p = Person(
            name=data["first_name"] + " " + data["last_name"],
            state="hi",
            chamber=chamber,
            district=data["district"],
            given_name=data["first_name"],
            family_name=data["last_name"],
            party=party,
            email=data["email"],
        )
        p.capitol_office.address = address
        p.capitol_office.voice = data["voice"]
        p.capitol_office.fax = data["fax"]
        p.add_source(data["url"])
        p.add_link(data["url"])
        return p


all_legislators = PeopleWorkflow(HawaiiLegislators)
