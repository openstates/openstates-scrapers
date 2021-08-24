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

        # party=party
        # district=district

        # email=email
        # image=img

        p = ScrapePerson(
            name=self.input.name,
            state="ms",
            chamber=self.input.chamber,
        )

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
                link = children[2].text_content().strip()

                partial_p = PartialPerson(name=name, title=title, chamber=self.chamber)

                yield LegDetail(partial_p, source=link)
            else:
                for mem in grouper(member, 3):
                    name = mem[0].text_content().strip()
                    link = mem[1].text_content().strip()

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
