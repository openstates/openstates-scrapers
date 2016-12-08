from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from lxml import html

import re, datetime

class AZLegislatorScraper(LegislatorScraper):
    jurisdiction = 'az'
    parties = {
        'R': 'Republican',
        'D': 'Democratic',
        'L': 'Libertarian',
        'I': 'Independent',
        'G': 'Green'
    }

    def get_party(self, abbr):
        return self.parties[abbr]

    def get_session_id(self, session):
        return self.metadata['session_details'][session]['session_id']

    def get_session_for_term(self, term):
        # ideally this should be either first or second regular session
        # and probably first and second when applicable
        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][-1]
                if re.search('regular', session):
                    return session
                else:
                    return t['sessions'][0]

    def scrape(self, chamber, term):
        self.validate_term(term)
        session = self.get_session_for_term(term)
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod(session)

        body = {'lower': 'H', 'upper': 'S'}[chamber]
        url = 'http://www.azleg.gov/MemberRoster.asp?Session_ID=%s&body=%s' % (
                                                               session_id, body)
        page = self.get(url).text
        root = html.fromstring(page)
        path = '//table[@id="%s"]/tr' % {'H': 'house', 'S': 'senate'}[body]
        roster = root.xpath(path)[1:]
        for row in roster:
            position = ''
            vacated = ''
            name, district, party, email, room, phone, fax = row.xpath('td')

            if email.attrib.get('class') == 'vacantmember':
                continue  # Skip any vacant members.

            link = name.xpath('string(a/@href)')
            link = "http://www.azleg.gov" + link
            if len(name) == 1:
                name = name.text_content().strip()
            else:
                position = name.tail.strip()
                name = name[0].text_content().strip()

            linkpage = self.get(link).text
            linkroot = html.fromstring(linkpage)
            linkroot.make_links_absolute(link)

            photos = linkroot.xpath("//img[@name='memberphoto']")

            if len(photos) != 1:
                raise Exception

            photo_url = photos[0].attrib['src']

            district = district.text_content()
            party = party.text_content().strip()
            email = email.text_content().strip()

            if ('Vacated' in email or 'Resigned' in email or 
                'Removed' in email):
                # comment out the following 'continue' for historical
                # legislative sessions
                # for the current session, if a legislator has left we will
                # skip him/her to keep from overwriting their information
                continue
                vacated = re.search('[0-9]*/[0-9]*/\d{4}', email).group()
                email = ''

            party = self.get_party(party)
            room = room.text_content().strip()
            if chamber == 'lower':
                address = "House of Representatives\n"
            else:
                address = "Senate\n"
            address = address + "1700 West Washington\n Room " + room  \
                              + "\nPhoenix, AZ 85007"

            phone = phone.text_content().strip()
            if not phone.startswith('602'):
                phone = "602-" + phone
            fax = fax.text_content().strip()
            if not fax.startswith('602'):
                fax = "602-" + fax
            if vacated:
                end_date = datetime.datetime.strptime(vacated, '%m/%d/%Y')
                leg = Legislator( term, chamber, district, full_name=name,
                                  party=party, url=link)
                leg['roles'][0]['end_date'] = end_date
            else:
                leg = Legislator(term, chamber, district, full_name=name,
                                 party=party, url=link,
                                 photo_url=photo_url)

            leg.add_office('capitol', 'Capitol Office', address=address,
                           phone=phone, fax=fax,  email=email)

            if position:
                leg.add_role( position, term, chamber=chamber,
                             district=district, party=party)

            leg.add_source(url)

            #Probably just get this from the committee scraper
            #self.scrape_member_page(link, session, chamber, leg)
            self.save_legislator(leg)

    def scrape_member_page(self, url, session, chamber, leg):
        html = self.get(url).text
        root = html.fromstring(html)
        #get the committee membership
        c = root.xpath('//td/div/strong[contains(text(), "Committee")]')
        for row in c.xpath('ancestor::table[1]')[1:]:
            name = row[0].text_content().strip()
            role = row[1].text_content().strip()
            leg.add_role(role, session, chamber=chamber, committee=name)

        leg.add_source(url)
