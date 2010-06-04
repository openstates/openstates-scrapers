import re

from fiftystates.scrape.legislators import LegislatorScraper, Legislator

class MDLegislatorScraper(LegislatorScraper):
    state = 'md'

    def scrape(self, chamber, year):
        urls = {'lower': "http://www.msa.md.gov/msa/mdmanual/06hse/html/hseal.html",
                'upper': "http://www.msa.md.gov/msa/mdmanual/05sen/html/senal.html"}
        detail_re = re.compile('\((R|D)\), (?:Senate President, )?(?:House Speaker, )?District (\w+)')

        if year != 2010:
            raise NoDataForYear(year)

        with self.lxml(urls[chamber]) as (resp, doc):
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
                        suffix = names[2]
                    else:
                        suffix = None

                    # handle details
                    details = detail_text.strip()
                    party, district = detail_re.match(details).groups()

                    leg = Legislator('current', chamber, district,
                                     ' '.join((first_name, last_name)),
                                     first_name, last_name, '',
                                     party, suffix=suffix,
                                     url='http://www.msa.md.gov'+link)
                    self.save_legislator(leg)
