import json
from openstates_core.scrape import Person, Scraper


class NVPeopleScraper(Scraper):
    def scrape(self, chamber=None):
        session = self.latest_session()
        if chamber:
            yield from self.scrape_chamber(chamber, session)
        else:
            yield from self.scrape_chamber("upper", session)
            yield from self.scrape_chamber("lower", session)

    def scrape_chamber(self, chamber, session):

        if chamber == "upper":
            chamber_slug = "Senate"
        elif chamber == "lower":
            chamber_slug = "Assembly"
        session_slug = self.jurisdiction.session_slugs[session]

        leg_base_url = "http://www.leg.state.nv.us/App/Legislator/A/%s/%s/" % (
            chamber_slug,
            session_slug,
        )
        leg_json_url = (
            "http://www.leg.state.nv.us/App/Legislator/A/api/%s/Legislator?house=%s"
            % (session_slug, chamber_slug)
        )

        resp = json.loads(self.get(leg_json_url).text)
        for item in resp:
            # empty district
            empty_names = ["District No", "Vacant"]
            if any(name in item["FullName"] for name in empty_names):
                continue
            last, first = item["FullName"].split(",", 1)
            item["FullName"] = "{first} {last}".format(last=last, first=first).strip()
            person = Person(
                name=item["FullName"],
                district=item["DistrictNbr"],
                party=item["Party"],
                primary_org=chamber,
                image=item["PhotoURL"],
            )
            leg_url = leg_base_url + item["DistrictNbr"]

            # hack to get the legislator ID
            html = self.get(leg_url).text
            for l in html.split("\n"):
                if "GetLegislatorDetails" in l:
                    leg_id = l.split(",")[1].split("'")[1]

            # fetch the json used by the page
            leg_details_url = (
                "https://www.leg.state.nv.us/App/Legislator/A/api/{}/Legislator?id=".format(
                    session_slug
                )
                + leg_id
            )
            leg_resp = json.loads(self.get(leg_details_url).text)
            details = leg_resp["legislatorDetails"]

            address = details["Address1"]
            address2 = details["Address2"]
            if address2:
                address += " " + address2
            address += "\n%s, NV %s" % (details["City"], details["Zip"])

            phone = details["LCBPhone"]
            email = details["LCBEmail"]
            if address:
                person.add_contact_detail(
                    type="address", value=address, note="District Office"
                )
            if phone:
                person.add_contact_detail(
                    type="voice", value=phone, note="District Office"
                )
            if phone:
                person.add_contact_detail(
                    type="email", value=email, note="District Office"
                )
            person.add_link(leg_details_url)
            person.add_source(leg_details_url)
            yield person
