import re

from pupa.scrape import Person, Scraper, Organization

import lxml.html


JOINT_COMMITTEE_OVERRIDE = [  # without Joint" in the name.
    "State Controlling Board",
    "Legislative Service Commission",
    "Correctional Institution Inspection Committee"
]

SUBCOMMITTEES = {
    # The Senate only has Finance subcommittees
    "Finance - Corrections Subcommittee": "Finance",
    "Finance - Education Subcommittee": "Finance",
    "Finance - General Government Subcommittee": "Finance",
    "Finance - Higher Ed Subcommittee": "Finance",
    "Finance - Workforce Subcommittee": "Finance",

    # The House has mostly Finance, but also one more
    "Community and Family Advancement Subcommittee on Minority Affairs":
        "Community and Family Advancement",
    "Finance Subcommittee on Agriculture Development and Natural Resources":
        "Finance",
    "Finance Subcommittee on Health and Human Services": "Finance",
    "Finance Subcommittee on Higher Education": "Finance",
    "Finance Subcommittee on Primary and Secondary Education": "Finance",
    "Finance Subcommittee on Transportation": "Finance",
    "Finance Subcommittee on State Government and Agency Review": "Finance"
}

CHAMBER_URLS = {
    'upper': "http://www.ohiosenate.gov/members/senate-directory",
    'lower':  "http://www.ohiohouse.gov/members/member-directory"
}

committee_cache = {}


class OHLegislatorScraper(Scraper):
    latest_only = True

    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_page(chamber, CHAMBER_URLS[chamber])
        else:
            yield from self.scrape_page('upper', CHAMBER_URLS['upper'])
            yield from self.scrape_page('lower', CHAMBER_URLS['lower'])

    def fetch_committee_positions(self, a):
        page = self.get(a.attrib['href']).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(a.attrib['href'])
        ret = {}
        for entry in page.xpath("//div[@class='committeeMembers']//td//a"):
            person = re.sub(
                "\s+", " ", re.sub("\(.*\)", "", entry.text or "")).strip()

            if person == "":
                continue

            title = entry.xpath(".//div[@class='title']/text()") or None

            if title:
                title = title[0]
                ret[person] = title

        return ret

    def scrape_homepage(self, leg, chamber, homepage):
        page = self.get(homepage).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(homepage)
        bio = page.xpath(
            "//div[@class='biography']//div[@class='right']//p/text()")
        if bio != []:
            bio = bio[0]
            leg.extras['biography'] = bio

        fax_line = [
            x.strip() for x in
            page.xpath(
                "//div[@class='contactModule']/div[@class='data']/text()"
            )
            if "Fax" in x
        ]
        if fax_line:
            fax_number = re.search(
                r'(\(\d{3}\)\s\d{3}\-\d{4})', fax_line[0]
            ).group(1)
            leg.add_contact_detail(type='fax', value=fax_number, note='Office')

        ctties = page.xpath("//div[@class='committeeList']//a")
        for a in ctties:
            entry = a.text_content()

            if entry in committee_cache:
                committee_positions = committee_cache[entry]
            else:
                committee_positions = self.fetch_committee_positions(a)
                committee_cache[entry] = committee_positions

            chmbr = "joint" if "joint" in entry.lower() else chamber
            if entry in JOINT_COMMITTEE_OVERRIDE:
                chmbr = "joint"

            kwargs = {}

            if "subcommittee" in entry.lower():
                if entry in SUBCOMMITTEES:
                    kwargs['subcommittee'] = entry
                    entry = SUBCOMMITTEES[entry]
                else:
                    self.warning("No subcommittee known: '%s'" % (entry))
                    raise Exception
            org = Organization(
                name=entry,
                chamber=chmbr,
                classification='committee',
            )
            org.add_source(homepage)
            leg.add_membership(org)
            yield org

    def scrape_page(self, chamber, url):
        page = self.get(url).text
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for legislator in page.xpath(
                "//div[contains(concat(' ', normalize-space(@class), ' '), "
                "' memberModule ')]"
                ):
            img = legislator.xpath(
                ".//div[@class='thumbnail']//img")[0].attrib['src']
            data = legislator.xpath(".//div[@class='data']")[0]
            homepage = data.xpath(".//a[@class='black']")[0]
            full_name = homepage.text_content()

            if "Vacant" in full_name:
                continue

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
            email = (
                'rep{0:0{width}}@ohiohouse.gov'
                if chamber == 'lower' else
                'sd{0:0{width}}@ohiosenate.gov'
            ).format(int(district), width=2)

            leg = Person(name=full_name, district=district,
                         party=party, primary_org=chamber,
                         image=img)

            leg.add_contact_detail(type='address', value=office, note='Capitol Office')
            leg.add_contact_detail(type='voice', value=phone, note='Capitol Office')
            leg.add_contact_detail(type='email', value=email, note='Capitol Office')

            yield from self.scrape_homepage(leg, chamber, homepage)

            leg.add_source(url)
            leg.add_link(url)
            yield leg
