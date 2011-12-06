import re

import lxml.html

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

PARTY_DICT = {'D': 'Democratic', 'R': 'Republican', 'I': 'Independent'}

BASE_URL = 'http://www.msa.md.gov'

class MDLegislatorScraper(LegislatorScraper):
    state = 'md'

    def scrape(self, chamber, term):
        urls = {'lower': "http://www.msa.md.gov/msa/mdmanual/06hse/html/hseal.html",
                'upper': "http://www.msa.md.gov/msa/mdmanual/05sen/html/senal.html"}
        detail_re = re.compile('\((R|D)\), (?:Senate President, )?(?:House Speaker, )?District (\w+)')

        self.validate_term(term, latest_only=True)

        with self.urlopen(urls[chamber]) as html:
            doc = lxml.html.fromstring(html)

            # data on this page is <li>s that have anchor tags
            for a in doc.cssselect('li a'):
                link = a.get('href')
                # tags don't close so we get the <li> and <a> content and diff them
                name_text = a.text_content()
                detail_text = a.getparent().text_content().replace(name_text, '')

                # ignore if it is not a valid link
                if link:
                    # handle names
                    names = name_text.split(',')
                    last_name = names[0]
                    first_name = names[1].strip()
                    # TODO: try to trim first name to remove middle initial
                    if len(names) > 2:
                        suffixes = names[2]
                    else:
                        suffixes = ''

                    # handle details
                    details = detail_text.strip()
                    party, district = detail_re.match(details).groups()
                    party = PARTY_DICT[party]

                    leg_url = BASE_URL+link

                    leg = Legislator(term, chamber, district,
                                     ' '.join((first_name, last_name)),
                                     first_name, last_name,
                                     party=party, suffixes=suffixes,
                                     url=leg_url)
                    leg.add_source(url=leg_url)

                    with self.urlopen(leg_url) as leg_html:
                        leg_doc = lxml.html.fromstring(leg_html)
                        img_src = leg_doc.xpath('//img[@align="left"]/@src')
                        if img_src:
                            leg['photo_url'] = BASE_URL + img_src[0]

                    self.save_legislator(leg)
