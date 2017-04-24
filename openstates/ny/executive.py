from pupa.scrape import Scraper
from pupa.models import Event
from pupa.utils.date_util import WordsToNumbers as Wtn

import lxml
import datetime as dt
import re


class NYGovernorPressScraper(Scraper):
    def get_events(self):
        # get list of executive orders
        url = 'http://www.governor.ny.gov/sl2/ExecutiveOrderindex'
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        # extract governor's name
        gov = page.xpath("(//div[@class='section-header']/div/div/div/a/div/h2)[1]")[0]
        governor_name = gov.text.lstrip('Governor ')

        # scrape each executive order
        for eo_par in page.xpath("//div[@class='content']/p"):
            for link in eo_par.xpath(".//a"):

                url = link.get('href').lower()
                if url.endswith('.pdf'):
                    continue

                # get date for executive order
                eo_page = self.urlopen(url)
                eo_page = lxml.html.fromstring(eo_page)
                eo_page = re.sub('(\\r*\\n|\W)', ' ', eo_page.xpath('string()').lower())
                eo_page = re.sub('\s+', ' ', eo_page)
                date_par = re.search('(?:g i v e n)(.*)(?:by the governor)', eo_page).groups()[0]
                date_comp = [s.strip() for s in
                             re.match('(?:.*this)(.*)(?:day of)(.*)(?:in the year)(.*)', date_par).groups()]
                eo_date = dt.datetime.strptime(' '.join(
                    (str(Wtn.parse(date_comp[0])), date_comp[1], str(Wtn.parse(date_comp[2])))), '%d %B %Y')

                # build yield object
                eo_number = eo_par.xpath('string()').split(':', 1)[0]
                eo = Event(eo_number, eo_date, 'New York')
                eo.add_person(governor_name, 'governor')
                eo.description = link.text
                eo.add_document(eo_number, url, 'text/html')
                eo.add_source(url)

                yield eo

        # TODO: get list of press statements