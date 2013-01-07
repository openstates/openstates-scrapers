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
        if chamber == 'upper':
            self.scrape_senators(chamber, term)
        else:
            self.scrape_reps(chamber, term)

    def scrape_reps(self, chamber, term):
        # There are 99 House districts
        for district in xrange(1, 100):
            rep_url = ('http://www.house.state.oh.us/components/'
                       'com_displaymembers/page.php?district=%d' % district)

            with self.urlopen(rep_url) as page:
                page = lxml.html.fromstring(page)

                ranges = []
                cur = []
                info = page.xpath('//td[@class="info"]/*')
                for r in info:
                    if r.tag == 'strong':
                        ranges.append(cur)
                        cur = []
                    else:
                        cur.append(r)
                ranges.append(cur)

                block = ranges[4][:-1]

                address = ", ".join(
                    [ x.tail.strip() for x in block ])

                phone = page.xpath(
                    "//strong[contains(text(), 'Phone')]")[0].tail

                fax = page.xpath(
                    "//strong[contains(text(), 'Fax')]")[0].tail

                for el in page.xpath('//table[@class="page"]'):
                    rep_link = el.xpath('tr/td/title')[0]
                    full_name = rep_link.text
                    party = full_name[-2]
                    full_name = full_name[0:-3]

                    if full_name == 'Vacant Posit':
                        continue

                    if party == "D":
                        party = "Democratic"
                    elif party == "R":
                        party = "Republican"


                    leg = Legislator(term, chamber, str(district),
                                     full_name, party=party, url=rep_url)
                    leg.add_office('capitol',
                                   'Capitol Office',
                                    address=address,
                                    phone=phone,
                                    fax=fax)  # Yet, no email.

                    committees = page.xpath("//table[@class='billLinks']")[0]
                    for committee in committees.xpath(".//tr"):
                        td = committee.xpath(".//td")
                        if len(td) != 2:
                            break

                        name, role = td
                        name, role = name.text_content(), role.text_content()
                        name, role = name.strip(), role.strip()
                        if name[0] == "|":
                            continue

                        if name.strip() == "Committee Name":
                            continue

                        chmbr = chamber
                        if "joint" in name.lower():
                            chmbr = "joint"

                        if name in JOINT_COMMITTEE_OVERRIDE:
                            chmbr = "joint"

                        leg.add_role('committee member',
                            term=term,
                            chamber=chmbr,
                            committee=name,
                            position=role
                        )

                    leg.add_source(rep_url)
                    self.save_legislator(leg)

    def scrape_senate_homepage(self, leg, homepage, term):
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

    def scrape_senators(self, chamber, term):
        url = 'http://www.ohiosenate.gov/senate/members/senate-directory'
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
            district = re.findall(
                "\d+\.png",
                legislator.attrib['style']
            )[-1].split(".", 1)[0]
            print district

            leg = Legislator(term, chamber, district, full_name,
                             party=party, url=homepage, photo_url=img)

            leg.add_office('capitol', 'Capitol Office',
                           address=office,
                           phone=phone)

            self.scrape_senate_homepage(leg, homepage, term)

            leg.add_source(url)
            self.save_legislator(leg)
