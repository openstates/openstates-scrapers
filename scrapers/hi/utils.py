import lxml

HI_URL_BASE = "https://www.capitol.hawaii.gov"
SHORT_CODES = f"{HI_URL_BASE}/legislature/committees.aspx?chamber=all"


def get_short_codes(scraper):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/79.0.3945.117 Safari/537.36",
        "referer": HI_URL_BASE,
        "authority": "www.capitol.hawaii.gov",
    }

    list_html = scraper.get(SHORT_CODES, headers=headers, verify=False, timeout=30).text
    list_page = lxml.html.fromstring(list_html)
    rows = list_page.xpath("//*[@id='MainContent_GridView1']//tr")
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
