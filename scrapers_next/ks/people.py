"""
2022-07-14: KS Leg site does not support HTTPS
"""
from spatula import JsonPage, URL
from openstates.models import ScrapePerson


class Legislators(JsonPage):
    source = "http://www.kslegislature.org/li/api/v11/rev-1/members/"

    def process_page(self):
        for member in (
            self.data["content"]["house_members"]
            + self.data["content"]["senate_members"]
        ):
            # source is a URL object, we need the .url member
            yield MembersDetail(
                source=URL(self.source.url + member["KPID"] + "/", timeout=10)
            )


class MembersDetail(JsonPage):
    example_source = (
        "http://www.kslegislature.org/li/api/v11/rev-1/members/sen_thompson_mike_1/"
    )

    def process_page(self):
        content = self.data["content"]
        party = content["PARTY"]
        name = content["FULLNAME"]
        district = content["DISTRICT"]
        occupation = content["OCCUPATION"]
        email = content["EMAIL"]
        phone = content["OFFPH"]
        title = content["JEMEMBFULLSHORT"].split()[0]
        chamber = "upper" if title == "Senator" else "lower"

        if party == "Democrat":
            party = "Democratic"

        address = "; ".join(
            [
                "Room {}".format(content["OFFICENUM"]),
                "Kansas State Capitol Building",
                "300 SW 10th St.",
                "Topeka, KS 66612",
            ]
        )

        leg_url = f"http://www.kslegislature.org/li/b2021_22/members/{content['KPID']}/"
        image_url = (
            f"http://www.kslegislature.org/li/m/images/pics/{content['KPID']}.jpg"
        )

        person = ScrapePerson(
            name=name,
            state="ks",
            party=party,
            district=district,
            chamber=chamber,
            email=email,
            image=image_url,
        )
        person.capitol_office.voice = phone
        person.capitol_office.address = address
        person.add_source(self.source.url)
        person.add_link(leg_url)
        if occupation:
            person.extras = {"occupation": occupation}
        return person
