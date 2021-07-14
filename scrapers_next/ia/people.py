from spatula import HtmlPage, HtmlListPage, CSS, XPath
from openstates.models import ScrapePerson


class LegDetail(HtmlPage):
    # input_type = ScrapePerson

    example_source = (
        "https://www.legis.iowa.gov/legislators/legislator?ga=89&personID=906"
    )

    def process_page(self):

        image = XPath("//img[contains(@src, '/photo')]").match_one(self.root).get("src")
        # print('hi')
        # print(image)

        p = ScrapePerson(
            name=self.input.name,
            state="ia",
            chamber=self.input.chamber,
            party=self.input.party,
            district=self.input.district,
            email=self.input.email,
            image=image,
        )

        # TODO: how to get the extra info?
        # for td in CSS(".legisIndent tr").match(self.root):
        # for each field:
        # p.extras[field[i]] =
        # table = XPath("//div[@class='legisIndent divideVert']//td[@class='col_1']")
        table = XPath("//div[@class='legisIndent divideVert']//td//text()").match(
            self.root
        )
        print("table", table)

        fields = table[0::2]
        # print('fields', fields)
        extra = table[1::2]
        # print('extra', extra)

        num_of_fields = range(len(fields))
        # print("num of fields", num_of_fields)

        for i in num_of_fields:
            p.extras[fields[i].lower()] = extra[i].strip()
            # print(fields[i],extra[i])

        return p


class LegList(HtmlListPage):
    # selector = CSS("#sortableTable tr")

    def process_item(self, item):

        __, name, district, party, county, email = item.getchildren()
        url = CSS("a").match(item)[0].get("href")

        # print(name.text_content(), district.text_content(), party.text_content(), county.text_content(), email.text_content())

        p = ScrapePerson(
            name=name.text_content(),
            state="ia",
            chamber=self.chamber,
            party=party.text_content(),
            district=district.text_content(),
            email=email.text_content(),
        )
        # todo: this source isn't included in the final :(
        p.add_source(self.source.url)
        # url = XPath("//a[contains(@href, 'personID')]").match_one(name).get("src")

        return LegDetail(p, source=url)


class SenList(LegList):
    source = "https://www.legis.iowa.gov/legislators/senate"
    chamber = "upper"
    selector = CSS("#sortableTable tbody tr")


# class RepList(LegList):
#     source = "https://www.legis.iowa.gov/legislators/house"
#     chamber = "lower"
