
import lxml.html

from billy.scrape.legislators import LegislatorScraper, Legislator
from apiclient import ApiClient
from requests import exceptions


class INLegislatorScraper(LegislatorScraper):
    jurisdiction = 'in'

    def get_with_increasing_timeout(self,link,kwargs={}):
        timeout_length = 2
        html = None
        while timeout_length < 65 and html is None:
            try:
                html = self.get(link,timeout=timeout_length,**kwargs)
            except exceptions.ConnectTimeout:
                old_length = timeout_length
                timeout_length **= 2
                self.logger.debug("Timed out after {now} seconds, increasing to {next} and trying again".format(now=old_length,next=timeout_length))
            else:
                return html

            raise AssertionError("Link {} failed after waiting over a minute, giving up.")



    def scrape(self, chamber, term):
        base_url = "https://iga.in.gov/legislative"
        api_base_url = "https://api.iga.in.gov/2015"
        client = ApiClient(self)
        t = next((item for item in self.metadata["terms"] if item["name"] == term),None)
        session = max(t["sessions"])
        chamber_name = "Senate" if chamber == "upper" else "House"
        r = client.get("chamber_legislators",session=session,chamber=chamber_name)
        all_pages = client.unpaginate(r)
        for leg in all_pages:
            print leg
            firstname = leg["firstName"]
            lastname = leg["lastName"]
            party = leg["party"]
            link = leg["link"]
            api_link = api_base_url+link
            html_link = base_url+link.replace("legislators/","legislators/legislator_")
            html = self.get_with_increasing_timeout(html_link,{"verify":False})
            doc = lxml.html.fromstring(html.text)
            doc.make_links_absolute(html_link)
            address, phone = doc.xpath("//address")
            address = address.text_content().strip()
            phone = phone.text_content().strip()
            district = doc.xpath("//span[@class='district-heading']")[0].text.lower().replace("district","").strip()
            legislator = Legislator(term,
                                    chamber,
                                    district,
                                    " ".join([firstname,lastname]),
                                    firstname=firstname,
                                    lastname=lastname,
                                    party=party)
            legislator.add_source(html_link)
            legislator.add_source(api_link,note="Requires API key")
            self.save_legislator(legislator)


