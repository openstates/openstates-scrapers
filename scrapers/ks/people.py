import json

import scrapelib
from openstates.scrape import Person, Scraper

from . import ksapi
from utils import LXMLMixin


class KSPersonScraper(Scraper, LXMLMixin):
    def scrape(self, session=None, chamber=None):
        if session is None:
            session = self.latest_session()
        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        content = json.loads(self.get(ksapi.url + "members/").text)["content"]
        if "upper" in chambers:
            for member in content["senate_members"]:
                yield from self.get_member(session, "upper", member["KPID"])
        if "lower" in chambers:
            for member in content["house_members"]:
                yield from self.get_member(session, "lower", member["KPID"])

    def get_member(self, session, chamber, kpid):
        url = "%smembers/%s" % (ksapi.url, kpid)
        content = json.loads(self.get(url).text)["content"]

        party = content["PARTY"]
        if party == "Democrat":
            party = "Democratic"

        slug = {
            "2013-2014": "b2013_14",
            "2015-2016": "b2015_16",
            "2017-2018": "b2017_18",
            "2019-2020": "b2019_20",
        }[session]
        leg_url = "http://www.kslegislature.org/li/%s/members/%s/" % (slug, kpid)

        try:
            legislator_page = self.lxmlize(leg_url)
            (photo_url,) = legislator_page.xpath('//img[@class="profile-picture"]/@src')
        except scrapelib.HTTPError:
            self.warning(
                "{}'s legislator bio page not found".format(content["FULLNAME"])
            )
            leg_url = ""
            photo_url = ""

        person = Person(
            name=content["FULLNAME"],
            district=str(content["DISTRICT"]),
            primary_org=chamber,
            party=party,
            image=photo_url,
        )
        person.extras = {"occupation": content["OCCUPATION"]}

        address = "\n".join(
            [
                "Room {}".format(content["OFFICENUM"]),
                "Kansas State Capitol Building",
                "300 SW 10th St.",
                "Topeka, KS 66612",
            ]
        )

        note = "Capitol Office"
        person.add_contact_detail(type="address", value=address, note=note)
        person.add_contact_detail(type="email", value=content["EMAIL"], note=note)
        if content["OFFPH"]:
            person.add_contact_detail(type="voice", value=content["OFFPH"], note=note)

        person.add_source(url)
        person.add_link(leg_url)

        yield person
