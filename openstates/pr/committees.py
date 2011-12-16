import lxml.html
from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

import re

def clean_spaces(s):
    """ remove \xa0, collapse spaces, strip ends """
    if s is not None:
    	return re.sub('\s+', ' ', s.replace(u'\xa0', ' ')).strip()

class PRCommitteeScraper(CommitteeScraper):
    state = 'pr'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == "upper":
            pass
        elif chamber == "lower":
            self.scrape_house()

    def scrape_house(self):
        url = 'http://www.camaraderepresentantes.org/comisiones.asp'
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
            for link in doc.xpath('//a[contains(@href, "comisiones2")]'):
                self.scrape_house_committee(link.text, link.get('href'))

    def scrape_house_committee(self, name, url):
        com = Committee('lower', name)
        com.add_source(url)

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            contact, directiva, reps = doc.xpath('//div[@class="sbox"]/div[2]')

            # all members are tails of images (they use img tags for bullets)

            # first three members are in the directiva div
            #pres, vpres, secretary, _ = directiva.xpath('.//img')
            chair = directiva.xpath('b[text()="Presidente:"]/following-sibling::img[1]')
            vchair = directiva.xpath('b[text()="Vice Presidente:"]/following-sibling::img[1]')
            sec = directiva.xpath('b[text()="Secretario(a):"]/following-sibling::img[1]')
            if chair:
                com.add_member(clean_spaces(chair[0].tail), 'chairman')
            if vchair:
                com.add_member(clean_spaces(vchair[0].tail), 'vice chairman')
            if sec:
                com.add_member(clean_spaces(sec[0].tail), 'secretary')

            for img in reps.xpath('.//img'):
                com.add_member(clean_spaces(img.tail))

            self.save_committee(com)
