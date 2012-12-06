import re
from collections import defaultdict
import lxml.html

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

PARTY_DICT = {'D': 'Democratic', 'R': 'Republican', 'I': 'Independent'}

BASE_URL = 'http://www.msa.md.gov'

class MDLegislatorScraper(LegislatorScraper):
    jurisdiction = 'md'
    latest_term = True

    def scrape(self, chamber, term):
        urls = {'lower': "http://www.msa.md.gov/msa/mdmanual/06hse/html/hseal.html",
                'upper': "http://www.msa.md.gov/msa/mdmanual/05sen/html/senal.html"}
        detail_re = re.compile('\((R|D)\), (?:Senate President, )?(?:House Speaker, )?District (\w+)')

        with self.urlopen(urls[chamber]) as html:
            doc = lxml.html.fromstring(html)

            # rest of data on this page is <li>s that have anchor tags
            for a in doc.xpath('//li/a'):
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

                        # address extraction
                        # this is pretty terrible, we get address in a format that looks
                        # like:
                        #   James Senate Office Building, Room 322
                        #   11 Bladen St., Annapolis, MD 21401
                        #   (410) 841-3565, (301) 858-3565; 1-800-492-7122, ext. 3565 (toll free)
                        #   e-mail: george.edwards@senate.state.md.us
                        #   fax: (410) 841-3552, (301) 858-3552
                        #
                        #   Western Maryland Railway Station, 13 Canal St., Room 304, Cumberland, MD 21502
                        #   (301) 722-4780; 1-866-430-9553 (toll free)
                        #   e-mail: george.edwards.district@senate.state.md.us
                        #   fax: (301) 722-4790
                        # usually first ul, sometimes first p
                        try:
                            addr_lines = leg_doc.xpath('//ul')[0].text_content().strip().splitlines()
                        except IndexError:
                            addr_lines = leg_doc.xpath('//p')[0].text_content().strip().splitlines()
                        addr_pieces = {'capitol': defaultdict(str),
                                       'district': defaultdict(str)}
                        addr_type = 'capitol'
                        for line in addr_lines:
                            if '(401)' in line or '(301)' in line:
                                addr_pieces[addr_type]['phone'] = line
                            elif 'toll free' in line:
                                pass # skip stand alone 1-800 numbers
                            elif 'e-mail' in line:
                                addr_pieces[addr_type]['email'] = line.replace('email: ',
                                                                               '')
                            elif 'fax' in line:
                                addr_pieces[addr_type]['fax'] = line.replace('fax: ', '')
                            elif line == '':
                                addr_type = 'district'
                            else:
                                addr_pieces[addr_type]['address'] += '{0}\n'.format(line)
                        if addr_pieces['capitol']:
                            leg.add_office('capitol', 'Capitol Office',
                                           **addr_pieces['capitol'])
                            leg['email'] = (addr_pieces['capitol']['email'] or
                                            addr_pieces['district']['email'] or
                                            None)
                        if addr_pieces['district']:
                            leg.add_office('district', 'District Office',
                                           **addr_pieces['district'])

                    self.save_legislator(leg)
