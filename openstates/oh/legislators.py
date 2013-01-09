import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


JOINT_COMMITTEE_OVERRIDE = [  # without Joint" in the name.
    "State Controlling Board",
    "Legislative Service Commission",
    "Correctional Institution Inspection Committee"
]


class OHLegislatorScraper(LegislatorScraper):
    jurisdiction = 'oh'
    latest_only = True

    def scrape(self, chamber, term):
        url = (
            "http://www.ohiosenate.gov/senate/members/senate-directory"
            if chamber == "upper" else
            "http://www.ohiohouse.gov/members/member-directory")
        self.scrape_page(chamber, term, url)

    def scrape_homepage(self, leg, homepage, term):
        with self.urlopen(homepage) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(homepage)
        bio = page.xpath(
            "//div[@class='biography']//div[@class='right']//p/text()")
        if bio != []:
            bio = bio[0]
            leg['biography'] = bio

        ctties = page.xpath("//div[@class='committeeList']//a")
        for entry in [x.text_content() for x in ctties]:
            chmbr = "joint" if "joint" in entry.lower() else "upper"
            leg.add_role('committee member',
                         term=term,
                         chamber=chmbr,
                         committee=entry)

    def scrape_page(self, chamber, term, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for legislator in page.xpath("//div[contains(concat(' ', "
                "normalize-space(@class), ' '), ' memberModule ')]"):

            img = legislator.xpath(
                ".//div[@class='thumbnail']//img")[0].attrib['src']
            data = legislator.xpath(".//div[@class='data']")[0]
            homepage = data.xpath(".//a[@class='black']")[0]
            full_name = homepage.text_content()
            homepage = homepage.attrib['href']
            party = data.xpath(
                ".//span[@class='partyLetter']")[0].text_content()
            party = {"R": "Republican", "D": "Democratic"}[party]
            office_lines = data.xpath("child::text()")
            phone = office_lines.pop(-1)
            office = "\n".join(office_lines)
            h3 = data.xpath("./h3")
            if len(h3):
                h3 = h3[0]
                district = h3.xpath("./br")[0].tail.replace("District", ""
                                                           ).strip()
            else:
                district = re.findall(
                    "\d+\.png",
                    legislator.attrib['style']
                )[-1].split(".", 1)[0]

            full_name = re.sub("\s+", " ", full_name).strip()
            leg = Legislator(term, chamber, district, full_name,
                             party=party, url=homepage, photo_url=img)

            leg.add_office('capitol', 'Capitol Office',
                           address=office,
                           phone=phone)

            self.scrape_homepage(leg, homepage, term)

            leg.add_source(url)
            self.save_legislator(leg)
