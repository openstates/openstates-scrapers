
import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator
from apiclient import ApiClient
from .utils import get_with_increasing_timeout
import scrapelib


class INLegislatorScraper(LegislatorScraper):
    jurisdiction = 'in'

    def scrape(self, chamber, term):
        client = ApiClient(self)
        t = next((item for item in self.metadata["terms"] if item["name"] == term),None)
        session = max(t["sessions"])
        base_url = "http://iga.in.gov/legislative"
        api_base_url = "https://api.iga.in.gov"
        chamber_name = "Senate" if chamber == "upper" else "House"
        r = client.get("chamber_legislators",session=session,chamber=chamber_name)
        all_pages = client.unpaginate(r)
        for leg in all_pages:
            firstname = leg["firstName"]
            lastname = leg["lastName"]
            party = leg["party"]
            link = leg["link"]
            api_link = api_base_url+link
            html_link = base_url+link.replace("legislators/","legislators/legislator_")
            try:
                html = get_with_increasing_timeout(self,html_link,fail=True,kwargs={"verify":False})
            except scrapelib.HTTPError:
                self.logger.warning("Legislator's page is not available.")
                continue
            doc = lxml.html.fromstring(html.text)
            doc.make_links_absolute(html_link)
            address, phone = doc.xpath("//address")
            address = address.text_content().strip()
            address = "\n".join([l.strip() for l in address.split("\n")])
            phone = phone.text_content().strip()
            district = doc.xpath("//span[@class='district-heading']")[0].text.lower().replace("district","").strip()
            image_link = base_url+link.replace("legislators/","portraits/legislator_")
            legislator = Legislator(term,
                                    chamber,
                                    district,
                                    " ".join([firstname,lastname]),
                                    party=party,
                                    photo_url = image_link)
            legislator.add_office('capitol', 'Capitol Office', address=address,
                           phone=phone)
            legislator.add_source(html_link)
            legislator.add_source(api_link)
            self.save_legislator(legislator)


