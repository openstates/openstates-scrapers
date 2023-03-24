import attr
from spatula import HtmlListPage, HtmlPage, XPath, CSS, SelectorError
from openstates.models import ScrapePerson


@attr.s(auto_attribs=True)
class PartialMember:
    name: str
    url: str
    chamber: str = ""


class LegDetail(HtmlPage):
    example_source = (
        "https://www.arkleg.state.ar.us/Legislators/Detail?"
        "member=B.+Ballinger&ddBienniumSession=2023%2F2023R"
    )

    def process_page(self):

        table_div = CSS(".col-md-7").match(self.root)[0]

        rows = CSS(".row").match(table_div)

        party = ""
        name_party = CSS("h1").match_one(self.root).text_content()

        if name_party.endswith("(R)"):
            party = "Republican"
        elif name_party.endswith("(D)"):
            party = "Democrat"
        elif name_party.endswith("(I)"):
            party = "Independent"
        elif name_party.endswith("(G)"):
            party = "Green"

        image = CSS(".MemberPhoto").match_one(self.root).get("src")

        table = {
            "Phone:": "",
            "Email:": "",
            "District:": "",
            "Seniority:": "",
            "Occupation:": "",
            "Church Affiliation:": "",
            "Veteran:": "",
            "Public Service:": "",
            "Biography:": "",
        }

        for row in rows:
            try:
                type = CSS(".col-md-3").match_one(row).text_content()
                info = CSS(".col-md-9").match_one(row).text_content().strip()
                if type == "Biography:":
                    info = CSS(".col-md-9 a").match_one(row).get("href")
                if type in table:
                    table[type] = info
            except SelectorError:
                pass

        p = ScrapePerson(
            name=self.input.name,
            state="ar",
            chamber=self.input.chamber,
            party=party,
            image=image,
            district=table["District:"],
            email=table["Email:"],
        )

        if table["Biography:"] != "":
            p.add_link(table["Biography:"], "Biography")

        for key in table:
            if (
                key == "Phone:"
                or key == "Email:"
                or key == "District:"
                or key == "Biography:"
            ):
                continue
            elif table[key] != "":
                # remove the colon at the end
                p.extras[key[:-1].lower()] = table[key]
        try:
            address = CSS(".col-md-12 p b").match_one(self.root).text_content()
            full_address = address[:-5] + "AR " + address[-5:]
            p.district_office.address = full_address
        except SelectorError:
            pass

        p.add_source(self.source.url)
        p.add_source(self.input.url)

        return p


class LegList(HtmlListPage):
    source = (
        "https://www.arkleg.state.ar.us/Legislators/List?"
        "sort=Type&by=desc&ddBienniumSession=2023%2F2023R#SearchResults"
    )
    selector = XPath(
        "//div[@role='grid']"
        "//div[contains(@class, 'row')]"
        "//div[@class='col-md-6']"
    )

    def process_item(self, item):
        chamber_name = (
            item.text_content()
            .replace("\r\n", "")
            .strip()
            .replace("                                        ", "   ")
            .split("   ")
        )

        chamber = chamber_name[0]

        name = chamber_name[1].replace("  ", " ")
        if "resigned" in name.lower():
            self.skip()

        if chamber == "Senator":
            chamber = "upper"
        elif chamber == "Representative":
            chamber = "lower"

        source = item.getchildren()[0].get("href")
        p = PartialMember(name=name, chamber=chamber, url=self.source.url)

        return LegDetail(p, source=source)


class SenDetail(HtmlPage):
    example_source = (
        "https://senate.arkansas.gov/senators/missy-irvin/"
    )

    def process_page(self):
        rows = XPath("//div[contains(@class,col-md-8)]/ul/li").match(self.root[0])

        image_container = CSS(".col-md-4").match(self.root)[0]
        image = XPath("//img[contains(@alt, '" + self.input.name + "')]").match(image_container)[0].get('src')
        image = image.split("?")[0]

        biocontainer = CSS(".panel-body").match(self.root)[0]
        bio = XPath("//a/@href").match(biocontainer)[0]
        committees = XPath("//div[contains(@class,base-text)]/ul/li").match(self.root)

        table = {
            "Party": "",
            "Phone": "",
            "Email": "",
            "District": "",
            "Seniority": "",
            "Occupation": "",
            "District Address": "",
            "Church Affiliation:": "",
            "Veteran": "",
            "Public Service": "",
            "Legislative Service": "",
            "Biography": "",
        }

        for row in rows:
            try:
                text = row.text_content()
                text = text.split(": ")
                if len(text) < 2:
                    continue
                item_name = text[0]
                value = text[1]
                table[item_name] = value
                if item_name == "Legislative Service":
                    if value[0] != "H":
                        value = value.replace('House', '; House')
                    table[item_name] = value
                    break

            except SelectorError:
                pass

        table["Biography"] = bio

        p = ScrapePerson(
            name=self.input.name,
            state="ar",
            chamber=self.input.chamber,
            party=table["Party"],
            image=image,
            district=table["District"],
            email=table["Email"],
        )

        committees_string = ""
        first_committee = True
        for c in committees:
            found = False
            for k in table.keys():
                if c.text_content().find(k) >= 0:
                    found = True
            if not found:
                if not first_committee:
                    committees_string += ", "
                committees_string += c.text_content().lower()
                first_committee = False
        p.extras["Committees"] = committees_string

        if table["District Address"] != "":
            address = table["District Address"]
            full_address = address[:-5] + "AR " + address[-5:]
            p.district_office.address = full_address
        if table["Phone"] != "":
            p.district_office.voice = table["Phone"]
        if table["Biography"] != "":
            p.add_link(table["Biography"], "Biography")

        for key in table:
            if (
                key == "Phone"
                or key == "Email"
                or key == "District"
                or key == "Biography"
            ):
                continue
            elif table[key] != "":
                # remove the colon at the end
                p.extras[key.lower()] = table[key]
        p.district_office.address = table["District Address"]
        p.add_source(self.source.url)
        p.add_source(self.input.url)

        return p


