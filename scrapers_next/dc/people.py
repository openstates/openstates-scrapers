from spatula import CSS, HtmlListPage, URL, HtmlPage, SelectorError
from openstates.models import ScrapePerson
import re


class CouncilDetail(HtmlPage):
    def process_page(self):
        p = self.input

        name = CSS("h1").match(self.root)[0].text_content().strip()
        p.name = name

        district = CSS("p.h4").match_one(self.root).text_content().strip()
        if re.search(r"&bullet;", district):
            district = re.search(r"&bullet;(.+)", district).groups()[0].strip()
        p.district = district

        party = CSS("ul li p").match(self.root)[1].text_content().strip()
        if re.search(r"Party", party):
            party = re.search(r"(.+)\sParty", party).groups()[0]
        p.party = party

        addr = CSS("ul li p").match(self.root)[3].text_content().strip()
        p.capitol_office.address = addr

        email = CSS("p.byline a").match(self.root)[0].text_content().strip()
        p.email = email

        phone = CSS("p.byline a").match(self.root)[1].text_content().strip()
        if re.search(r"tel:", phone):
            phone = re.search(r"tel:(.+)", phone).groups()[0]
        p.capitol_office.voice = phone

        all_text = CSS("p.byline").match_one(self.root).text_content().strip()
        fax = all_text.split("Fax: ")[1]
        p.capitol_office.fax = fax

        if len(CSS("section.aside-section a").match(self.root)) == 2:
            # no extra info
            return p
        elif len(CSS("section.aside-section a").match(self.root)) == 3:
            # just a website
            website = CSS("section.aside-section a").match(self.root)[2].get("href")
            p.extras["website"] = website
        elif len(CSS("section.aside-section a").match(self.root)) == 4:
            # just fb and twitter
            fb = CSS("section.aside-section a").match(self.root)[2].get("href")
            fb = fb.split("/")[-2]
            twitter = CSS("section.aside-section a").match(self.root)[3].get("href")
            twitter = twitter.split("/")[-1]
            p.ids.facebook = fb
            p.ids.twitter = twitter
        else:
            # website, fb, and twitter
            website = CSS("section.aside-section a").match(self.root)[2].get("href")
            p.extras["website"] = website
            fb = CSS("section.aside-section a").match(self.root)[3].get("href")
            fb = fb.split("/")
            if fb[-1] == "":
                fb = fb[-2]
            else:
                fb = fb[-1]
            twitter = CSS("section.aside-section a").match(self.root)[4].get("href")
            twitter = twitter.split("/")[-1]
            p.ids.facebook = fb
            p.ids.twitter = twitter

        return p


class CouncilList(HtmlListPage):
    source = URL("http://dccouncil.us/councilmembers/")
    selector = CSS("li.column", num_items=14)

    def process_item(self, item):
        try:
            title = CSS("h3").match_one(item).text_content()
            if title == "Chair Pro Tempore":
                # this member is listed twice. skip the 1st time
                self.skip()
        except SelectorError:
            title = None

        img = CSS("img").match_one(item).get("src")

        # use placeholders?
        p = ScrapePerson(
            name="",
            state="dc",
            party="Democratic",
            chamber="",
            district="",
            image=img,
        )

        detail_link = CSS("a").match(item)[1].get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return CouncilDetail(p, source=detail_link)
