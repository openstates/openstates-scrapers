import html.parser

import lxml.html
from openstates.scrape import Person, Scraper
from scrapelib import HTTPError


class TNPersonScraper(Scraper):
    def scrape(self, chamber=None):
        if chamber:
            yield from self.scrape_chamber(chamber)
        else:
            yield from self.scrape_chamber("upper")
            yield from self.scrape_chamber("lower")

    def scrape_chamber(self, chamber):
        root_url = "http://www.capitol.tn.gov/"
        parties = {
            "D": "Democratic",
            "R": "Republican",
            "CCR": "Carter County Republican",
            "I": "Independent",
        }

        # testing for chamber
        if chamber == "upper":
            url_chamber_name = "senate"
            abbr = "s"
        else:
            url_chamber_name = "house"
            abbr = "h"
        chamber_url = root_url + url_chamber_name + "/members/"
        page_html = self.get(chamber_url).text
        page = lxml.html.fromstring(page_html)
        page.make_links_absolute(chamber_url)

        for row in page.xpath("//tr"):

            # Skip any a header row.
            if set(child.tag for child in row) == set(["th"]):
                continue

            vacancy_check = row.xpath("./td/text()")[1].strip()
            if "Vacant" in vacancy_check or vacancy_check == "":
                self.logger.warning("Vacant Seat")
                continue

            partyInit = row.xpath("td[3]")[0].text.split()[0]
            party = parties[partyInit]
            district = row.xpath("td[5]/a")[0].text.split()[1]
            address = row.xpath("td[6]")[0].text_content()
            # Hardcode the address of the Cordell Hull Building,
            # where all legislators currently have their offices
            address = address.strip()
            address = address.replace("CHB", "Cordell Hull Bldg.\nNashville, TN 37243")
            address = "425 5th Avenue North\nSuite " + address.strip()

            phone = [x.strip() for x in row.xpath("td[7]//text()") if x.strip()][0]

            # Member URL can't be guessed from the chamber and district alone
            # It may be `h46_JaneSmith.html` instead of `h46.html`, for example
            member_url = row.xpath("./td[2]/a/@href")[0]
            member_photo_url = (
                root_url
                + url_chamber_name
                + "/members/images/"
                + abbr
                + district
                + ".jpg"
            )

            try:
                member_page = self.get(member_url, allow_redirects=False).text
            except (TypeError, HTTPError):
                try:
                    member_url = row.xpath("td[2]/a/@href")[0]
                    member_page = self.get(member_url, allow_redirects=False).text
                except (TypeError, HTTPError):
                    self.logger.warning("Valid member page does not exist.")
                    continue

            member_page = lxml.html.fromstring(member_page)
            try:
                name = member_page.xpath("//div/div/h1/text()")[0]
            except IndexError:
                name = member_page.xpath('//div[@id="membertitle"]/h2/text()')[0]

            if "Speaker" in name:
                name = name[8 : len(name)]
            elif "Lt." in name:
                name = name[13 : len(name)]
            name = name.replace("Representative ", "")
            name = name.replace("Senator ", "")

            capitol_office_node = member_page.xpath(
                '//div[@data-mobilehide="contact"]/p'
            )[0]
            capitol_office_details = capitol_office_node.text_content()
            fax_text = [
                part for part in capitol_office_details.splitlines() if "Fax" in part
            ]
            fax = None
            if fax_text:
                fax = fax_text[0].replace("Fax", "").replace(":", "").strip()

            person = Person(
                name=name.strip(),
                image=member_photo_url,
                primary_org=chamber,
                district=district,
                party=party,
            )
            person.add_link(member_url)
            person.add_source(chamber_url)
            person.add_source(member_url)

            # TODO: add district address from this page
            person.add_contact_detail(
                type="address", value=address, note="Capitol Office"
            )
            person.add_contact_detail(type="voice", value=phone, note="Capitol Office")

            email_href = row.xpath("td[1]/a/@href")
            if email_href:
                email = html.parser.HTMLParser().unescape(
                    email_href[0][len("mailto:") :]
                )
                person.add_contact_detail(
                    type="email", value=email, note="Capitol Office"
                )
            if fax:
                person.add_contact_detail(type="fax", value=fax, note="Capitol Office")

            yield person
