import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import scrapelib
import lxml.html

def _get_b_tail(page, text):
    resp = []
    try:
        elem = page.xpath("//b[contains(text(), '%s')]" % text)[0]
        while True:
            if elem and elem.tag == 'font':
                resp.append(elem.text_content())
            if elem.tail:
                resp.append(elem.tail.strip())
            elem = elem.getnext()
            if elem is None or elem.tag == 'b':
                break
        return '\n'.join(resp)
    except IndexError:
        return None


class LALegislatorScraper(LegislatorScraper):
    jurisdiction = 'la'
    latest_only = True

    def scrape(self, chamber, term):
        list_url = "http://www.legis.state.la.us/bios.htm"
        with self.urlopen(list_url) as text:
            page = lxml.html.fromstring(text)
            page.make_links_absolute(list_url)

            if chamber == 'upper':
                contains = 'senate'
            else:
                contains = 'house'

            for a in page.xpath("//a[contains(@href, '%s')]" % contains):
                name = a.text.strip()
                leg_url = a.attrib['href']
                try:
                    if chamber == 'upper':
                        self.scrape_senator(name, term, leg_url)
                    else:
                        self.scrape_rep(name, term, leg_url)
                except scrapelib.HTTPError:
                    self.warning('Unable to retrieve legislator %s (%s) ' % (
                        name, leg_url))

    def scrape_rep(self, name, term, url):

        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            xpath = '//table[@id="table41"]/tr/td/font'
            name = page.xpath(xpath)[3].xpath('p')[0].text
            name = name.replace('Representative', '').strip().strip(',')

            district = page.xpath(
                "//a[contains(@href, 'district')]")[0].attrib['href']
            district = re.search("district(\d+).pdf", district).group(1)

            if "Democrat&nbsp;District" in text:
                party = "Democratic"
            elif "Republican&nbsp;District" in text:
                party = "Republican"
            elif "Independent&nbsp;District" in text:
                party = "Independent"
            else:
                party = "Other"

            kwargs = {"party": party,
                      "url": url}

            photo = page.xpath("//img[@rel='lightbox']")
            if len(photo) > 0:
                photo = photo[0]
                photo_url = "http://house.louisiana.gov/H_Reps/%s" % (
                    photo.attrib['src']
                )
                kwargs['photo_url'] = photo_url
            else:
                self.warning("No photo found :(")

            district_office = _get_b_tail(page, 'DISTRICT OFFICE')
            email = page.xpath('//a[starts-with(@href, "mailto")]/@href')[0]
            # split off extra parts of mailto: link
            email = email.split(':')[1].split('?')[0]

            leg = Legislator(term, 'lower', district, name, email=email,
                             **kwargs)
            leg.add_office('district', 'District Office',
                           address=district_office)
            leg.add_source(url)

            self.save_legislator(leg)

    def scrape_senator(self, name, term, url):
        text = self.urlopen(url)
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)

        name = page.xpath('//title')[0].text_content().split('>')[-1].strip().strip(',')

        district = page.xpath(
            "string(//*[starts-with(text(), 'Senator ')])")

        district = re.search(r'District (\d+)', district).group(1)

        party = _get_b_tail(page, 'Party')

        if party == 'No Party (Independent)':
            party = 'Independent'
        elif party == 'Democrat':
            party = 'Democratic'

        email = _get_b_tail(page, 'E-mail')
        photo_url = page.xpath('//img[starts-with(@src, "%s")]/@src' % url)
        if photo_url:
            photo_url = photo_url[0]
        else:
            photo_url = None
        capitol = _get_b_tail(page, 'Capitol Office').splitlines()
        capitol_address = '\n'.join(capitol[0:2])
        capitol_phone = capitol[2]
        district_address = _get_b_tail(page, 'District Office')
        district_phone = _get_b_tail(page, 'Phone')
        district_fax = _get_b_tail(page, 'Fax')


        leg = Legislator(term, 'upper', district, name, party=party,
                         url=url, email=email, photo_url=photo_url)
        leg.add_office('capitol', 'Capitol Office', address=capitol_address,
                       phone=capitol_phone)
        leg.add_office('district', 'District Office', address=district_address,
                       phone=district_phone, fax=district_fax)
        leg.add_source(url)
        self.save_legislator(leg)
