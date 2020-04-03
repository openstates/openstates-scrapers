from scrapelib import HTTPError
from scrapers.utils import LXMLMixin
from openstates.scrape import Person, Scraper


class UTPersonScraper(Scraper, LXMLMixin):
    def scrape(self):
        PARTIES = {"R": "Republican", "D": "Democratic"}
        representative_url = "http://house.utah.gov/rep/{}"
        senator_url = "http://senate.utah.gov/senators/district{}.html"

        json_link = "http://le.utah.gov/data/legislators.json"
        person_json = self.get(json_link).json()

        for info in person_json["legislators"]:
            chamber = "lower" if info["house"] == "H" else "upper"

            person = Person(
                name=info["formatName"],
                district=info["district"],
                party=PARTIES[info["party"]],
                image=info["image"],
                primary_org=chamber,
            )

            person.add_source(json_link)
            if chamber == "lower":
                link = representative_url.format(info["id"])
            else:
                link = senator_url.format(info["district"])
            try:
                self.head(link)
            except HTTPError:
                self.logger.warning("Bad URL for {}".format(info["formatName"]))
            else:
                person.add_link(link)

            address = info.get("address")
            email = info.get("email")
            fax = info.get("fax")

            # Work phone seems to be the person's non-legislative
            # office phone, and thus a last option
            # For example, we called one and got the firm
            # where he's a lawyer. We're picking
            # them in order of how likely we think they are
            # to actually get us to the person we care about.
            phone = info.get("cell") or info.get("homePhone") or info.get("workPhone")

            if address:
                person.add_contact_detail(
                    type="address", value=address, note="District Office"
                )
            if phone:
                person.add_contact_detail(
                    type="voice", value=phone, note="District Office"
                )
            if email:
                person.add_contact_detail(
                    type="email", value=email, note="District Office"
                )
            if fax:
                person.add_contact_detail(type="fax", value=fax, note="District Office")

            BASE_FINANCE_URL = "http://www.disclosures.utah.gov/Search/PublicSearch"
            conflicts_of_interest = info.get("CofI") or []
            finance_reports = info.get("FinanceReport") or []
            extra_links = []
            for conflict in conflicts_of_interest:
                extra_links.append(conflict["url"])
            for finance in finance_reports:
                # Some links are just to the base disclosure website
                # Presumably, these members don't yet have their forms up
                if finance != BASE_FINANCE_URL:
                    extra_links.append(finance["url"])
            if extra_links:
                person.extras["links"] = extra_links

            yield person
