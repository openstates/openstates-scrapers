from spatula import HtmlPage, HtmlListPage, XPath, URL
from openstates.models import ScrapeCommittee


def fix_name(name):
    # handles cases like Watson, Jr., Clovis
    if ", " not in name:
        return name
    last, first = name.rsplit(", ", 1)
    return first + " " + last


class HouseComList(HtmlPage):
    source = "https://www.myfloridahouse.gov/Sections/Committees/committees.aspx"
    selector = XPath("//a[contains(@href, 'committeesdetail.aspx')]")

    def process_page(self):
        # don't use list page because we need to look back at prior element
        parent = None
        chamber = "lower"

        for item in self.selector.match(self.root):
            cssclass = item.attrib.get("class", "")
            name = item.text_content().strip()

            if "parentcommittee" in cssclass:
                parent = None
                chamber = "lower"

            comm = ScrapeCommittee(
                name=name, classification="committee", chamber=chamber, parent=parent
            )
            yield HouseComDetail(comm, source=item.attrib["href"])

            # parent for next time
            if "parentcommittee" in cssclass:
                parent = comm._id
                chamber = None


class HouseComDetail(HtmlPage):
    def clean_name(self, name):
        name = name.replace(" [D]", "")
        name = name.replace(" [R]", "")
        name = name.replace(" [I]", "")
        name = name.strip()
        name = fix_name(name)
        return name

    def process_page(self):
        name = self.root.xpath('//h1[@class="ribbon"]')[0].text

        for lm in self.root.xpath('//div[@class="member-card"]'):
            role = lm.xpath('.//div[@class="portrait-title"]')[0].text_content().strip()
            name = (
                lm.xpath('.//div[@class="portrait-title"]/a')[0].text_content().strip()
            )
            name = self.clean_name(name)
            self.input.add_member(name, role=role)

        for cm in self.root.xpath('//div[@class="portrait-title"]//a'):
            name = self.clean_name(cm.text_content())
            self.input.add_member(name)

        self.input.add_source(self.source.url)

        yield self.input


class SenComList(HtmlListPage):
    source = URL("https://www.flsenate.gov/Committees/", verify=False)
    selector = XPath("//a[contains(@href, 'Committees/Show')]/@href")

    def process_item(self, item):
        return SenComDetail(source=item)


class SenComDetail(HtmlPage):
    def clean_name(self, member):
        member = member.replace("Senator ", "").strip()
        member = member.replace(" (D)", "")
        member = member.replace(" (R)", "")
        member = member.replace(" (I)", "")
        member = fix_name(member)
        return member

    def process_page(self):
        name = self.root.xpath('//h2[@class="committeeName"]')[1].text
        if name.startswith("Appropriations Subcommittee"):
            return
            # TODO: restore scraping of Appropriations Subcommittees
            # name = name.replace('Appropriations ', '')
            # parent = {'name': 'Appropriations', 'classification': 'upper'}
            # chamber = None
        else:
            if name.startswith("Committee on"):
                name = name.replace("Committee on ", "")
            parent = None
            chamber = "upper"
        comm = ScrapeCommittee(
            name=name, classification="committee", chamber=chamber, parent=parent
        )

        for dt in self.root.xpath('//div[@id="members"]/dl/dt'):
            role = dt.text.replace(": ", "").strip().lower()
            member = dt.xpath("./following-sibling::dd")[0].text_content()
            member = self.clean_name(member)
            comm.add_member(member, role=role)

        for ul in self.root.xpath('//div[@id="members"]/ul/li'):
            member = self.clean_name(ul.text_content())
            comm.add_member(member)

        comm.add_source(self.source.url)

        return comm
