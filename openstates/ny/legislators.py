# -*- coding: utf-8 -*-
import re
import itertools

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html



class NYLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ny'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            self.scrape_upper(term)
        else:
            self.scrape_lower(term)

    def scrape_upper(self, term):
        url = "http://www.nysenate.gov/senators"
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        xpath = (
            '//div[contains(@class, "views-row")]/'
            'div[contains(@class, "last-name")]/'
            'span[contains(@class, "field-content")]/a')
        for link in page.xpath(xpath):
            if link.text in (None, 'Contact', 'RSS'):
                continue
            name = link.text.strip()

            district = link.xpath("string(../../../div[3]/span[1])")
            district = re.match(r"District (\d+)", district).group(1)

            photo_link = link.xpath("../../../div[1]/span/a/img")[0]
            photo_url = photo_link.attrib['src']

            legislator = Legislator(term, 'upper', district,
                                    name, party="Unknown",
                                    photo_url=photo_url)
            legislator.add_source(url)

            contact_link = link.xpath("../span[@class = 'contact']/a")[0]
            contact_url = contact_link.attrib['href']
            self.scrape_upper_offices(legislator, contact_url)

            legislator['url'] = contact_url.replace('/contact', '')

            self.save_legislator(legislator)

    def scrape_upper_offices(self, legislator, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        legislator.add_source(url)

        xpath = '//a[contains(@href, "profile-pictures")]/@href'
        legislator['photo_url'] = page.xpath(xpath).pop()

        email = page.xpath('//span[@class="spamspan"]')
        if email:
            email = email[0].text_content()
            email = email.replace(' [at] ', '@').replace(' [dot] ', '.')
            legislator['email'] = email

        dist_str = page.xpath("string(//div[@class = 'district'])")
        match = re.findall(r'\(([A-Za-z,\s]+)\)', dist_str)
        if match:
            match = match[0].split(', ')
            party_map = {'D': 'Democratic', 'R': 'Republican',
                         'WF': 'Working Families',
                         'C': 'Conservative',
                         'IP': 'Independence',
                        }
            parties = [party_map.get(p.strip(), p.strip()) for p in match
                       if p.strip()]
            if 'Republican' in parties:
                party = 'Republican'
                parties.remove('Republican')
            elif 'Democratic' in parties:
                party = 'Democratic'
                parties.remove('Democratic')
            legislator['roles'][0]['party'] = party
            legislator['roles'][0]['other_parties'] = parties

        try:
            span = page.xpath("//span[. = 'Albany Office']/..")[0]
            address = span.xpath("string(div[1])").strip()
            address += "\nAlbany, NY 12247"

            phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
            phone = phone.text.strip()

            office = dict(
                    name='Capitol Office',
                    type='capitol', phone=phone,
                    fax=None, email=None,
                    address=address)

            legislator.add_office(**office)

        except IndexError:
            # Sometimes contact pages are just plain broken
            pass

        try:
            span = page.xpath("//span[. = 'District Office']/..")[0]
            address = span.xpath("string(div[1])").strip() + "\n"
            address += span.xpath(
                "string(span[@class='locality'])").strip() + ", "
            address += span.xpath(
                "string(span[@class='region'])").strip() + " "
            address += span.xpath(
                "string(span[@class='postal-code'])").strip()

            phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
            phone = phone.text.strip()

            office = dict(
                    name='District Office',
                    type='district', phone=phone,
                    fax=None, email=None,
                    address=address)

            legislator.add_office(**office)
        except IndexError:
            # No district office yet?
            pass

    def scrape_lower(self, term):
        url = "http://assembly.state.ny.us/mem/?sh=email"
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        # full_names = []

        def _split_list_on_tag(lis, tag):
            data = []
            for entry in lis:
                if entry.attrib['class'] == tag:
                    yield data
                    data = []
                else:
                    data.append(entry)

        for row in _split_list_on_tag(page.xpath("//div[@id='mememailwrap']/*"),
                                      "emailclear"):

            try:
                name, district, email = row
            except ValueError:
                name, district = row
                email = None

            link = name.xpath(".//a[contains(@href, '/mem/')]")
            if link != []:
                link = link[0]
            else:
                link = None

            if email is not None:
            # XXX: Missing email from a record on the page
            # as of 12/11/12. -- PRT
                email = email.xpath(".//a[contains(@href, 'mailto')]")
                if email != []:
                    email = email[0]
                else:
                    email = None

            name = link.text.strip()
            if name == 'Assembly Members':
                continue

            # empty seats
            if 'Assembly District' in name:
                continue

            district = link.xpath("string(../following-sibling::"
                                  "div[@class = 'email2'][1])")
            district = district.rstrip('rthnds')

            # unicodedata.normalize didn't help here.
            if name == u'Sep\xfalveda, Luis':
                party_name = party_dict['Sepulveda, Luis']
            else:
                party_name = party_dict[name]

            leg_url = link.get('href')
            legislator = Legislator(term, 'lower', district, name,
                                    party=party_name,
                                    url=leg_url)
            legislator.add_source(url)

            # Legislator
            self.scrape_lower_offices(leg_url, legislator)

            if email is not None:
                email = email.text_content().strip()
                if email:
                    legislator['email'] = email

            self.save_legislator(legislator)

    def scrape_lower_offices(self, url, legislator):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        contact = doc.xpath('//div[@id="addrinfo"]')[0]
        email = contact.xpath(".//a[contains(@href, 'mailto:')]")
        if email != []:
            email = email[0].attrib['href'].replace("mailto:", "").strip()
            if not email:
                email = None
        else:
            email = None

        # Sometimes class is "addrcol1", others "addrcola"
        col_generators = [

            # Try alpha second.
            iter('abcedef'),

            # Try '' first, then digits.
            itertools.chain(iter(['']), iter(xrange(1, 5)))
            ]

        cols = col_generators.pop()
        while True:

            # Get the column value.
            try:
                col = cols.next()
            except StopIteration:
                try:
                    cols = col_generators.pop()
                except IndexError:
                    break
                else:
                    continue

            xpath = 'div[@class="addrcol%s"]' % str(col)
            address_data = contact.xpath(xpath)
            if not address_data:
                continue

            for data in address_data:
                data = (data.xpath('div[@class="officehdg"]/text()'),
                        data.xpath('div[@class="officeaddr"]/text()'))
                ((office_name,), address) = data

                if 'district' in office_name:
                    office_type = 'district'
                else:
                    office_type = 'capitol'

                # Phone can't be blank.
                phone = address.pop().strip()
                if not phone:
                    phone = None

                office = dict(
                    name=office_name, type=office_type, phone=phone,
                    fax=None, email=email,
                    address=''.join(address).strip())

                legislator.add_office(**office)


# Map ID's to party affiliation. Has to be an id-to-party mapping, because
# full_name gets normalized on import and may be different at scrape time
# than at the time get_parties_dict.py is run (which uses post-import data).
party_dict = {

    'Abinanti, Thomas': 'Democratic',        'Skoufis, James': 'Democratic',

    'Magnarelli, William': 'Democratic',     'McDonough, David': 'Republican',

    'Hevesi, Andrew': 'Democratic',          'Hooper, Earlene': 'Democratic',

    'Blankenbush, Ken': 'Republican',        'Kellner, Micah': 'Democratic',

    'Camara, Karim': 'Democratic',           'Gottfried, Richard': 'Democratic',

    u'Rivera, Jos\xe9': 'Democratic',        'Otis, Steven': 'Democratic',

    'Graf, Al': 'Republican',                'Stirpe, Al': 'Democratic',

    'Crespo, Marcos': 'Democratic',          'Rodriguez, Robert': 'Democratic',

    'Raia, Andrew': 'Republican',            'Thiele, Jr., Fred': 'Democratic',

    'Moya, Francisco': 'Democratic',         'Titone, Matthew': 'Democratic',

    'McDonald, III, John': 'Democratic',     'Saladino, Joseph': 'Republican',

    'Crouch, Clifford': 'Republican',        'Rabbitt, Annie': 'Republican',

    'Steck, Phil': 'Democratic',             'Stevenson, Eric': 'Democratic',

    'Cusick, Michael': 'Democratic',         'Rosa, Gabriela': 'Democratic',

    'Roberts, Samuel': 'Democratic',         'Aubry, Jeffrion': 'Democratic',

    'Brindisi, Anthony': 'Democratic',       'Galef, Sandy': 'Democratic',

    'Lentol, Joseph': 'Democratic',          'Curran, Brian': 'Republican',

    'Perry, N. Nick': 'Democratic',          'Tedisco, James': 'Republican',

    'Lifton, Barbara': 'Democratic',         'Ramos, Phil': 'Democratic',

    'Oaks, Bob': 'Republican',               'Lupinacci, Chad': 'Republican',

    'Pretlow, J. Gary': 'Democratic',        'Miller, Michael': 'Democratic',

    'Rozic, Nily': 'Democratic',             'Walter, Raymond': 'Republican',

    'Brennan, James': 'Democratic',          'Skartados, Frank': 'Democratic',

    'Espinal, Jr., Rafael': 'Democratic',    'Gibson, Vanessa': 'Democratic',

    'Butler, Marc': 'Republican',            'Farrell, Jr., Herman': 'Democratic',

    'Mayer, Shelley': 'Democratic',          'Lupardo, Donna': 'Democratic',

    'Sepulveda, Luis': 'Democratic',         'Titus, Michele': 'Democratic',

    'Garbarino, Andrew': 'Republican',       'Finch, Gary': 'Republican',

    'Borelli, Joseph': 'Republican',         'Millman, Joan': 'Democratic',

    'Barron, Inez': 'Democratic',            'Malliotakis, Nicole': 'Republican',

    'Kolb, Brian M.': 'Republican',          'Wright, Keith L.T.': 'Democratic',

    'Weinstein, Helene': 'Democratic',       'Tenney, Claudia': 'Republican',

    'Englebright, Steve': 'Democratic',      'Fahy, Patricia': 'Democratic',

    'Maisel, Alan': 'Democratic',            'Kavanagh, Brian': 'Democratic',

    'Peoples-Stokes, Crystal': 'Democratic', 'Goldfeder, Phillip': 'Democratic',

    'Solages, Michaelle': 'Democratic',      'Braunstein, Edward': 'Democratic',

    'Simanowitz, Michael': 'Democratic',     'Rosenthal, Linda': 'Democratic',

    'Glick, Deborah': 'Democratic',          'Lavine, Charles': 'Democratic',

    'Giglio, Joseph': 'Republican',          'Buchwald, David': 'Democratic',

    'Magee, William': 'Democratic',          'Jordan, Tony': 'Republican',

    'Duprey, Janet': 'Republican',           'Schimminger, Robin': 'Democratic',

    'Friend, Christopher': 'Republican',     'Reilich, Bill': 'Republican',

    'Stec, Dan': 'Republican',               'Barrett, Didi': 'Democratic',

    'Gjonaj, Mark': 'Democratic',            'Ceretto, John': 'Republican',

    u'Ortiz, F\xe9lix': 'Democratic',        'Morelle, Joseph': 'Democratic',

    'Nojay, Bill': 'Republican',             'Heastie, Carl': 'Democratic',

    'Arroyo, Carmen': 'Democratic',          'Cook, Vivian': 'Democratic',

    'Cahill, Kevin': 'Democratic',           'Zebrowski, Kenneth': 'Democratic',

    'DiPietro, David': 'Republican',         'Quart, Dan': 'Democratic',

    'Hikind, Dov': 'Democratic',             'Hennessey, Edward': 'Democratic',

    'Johns, Mark': 'Republican',             'Kim, Ron': 'Democratic',

    'McLaughlin, Steven': 'Republican',      'Montesano, Michael': 'Republican',

    'Losquadro, Dan': 'Republican',          'Sweeney, Robert': 'Democratic',

    'Robinson, Annette': 'Democratic',       'Bronson, Harry': 'Democratic',

    'Cymbrowitz, Steven': 'Democratic',      'Palmesano, Philip': 'Republican',

    'Corwin, Jane': 'Republican',            'Markey, Margaret': 'Democratic',

    'Dinowitz, Jeffrey': 'Democratic',       'Gunther, Aileen': 'Democratic',

    'Castro, Nelson': 'Democratic',          'Scarborough, William': 'Democratic',

    'Lopez, Vito': 'Democratic',             'Goodell, Andy': 'Republican',

    'Russell, Addie': 'Democratic',          'Mosley, Walter': 'Democratic',

    'Ra, Edward': 'Republican',              'Weisenberg, Harvey': 'Democratic',

    'Gantt, David': 'Democratic',            'Jaffee, Ellen': 'Democratic',

    'Santabarbara, Angelo': 'Democratic',    'Brook-Krasny, Alec': 'Democratic',

    'Katz, Steve': 'Republican',             'Barclay, William': 'Republican',

    'Weprin, David': 'Democratic',           'Gabryszak, Dennis': 'Democratic',

    'Silver, Sheldon': 'Democratic',         'Lalor, Kieran Michael': 'Republican',

    "O'Donnell, Daniel": 'Democratic',       'Colton, William': 'Democratic',

    'Abbate, Jr., Peter': 'Democratic',      'Simotas, Aravella': 'Democratic',

    'Boyland, Jr., William': 'Democratic',   'Jacobs, Rhoda': 'Democratic',

    'Fitzpatrick, Michael': 'Republican',    'DenDekker, Michael': 'Democratic',

    'Paulin, Amy': 'Democratic',             'Schimel, Michelle': 'Democratic',

    'Benedetto, Michael': 'Democratic',      'Ryan, Sean': 'Democratic',

    'Kearns, Michael': 'Democratic',         'Hawley, Stephen': 'Republican',

    'McKevitt, Tom': 'Republican',           'Lopez, Peter': 'Republican',

    'Clark, Barbara': 'Democratic',          'Nolan, Catherine': 'Democratic',
    }

