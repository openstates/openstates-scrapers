from billy.scrape.legislators import LegislatorScraper, Legislator
from scrapelib import HTTPError
import lxml.html

from openstates.utils import LXMLMixin


class UTLegislatorScraper(LegislatorScraper,LXMLMixin):
    jurisdiction = 'ut'
    latest_only = True

    def scrape(self, term, chambers):
        #utah seems to have undocumented JSON!
        house_base_url = "http://le.utah.gov/house2/"
        senate_base_url = "http://senate.utah.gov/"
        json_link = "http://le.utah.gov/data/legislators.json"
        leg_json = self.get(json_link).json()
        for leg_info in leg_json["legislators"]:
            leg_name = leg_info["fullName"]
            district = leg_info["district"]
            party = {"R":"Republican",
                    "D":"Democrat"}[leg_info["party"]]
            photo_url = leg_info["image"]
            leg_id = leg_info["id"]
            
            if leg_info["house"] == "H":
                leg_url = house_base_url + "detail.jsp?i=" + leg_id
                leg = Legislator(term, 'lower', district, leg_name,
                         party=party, photo_url=photo_url, url=leg_url)
                leg.add_source(leg_url)
                leg = self.scrape_house_member(leg_url, leg)
            
            else:
                leg_url = (senate_base_url +
                        "senators/district{dist}.html".format(dist=district))
                try:
                    self.head(leg_url)
                except HTTPError:
                    warning_text = "Bad link for {sen}".format(sen=leg_name)
                    self.logger.warning(warning_text)

                    leg = Legislator(term, 'upper', district, leg_name,
                         party=party, photo_url=photo_url)
                else:
                    leg = Legislator(term, 'upper', district, leg_name,
                         party=party, photo_url=photo_url,url=leg_url)
                    leg.add_source(leg_url)

                address = leg_info["address"]
                try:
                    cell = leg_info["cell"]
                except KeyError:
                    cell = None
                email = leg_info["email"]
                leg.add_office('district', 'Home',
                    address=address, phone=cell, email=email)
                conflict_of_interest = (senate_base_url +
                        "disclosures/2015/{id}.pdf".format(id=leg_id))

                leg["links"] = [conflict_of_interest]

            leg.add_source(json_link)
            self.save_legislator(leg)

    def scrape_house_member(self, leg_url, leg):

        leg_doc = self.lxmlize(leg_url)
        email = leg_doc.xpath('//a[starts-with(@href, "mailto")]')[0].text
        address = leg_doc.xpath('//b[text()="Address:"]')[0].tail.strip()
        cell = leg_doc.xpath('//b[text()="Cell Phone:"]')
        if cell:
            cell = cell[0].tail.strip()
        else:
            cell = None

        leg.add_office('district', 'Home',
                    address=address, phone=cell, email=email)

        conflict_of_interest = leg_doc.xpath("//a[contains(@href,'CofI')]/@href")
        leg["links"] = [conflict_of_interest]

        return leg
