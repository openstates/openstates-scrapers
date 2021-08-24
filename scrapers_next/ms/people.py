from spatula import URL, HtmlPage
from openstates.models import ScrapePerson
from itertools import zip_longest
from dataclasses import dataclass


@dataclass
class PartialPerson:
    name: str
    title: str
    chamber: str


# source https://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


class LegDetail(HtmlPage):
    input_type = PartialPerson

    def process_page(self):
        if self.source.url == "http://ltgovhosemann.ms.gov/":
            return None

        district = self.root.cssselect("district")[0].text_content()
        party = self.root.cssselect("party")[0].text_content()

        if party == "D":
            party = "Democratic"
        elif party == "R":
            party = "Republican"
        elif party == "I":
            party = "Independent"

        # no party listed on page
        if self.input.name in ["Lataisha Jackson", "John G. Faulkner"]:
            party = "Democratic"

        p = ScrapePerson(
            name=self.input.name,
            state="ms",
            chamber=self.input.chamber,
            district=district,
            party=party,
        )

        email = self.root.cssselect("email")[0].text_content()
        p.email = email
        img_id = self.root.cssselect("img_name")[0].text_content()
        if self.input.chamber == "upper":
            img = "http://billstatus.ls.state.ms.us/members/senate/" + img_id
        else:
            img = "http://billstatus.ls.state.ms.us/members/house/" + img_id
        p.image = img

        if self.input.title != "member":
            p.extras["title"] = self.input.title

        return p


class Legislators(HtmlPage):
    def process_page(self):
        members = self.root.getchildren()
        for member in members:
            children = member.getchildren()
            if children == []:
                continue
            elif len(children) == 3:
                title = children[0].text_content().strip()
                name = children[1].text_content().strip()
                link_id = children[2].text_content().strip()
                if link_id == "http://ltgovhosemann.ms.gov/":
                    link = link_id
                else:
                    link = "http://billstatus.ls.state.ms.us/members/" + link_id

                partial_p = PartialPerson(name=name, title=title, chamber=self.chamber)

                yield LegDetail(partial_p, source=link)
            else:
                for mem in grouper(member, 3):
                    name = mem[0].text_content().strip()
                    link_id = mem[1].text_content().strip()
                    link = "http://billstatus.ls.state.ms.us/members/" + link_id

                    partial_p = PartialPerson(
                        name=name, title="member", chamber=self.chamber
                    )

                    yield LegDetail(partial_p, source=link)


class Senate(Legislators):
    source = URL("http://billstatus.ls.state.ms.us/members/ss_membs.xml")
    chamber = "upper"


class House(Legislators):
    source = URL("http://billstatus.ls.state.ms.us/members/hr_membs.xml")
    chamber = "lower"
