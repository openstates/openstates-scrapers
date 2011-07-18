from billy.scrape.legislators import LegislatorScraper, Legislator
import re
import datetime
import lxml.html

_BASE_URL = 'http://legislature.idaho.gov/%s/membership.cfm'

_CHAMBERS = {'upper':'Senate', 'lower':'House'}
_PARTY = {
        '(R)': 'Republican',
        '(D)': 'Democratic',
    }
_PHONE_NUMBERS = {'hom':'phone_number',
                  'bus':'business_phone',
                  'fax':'fax_number'}

class IDLegislatorScraper(LegislatorScraper):
    """Legislator data seems to be available for the current term only."""
    state = 'id'

    def scrape_sub(self, chamber, term, district, sub_url):
        "Scrape basic info for a legislator's substitute."
        with self.urlopen(sub_url) as page:
            html = lxml.html.fromstring(page)
            html.make_links_absolute(sub_url)
            # substitute info div#MAINS35
            div = html.xpath('//div[contains(@id, "MAINS")]')[0]
            leg = {}
            leg['img_url'] = div[0][0].get('src')
            subfor = div[1][0].text.replace(u'\xa0', ' ').replace(': ', '')
            full_name = div[1][2].text.replace(u'\xa0', ' ')
            party = _PARTY[div[1][2].tail.strip()]
            leg['contact_form'] = div[1][3].xpath('string(a/@href)')
            leg = Legislator(term, chamber, district, full_name, party, **leg)
            leg['roles'][0] = {'chamber': chamber, 'state': self.state,
                               'term': term, 'role':'substitute',
                               'legislator': subfor[subfor.rindex('for'):],
                               'district': district.replace('District', ''),
                               'party': party,
                               'start_date':None, 'end_date':None}
            leg.add_source(sub_url)
            self.save_legislator(leg)

    def scrape(self, chamber, term):
        """
        Scrapes legislators for the current term only
        """
        self.validate_term(term, latest_only=True)
        url = _BASE_URL % _CHAMBERS[chamber].lower()
        with self.urlopen(url) as index:
            html = lxml.html.fromstring(index)
            html.make_links_absolute(url)
            base_table = html.xpath('body/table/tr/td[2]/table[2]')
            district = None # keep track of district for substitutes
            for row in base_table[0].xpath('tr'):
                img_url = row.xpath('string(.//img/@src)')
                contact_form, additional_info_url = row.xpath('.//a/@href')
                if "Substitute" in row.text_content():
                    # it seems like the sub always follows the person who he/she
                    # is filling in for.
                    # most sub info is provided at the additional info url
                    self.scrape_sub(chamber, term, district, additional_info_url)
                    continue
                else:
                    full_name = " ".join(row[1][0].text_content().replace(u'\xa0', ' ').split())
                    party = _PARTY[row[1][0].tail.strip()]

                pieces = [ x.strip() for x in row.itertext() if x ][6:]

                # the first index will either be a role or the district
                role = None
                if 'District' in pieces[0]:
                    district = pieces.pop(0)
                else:
                    role = pieces.pop(0)
                    district = pieces.pop(0)

                leg = Legislator(term, chamber,
                                 district.replace('District', ''), full_name,
                                 party=party)
                leg.add_source(url)
                leg['photo_url'] = img_url
                leg['contact_form'] = contact_form
                leg['additional_info_url'] = additional_info_url
                leg['address'] = pieces.pop(0)

                # at this point 'pieces' still contains phone numbers and profession
                # and committee membership
                # skip committee membership, pick 'em up in IDCommitteeScraper
                end = -1
                if 'Committees:' in pieces:
                    end = pieces.index('Committees:')
                for prop in pieces[:end]:
                    # phone numbers
                    if prop.lower()[0:3] in _PHONE_NUMBERS:
                        leg[ _PHONE_NUMBERS[ prop.lower()[0:3] ] ] = prop
                    # profession
                    else:
                        leg['profession'] = prop

                self.save_legislator(leg)
