import lxml
from scrapelib import HTTPError

HI_URL_BASE = "https://data.capitol.hawaii.gov"
SHORT_CODES = f"{HI_URL_BASE}/legislature/committees.aspx?chamber=all"


def get_short_codes(scraper):
    scraper.short_ids = {
        "STF": {
            "chamber": "lower",
            "name": "Simplifying Permitting for Enhanced Economic Development (SPEED) Task Force",
        }
    }

    try:
        list_html = scraper.get(SHORT_CODES, verify=False).text
        list_page = lxml.html.fromstring(list_html)
        rows = list_page.xpath("//table[contains(@id, 'MainContent_GridView1')]//tr")
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
    except HTTPError:
        # In case this page goes down (as it currently is 2/11/26), a hardcoded 2026 list
        scraper.short_ids = {
            "STF": {
                "chamber": "lower",
                "name": "Simplifying Permitting for Enhanced Economic Development (SPEED) Task Force",
            },
            "AEN": {
                "chamber": "upper",
                "name": "Senate Committee on Agriculture and Environment",
            },
            "AGR": {
                "chamber": "lower",
                "name": "House Committee onAgriculture & Food Systems",
            },
            "CAA": {
                "chamber": "lower",
                "name": "House Committee on Culture & Arts",
            },
            "CPC": {
                "chamber": "lower",
                "name": "House Committee on Consumer Protection & Commerce",
            },
            "CPN": {
                "chamber": "upper",
                "name": "Senate Committee on Commerce and Consumer Protection",
            },
            "ECD": {
                "chamber": "lower",
                "name": "House Committee on Economic Development & Technology",
            },
            "EDN": {
                "chamber": "lower",
                "name": "House Committee on Education",
            },
            "EDT": {
                "chamber": "upper",
                "name": "Senate Committee on Economic Development and Tourism",
            },
            "EDU": {
                "chamber": "upper",
                "name": "Senate Committee on Education",
            },
            "EEP": {
                "chamber": "lower",
                "name": "House Committee on Energy & Environmental Protection",
            },
            "EIG": {
                "chamber": "upper",
                "name": "Senate Committee on Energy and Intergovernmental Affairs",
            },
            "FIN": {
                "chamber": "lower",
                "name": "House Committee on Finance",
            },
            "GVO": {
                "chamber": "upper",
                "name": "Senate Committee on Government Operations",
            },
            "HED": {
                "chamber": "lower",
                "name": "House Committee on Higher Education",
            },
            "HHS": {
                "chamber": "upper",
                "name": "Senate Committee on Health and Human Services",
            },
            "HLT": {
                "chamber": "lower",
                "name": "House Committee on Health",
            },
            "HOU": {
                "chamber": "upper",
                "name": "Senate Committee on Housing",
            },
            "HSG": {
                "chamber": "lower",
                "name": "House Committee on Housing",
            },
            "HSH": {
                "chamber": "lower",
                "name": "House Committee on Human Services & Homelessness",
            },
            "HWN": {
                "chamber": "upper",
                "name": "Senate Committee on Hawaiian Affairs",
            },
            "JDC": {
                "chamber": "upper",
                "name": "Senate Committee on Judiciary",
            },
            "JHA": {
                "chamber": "lower",
                "name": "House Committee on Judiciary & Hawaiian Affairs",
            },
            "LAB": {
                "chamber": "lower",
                "name": "House Committee on Labor",
            },
            "LBT": {
                "chamber": "upper",
                "name": "Senate Committee on Labor and Technology",
            },
            "LMG": {
                "chamber": "lower",
                "name": "House Committee on Legislative Management",
            },
            "PBS": {
                "chamber": "lower",
                "name": "House Committee on Public Safety",
            },
            "PSM": {
                "chamber": "upper",
                "name": "Senate Committee on Public Safety and Military Affairs",
            },
            "TOU": {
                "chamber": "lower",
                "name": "House Committee on Tourism",
            },
            "TRN": {
                "chamber": "lower",
                "name": "House Committee on Transportation",
            },
            "TRS": {
                "chamber": "upper",
                "name": "Senate Committee on Transportation",
            },
            "WAL": {
                "chamber": "lower",
                "name": "House Committee on Water & Land",
            },
            "WAM": {
                "chamber": "upper",
                "name": "Senate Committee on Ways and Means",
            },
            "WLA": {
                "chamber": "upper",
                "name": "Senate Committee on Water, Land, Culture and the Arts",
            },
        }


def make_data_url(url: str) -> str:
    if "www" in url:
        return url.replace("www.", "data.")
    elif "http" not in url:
        return f"{HI_URL_BASE}{url}"
    else:
        return url.replace("capitol.", "data.capitol.")