class SenList(HtmlListPage):
    source = (
        "https://senate.arkansas.gov/senators/senators-sorted-by-congressional-district-and-seniority/"
    )
    selector = XPath(
        "//div[contains(@class,'col-sm-6')]"
    )
    chamber = "upper"

    def process_item(self, item):
        description = item.text_content()
        nameFromDescription = description.split("\r\n")[2]
        link = list(item.iterlinks())
        (element, attr, url, position) = link[1]
        p = PartialMember(name=nameFromDescription, chamber="upper", url=self.source.url)
        return SenDetail(p, source=url)


class AssemblyDetail(HtmlPage):
    example_source = (
        "https://www.arkansashouse.org/district/1"
    )

    def process_page(self):
        heading = CSS(".py-sm-6").match(self.root)[0]
        name = self.input.name
        line2 = heading[2].text_content().split(" ")
        party = line2[0]
        districtName = line2[2]
        districtNumber = ""
        for c in districtName:
            if c.isdigit():
                districtNumber += c

        leftInfobox = CSS(".col-lg-3").match(self.root)[0]

        table = {
            "Seniority": "",
            "Occupation": "",
            "Religion": "",
            "Past Service": "",
        }

        for k in table.keys():
            value = XPath("//dt[. = '" + k + "']//following-sibling::dd").match(leftInfobox)[0]
            valueString = value.text_content()
            if len(valueString) > 0:
                table[k] = valueString

        table["Name"] = name
        table["District"] = districtNumber
        table["Title"] = "Representative"
        table["Party"] = party

        image = XPath("//div[contains(@class,'col-lg-3')]//a/@href").match(self.root)[0]

        emailContainer = XPath("//p[contains(@class,'mb-0')]/a").match(self.root)[0]
        table["Email"] = emailContainer.text_content()

        officeContainer = XPath("//p[contains(@class,'mb-0')]").match(self.root)[1]
        table["Phone"] = officeContainer[2].text_content()
        addressArray = XPath("//p[contains(@class,'mb-0')]/text()").match(self.root)

        address = ""
        started = False
        for c in addressArray[3]:
            if c.isalnum():
                started = True
            if started:
                address += c
        address += " "
        address += addressArray[4]
        table["District Address"] = address

        p = ScrapePerson(
            name=name,
            state="ar",
            chamber=self.input.chamber,
            party=table["Party"],
            image=image,
            district=table["District"],
            email=table["Email"],
        )
        p.add_source(self.source.url)
        p.add_source(self.input.url)

        for key in table:
            if (
                key == "Phone"
                or key == "Name"
                or key == "Email"
                or key == "District"
                or key == "Biography"
                or key == "District Address"
                or key == "Phone"
            ):
                continue
            elif table[key] != "":
                # remove the colon at the end
                p.extras[key.lower()] = table[key]

        if table["District Address"] != "":
            p.district_office.address = table["District Address"]
        if table["Phone"] != "":
            p.district_office.voice = table["Phone"]
        return p


class AssemblyList(HtmlListPage):
    source = (
        "https://www.arkansashouse.org/representatives/members"
    )
    selector = XPath(
        "//div[contains(@class,'col-sm-6')]"
    )
    chamber = "lower"

    def process_item(self, item):
        description = item.text_content()
        nameFromDescription = description.split("\n")[6].strip()
        link = list(item.iterlinks())
        (element, attr, url, position) = link[0]
        p = PartialMember(name=nameFromDescription, chamber="lower", url=self.source.url)
        return AssemblyDetail(p, source=url)
