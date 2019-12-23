import json

from pupa.scrape import Person, Scraper

from openstates.utils import LXMLMixin


class VTPersonScraper(Scraper, LXMLMixin):
    CHAMBERS = {"Senator": "upper", "Representative": "lower"}

    def scrape(self, session=None):
        if session is None:
            session = self.latest_session()

        year_slug = self.jurisdiction.get_year_slug(session)

        # Load all members via the private API
        legislator_dump_url = "http://legislature.vermont.gov/people/loadAll/{}".format(
            year_slug
        )
        json_data = self.get(legislator_dump_url).text
        legislators = json.loads(json_data)["data"]

        # Parse the information from each legislator
        for info in legislators:
            # Strip whitespace from strings
            info = {k: v.strip() for k, v in info.items()}

            # Skip duplicate record for Christopher Mattos (appointed Rep September 2017)
            if info["PersonID"] == "29034":
                self.info("skipping first Christopher Mattos record")
                continue

            # Gather photo URL from the member's page
            member_url = "http://legislature.vermont.gov/people/single/{}/{}".format(
                year_slug, info["PersonID"]
            )
            page = self.lxmlize(member_url)
            (photo_url,) = page.xpath('//img[@class="profile-photo"]/@src')

            # Also grab their state email address
            state_email = page.xpath(
                '//dl[@class="summary-table profile-summary"]/'
                'dt[text()="Email"]/following-sibling::dd[1]/a/text()'
            )
            if state_email:
                (state_email,) = state_email
            else:
                state_email = None

            district = info["District"].replace(" District", "")

            leg = Person(
                primary_org=self.CHAMBERS[info["Title"]],
                district=district,
                party=info["Party"].replace("Democrat", "Democratic"),
                name="{0} {1}".format(info["FirstName"], info["LastName"]),
                image=photo_url,
            )

            leg.add_contact_detail(
                note="Capitol Office",
                type="address",
                value="Vermont State House\n115 State Street\nMontpelier, VT 05633",
            )
            if state_email:
                leg.add_contact_detail(
                    note="Capitol Office", type="email", value=state_email
                )

            leg.add_contact_detail(
                note="District Office",
                type="address",
                value="{0}{1}\n{2}, {3} {4}".format(
                    info["MailingAddress1"],
                    (
                        "\n" + info["MailingAddress2"]
                        if info["MailingAddress2"].strip()
                        else ""
                    ),
                    info["MailingCity"],
                    info["MailingState"],
                    info["MailingZIP"],
                ),
            )
            if info["HomePhone"]:
                leg.add_contact_detail(
                    note="District Office", type="voice", value=info["HomePhone"]
                )
            district_email = info["Email"] or info["HomeEmail"] or info["WorkEmail"]
            if district_email:
                leg.add_contact_detail(
                    note="District Office", type="email", value=district_email
                )

            leg.add_link(member_url)

            leg.add_source(legislator_dump_url)
            leg.add_source(member_url)

            yield leg
