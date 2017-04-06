from pupa.scrape import Scraper, Organization

import lxml.html


HI_URL_BASE = "http://capitol.hawaii.gov"



def get_chamber_url(chamber):

    chambers_code = {'upper': 'S', 'lower': 'H'}[chamber]
    URL = "%s/committees/committees.aspx?chamber=%s" % (HI_URL_BASE, chamber_code)
    return URL

class HICommitteeScraper(Scraper):

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def scrape_chamber(chamber):
        URL = get_chamber_url(chamber)
        list_html = scraper.get(URL).text
        list_page = lxml.html.fromstring(list_html)
        rows = list_page.xpath("//table[@id='ctl00_ContentPlaceHolderCol1_GridView1']/tr")
        scraper.short_ids = {
            "CONF": {
                "chamber": "joint",
                "name": "Conference Committee",
            },
        }

        for row in rows:
            tds = row.xpath("./td")
            short = tds[0]
            clong = tds[1]
            chamber = clong.xpath("./span")[0].text_content()
            clong = clong.xpath("./a")[0]
            short_id = short.text_content().strip()
            ctty_name = clong.text_content().strip()
            chamber = "joint"
            if "house" in chamber.lower():
                chamber = 'lower'
            elif "senate" in chamber.lower():
                chamber = 'upper'
