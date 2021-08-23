from spatula import URL, XmlPage
from openstates.models import ScrapePerson


class Legislators(XmlPage):
    def process_page(self):
        members = self.root.getchildren()
        for member in members:
            children = member.getchildren()
            if children == []:
                continue
            elif len(children) == 3:
                # title = member.getchildren()[0].text_content().strip()
                name = member.getchildren()[1].text_content().strip()
                # link = member.getchildren()[2].text_content().strip()
            else:
                pass
                # sub_members = [children[i:i + 3] for i in range(0, len(children), 3)]
                # print(sub_members)

                # name =  member.getchildren()[0].text_content().strip()
                # link =  member.getchildren()[1].text_content().strip()

        p = ScrapePerson(
            name=name,
            state="ms",
            chamber=self.chamber,
        )
        # party=party
        # district=district
        # email=email
        # image=img

        return p


class Senate(Legislators):
    source = URL("http://billstatus.ls.state.ms.us/members/ss_membs.xml")
    chamber = "upper"


class House(Legislators):
    source = URL("http://billstatus.ls.state.ms.us/members/hr_membs.xml")
    chamber = "lower"
