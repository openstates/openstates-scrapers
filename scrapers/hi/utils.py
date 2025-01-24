import lxml

HI_URL_BASE = "https://data.capitol.hawaii.gov"
SHORT_CODES = f"{HI_URL_BASE}/legislature/committees.aspx?chamber=all"


def get_short_codes(scraper):
    list_html = scraper.get(SHORT_CODES, verify=False).text
    list_page = lxml.html.fromstring(list_html)
    rows = list_page.xpath("//table[contains(@id, 'MainContent_GridView1')]//tr")
    scraper.short_ids = {"CONF": {"chamber": "joint", "name": "Conference Committee"}}

    for row in rows:
        tds = row.xpath("./td")
        short = tds[0].xpath("./a")[0]
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


def make_data_url(url: str) -> str:
    if "www" in url:
        return url.replace("www.", "data.")
    else:
        return url.replace("capitol.", "data.capitol.")
