from spatula import URL, CsvListPage
from openstates.models import ScrapePerson


class Legislators(CsvListPage):
    source = URL("http://gencourt.state.nh.us/downloads/members.txt")

    def process_item(self, item):
        for line in item.values():
            member = line.split("\t")

            lastname = member[0]
            firstname = member[1]
            middlename = member[2]
            name = firstname + " " + middlename + " " + lastname

            legislativebody = member[3]
            if legislativebody == "H":
                chamber = "lower"
            elif legislativebody == "S":
                chamber = "upper"

            district = member[6]
            party = member[15]

            p = ScrapePerson(
                name=name,
                state="nh",
                chamber=chamber,
                district=district,
                party=party,
            )

            address = member[8]
            address2 = member[9]
            city = member[10]
            zipcode = member[11]
            full_addr = (
                address + " " + address2 + " " + city + ", New Hampshire" + zipcode
            )
            p.district_office.address = full_addr

            phone = member[13]
            p.district_office.voice = phone

            email = member[14]
            p.email = email

            gendercode = member[16]
            p.extras["gender code"] = gendercode
            title = member[17]
            p.extras["title"] = title
            county = member[5]
            p.extras["county"] = county

            yield p
