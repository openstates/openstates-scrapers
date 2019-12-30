from pupa.scrape import Scraper, Organization

import lxml.html


HI_URL_BASE = "http://capitol.hawaii.gov"


def get_chamber_url(chamber):

    chamber_code = {"upper": "S", "lower": "H"}[chamber]
    URL = "%s/committees/committees.aspx?chamber=%s" % (HI_URL_BASE, chamber_code)
    return URL


class HICommitteeScraper(Scraper):
    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from self.scrape_chamber(chamber)

    def get_committee_data(self, url, org):
        list_html = self.get(HI_URL_BASE + url).text
        list_page = lxml.html.fromstring(list_html)
        chair_div = list_page.xpath(
            "//div[@id='ContentPlaceHolderCol1_PanelChair']/div"
        )
        chair = chair_div[0].xpath("//a[@id='ContentPlaceHolderCol1_HyperLinkChair']")
        vchair_div = list_page.xpath(
            "//div[@id='ContentPlaceHolderCol1_PanelViceChair']"
        )
        vice = vchair_div[0].xpath(
            "//div/a[@id='ContentPlaceHolderCol1_HyperLinkcvChair']"
        )
        members = list_page.xpath(
            "//table[@id='ContentPlaceHolderCol1_DataList1']/tr/td/a"
        )
        for i in chair:
            org.add_member(i.text_content().strip(), role="chair")
        for i in vice:
            org.add_member(i.text_content().strip(), role="vice chair")
        for i in members:
            org.add_member(i.text_content().strip(), role="member")

    def scrape_chamber(self, chamber):
        URL = get_chamber_url(chamber)
        list_html = self.get(URL).text
        list_page = lxml.html.fromstring(list_html)
        rows = list_page.xpath("//table[@id='ContentPlaceHolderCol1_GridView1']/tr")
        for row in rows:
            tds = row.xpath("./td")
            clong = tds[1]
            clong = clong.xpath("./a")[0]
            ctty_name = clong.text_content().strip()
            ctty_url = clong.get("href")
            org = Organization(
                chamber=chamber, classification="committee", name=ctty_name
            )
            org.add_source(HI_URL_BASE + ctty_url)
            self.get_committee_data(ctty_url, org)
            yield org
