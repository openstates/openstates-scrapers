from scrapelib import HTTPError
from openstates.utils import LXMLMixin
from pupa.scrape import Person, Scraper


class UTPersonScraper(Scraper, LXMLMixin):
    latest_only = True

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(self, chamber):
        house_base_url = "http://le.utah.gov/house2/"
        senate_base_url = "http://senate.utah.gov/"

        # utah seems to have undocumented JSON!
        json_link = "http://le.utah.gov/data/legislators.json"
        person_json = self.get(json_link).json()

        for person_info in person_json["legislators"]:
            person_name = person_info["formatName"]
            district = person_info["district"]
            party = {
                "R": "Republican",
                "D": "Democrat",
            }[person_info["party"]]
            photo_url = person_info["image"]
            person_id = person_info["id"]

            if person_info["house"] == "H":
                person_url = house_base_url + "detail.jsp?i=" + person_id
                person = Person(name=person_name, district=district, party=party,
                                primary_org='lower', image=photo_url)
                person.add_link(person_url)
                person.add_source(person_url)
                person = self.scrape_house_member(person_url, person)
            else:
                person_url = (senate_base_url +
                              "senators/district{dist}.html".format(dist=district))
                try:
                    self.head(person_url)
                except HTTPError:
                    warning_text = "Bad link for {sen}".format(sen=person_name)
                    self.logger.warning(warning_text)

                    person = Person(name=person_name, district=district, party=party,
                                    primary_org='upper', image=photo_url)
                else:
                    person = Person(name=person_name, district=district, party=party,
                                    primary_org='upper', image=photo_url)
                    person.add_link(person_url)
                    person.add_source(person_url)

                address = person_info.get('address', None)
                fax = person_info.get('fax', None)
                cell = person_info.get('cell', None)
                home_phone = person_info.get('homePhone', None)
                work_phone = person_info.get('workPhone', None)

                # Work phone seems to be the person's non-legislative
                # office phone, and thus a last option
                # For example, we called one and got the firm
                # where he's a lawyer. We're picking
                # them in order of how likely we think they are
                # to actually get us to the person we care about.
                phone = (cell or home_phone or work_phone)

                email = person_info.get('email', None)

                if address:
                    person.add_contact_detail(type='address', value=address,
                                              note='District Office')
                if phone:
                    person.add_contact_detail(type='voice', value=phone, note="District Office")
                if email:
                    person.add_contact_detail(type='email', value=email, note='District Office')
                if fax:
                    person.add_contact_detail(type='fax', value=fax, note="District Office")

                conflict_of_interest = (senate_base_url +
                                        "disclosures/2015/{id}.pdf".format(id=person_id))

                person.extras["links"] = [conflict_of_interest]

            person.add_source(json_link)
            yield person

    def scrape_house_member(self, person_url, person):
        # JSON is complete for senators, not for reps
        # so we still have to hit the rep's page
        # to get office info

        person_doc = self.lxmlize(person_url)
        email = person_doc.xpath('//a[starts-with(@href, "mailto")]')[0].text
        address = person_doc.xpath('//b[text()="Address:"]')[0].tail.strip()
        cell = person_doc.xpath('//b[text()="Cell Phone:"]')
        work_phone = person_doc.xpath('//b[text()="Work Phone:"]')
        home_phone = person_doc.xpath('//b[text()="Home Phone:"]')
        fax = person_doc.xpath('//b[text()="Fax:"]')

        cell = cell[0].tail.strip() if cell else None
        work_phone = work_phone[0].tail.strip() if work_phone else None
        home_phone = home_phone[0].tail.strip() if home_phone else None
        fax = fax[0].tail.strip() if fax else None

        phone = (cell or home_phone or work_phone)
        if address:
            person.add_contact_detail(type='address', value=address, note='District Office')
        if phone:
            person.add_contact_detail(type='voice', value=phone, note="District Office")
        if email:
            person.add_contact_detail(type='email', value=email, note='District Office')
        if fax:
            person.add_contact_detail(type='fax', value=fax, note="District Office")

        conflict_of_interest = person_doc.xpath("//a[contains(@href,'CofI')]/@href")
        person.extras["links"] = conflict_of_interest

        return person
