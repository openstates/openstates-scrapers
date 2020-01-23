import lxml

HI_URL_BASE = "https://capitol.hawaii.gov"
SHORT_CODES = "%s/committees/committees.aspx?chamber=all" % (HI_URL_BASE)

def get_short_codes(scraper):
    list_html = scraper.get(SHORT_CODES).text
    list_page = lxml.html.fromstring(list_html)
    rows = list_page.xpath("//table[@id='ctl00_ContentPlaceHolderCol1_GridView1']/tr")
    scraper.short_ids = {"CONF": {"chamber": "joint", "name": "Conference Committee"}}

    for row in rows:
        tds = row.xpath("./td")
        short = tds[0]
        clong = tds[1]
        chamber = clong.xpath("./span")[0].text_content()
        clong = clong.xpath("./a")[0]
        short_id = short.text_content().strip()
        ctty_name = clong.text_content().strip()
        if "house" in chamber.lower():
            chamber = "lower"
        elif "senate" in chamber.lower():
            chamber = "upper"
        else:
            chamber = "joint"
        scraper.short_ids[short_id] = {"chamber": chamber, "name": ctty_name}
