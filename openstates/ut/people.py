from billy.scrape.legislators import LegislatorScraper, Legislator
from scrapelib import HTTPError
import lxml.html
from openstates.utils import LXMLMixin


class UTLegislatorScraper(LegislatorScraper,LXMLMixin):
    jurisdiction = 'ut'
    latest_only = True

    def scrape(self, term, chambers):
        house_base_url = "http://le.utah.gov/house2/"
        senate_base_url = "http://senate.utah.gov/"

        #utah seems to have undocumented JSON!
        json_link = "http://le.utah.gov/data/legislators.json"
        leg_json = self.get(json_link).json()

        for leg_info in leg_json["legislators"]:
            leg_name = leg_info["formatName"]
            district = leg_info["district"]
            party = {
                "R":"Republican",
                "D":"Democrat",
            }[leg_info["party"]]
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

                address = leg_info.get('address', None)
                fax = leg_info.get('fax', None)
                cell = leg_info.get('cell', None)
                home_phone = leg_info.get('homePhone', None)
                work_phone = leg_info.get('workPhone', None)

                #Work phone seems to be the person's non-legislative
                #office phone, and thus a last option
                #For example, we called one and got the firm
                #where he's a lawyer. We're picking
                #them in order of how likely we think they are
                #to actually get us to the person we care about.
                phone = (cell or home_phone or work_phone)

                email = leg_info.get('email', None)

                leg.add_office('district', 'Home',
                    address=address, phone=phone, email=email, fax=fax)
                conflict_of_interest = (senate_base_url +
                    "disclosures/2015/{id}.pdf".format(id=leg_id))

                leg['links'] = [conflict_of_interest]

            leg.add_source(json_link)
            self.save_legislator(leg)

    def scrape_house_member(self, leg_url, leg):
        #JSON is complete for senators, not for reps
        #so we still have to hit the rep's page
        #to get office info

        leg_doc = self.lxmlize(leg_url)
        email = leg_doc.xpath('//a[starts-with(@href, "mailto")]')[0].text
        address = leg_doc.xpath('//b[text()="Address:"]')[0].tail.strip()
        cell = leg_doc.xpath('//b[text()="Cell Phone:"]')
        work_phone = leg_doc.xpath('//b[text()="Work Phone:"]')
        home_phone = leg_doc.xpath('//b[text()="Home Phone:"]')
        fax = leg_doc.xpath('//b[text()="Fax:"]')
        
        cell = cell[0].tail.strip() if cell else None
        work_phone = work_phone[0].tail.strip() if work_phone else None
        home_phone = home_phone[0].tail.strip() if home_phone else None
        fax = fax[0].tail.strip() if fax else None

        phone = (cell or home_phone or work_phone)
        leg.add_office('district', 'Home',
                    address=address, phone=phone, email=email, fax=fax)

        conflict_of_interest = leg_doc.xpath("//a[contains(@href,'CofI')]/@href")
        leg["links"] = conflict_of_interest

        return leg
