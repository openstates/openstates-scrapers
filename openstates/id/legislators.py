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
    jurisdiction = 'id'

    def _extract_email(self, contact_form):
        legislator_id = re.search(r'(\d+)', contact_form).group(1)
        contact_page = self.get(contact_form).text
        pattern = re.compile(r'legislators.email%s = "(.+?)";' % legislator_id)
        email = pattern.search(contact_page).group(1)

        return email


    def scrape_sub(self, chamber, term, district, sub_url):
        "Scrape basic info for a legislator's substitute."
        page = self.get(sub_url).text
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
        leg = Legislator(term, chamber, district.strip(), full_name, party, **leg)
        leg['roles'][0] = {'chamber': chamber, 'state': self.state,
                           'term': term, 'role':'substitute',
                           'legislator': subfor[subfor.rindex('for'):],
                           'district': district.replace('District', '').strip(),
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
        index = self.get(url).text
        html = lxml.html.fromstring(index)
        html.make_links_absolute(url)
        base_table = html.xpath('body/table/tr/td[2]/table[2]')
        district = None # keep track of district for substitutes
        for row in base_table[0].xpath('tr'):
            img_url = row.xpath('string(.//img/@src)')
            contact_form, additional_info_url = row.xpath('.//a/@href')
            email = self._extract_email(contact_form)
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

            # The parsed HTML will be something like:
            # ['District 4', '2', 'nd', 'term', address, phone(s), profession, committees]
            # Sometimes there's a leadership title before all that
            if 'District ' in pieces[1]:
                pieces.pop(0)
            assert pieces[0].startswith('District '), "Improper district found: {}".format(pieces[0])
            assert pieces[3] == 'term', "Improper term found: {}".format(pieces[3])

            district = pieces[0]
            district = district.replace('District', '').strip()
            pieces = pieces[4:]
            if pieces[0].startswith(u'(Served '):
                pieces.pop(0)

            address = re.sub(r'(\d{5})', r'ID \1', pieces.pop(0).strip())
            assert re.match(r'.*\d{5}', address), "Address potentially invalid: {}".format(address)

            phone = None
            fax = None
            for line in pieces:
                if line.lower().startswith('home '):
                    phone = line[len('home '):]
                elif not phone and line.lower().startswith('bus '):
                    phone = line[len('bus '):]
                if line.lower().startswith('fax '):
                    fax = line[len('fax '):]

                # After committees begin, no more contact information exists
                if line == "Committees:":
                    break

            leg = Legislator(term,
                             chamber,
                             district,
                             full_name,
                             party=party,
                             email=email)

            leg.add_office('district',
                           'District Office',
                           address=address,
                           email=email,
                           fax=fax if fax else None,
                           phone=phone if phone else None)

            leg.add_source(url)
            leg['photo_url'] = img_url
            leg['contact_form'] = contact_form
            leg['url'] = additional_info_url

            self.save_legislator(leg)
