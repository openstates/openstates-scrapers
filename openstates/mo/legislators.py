import lxml.html
import xlrd

from billy.scrape.legislators import LegislatorScraper, Legislator


class MOLegislatorScraper(LegislatorScraper):
    state = 'mo'
    assumed_telephone_prefix = '573'
    assumed_address_fmt = ('201 West Capitol Avenue %s, '
                            'Jefferson City, MO 65101')
    senator_url = 'http://www.senate.mo.gov/%sinfo/%sSenateRoster.xls'
    reps_url = 'http://www.house.mo.gov/member.aspx?year=%s'
    rep_details_url = 'http://www.house.mo.gov/member.aspx?year=%s&district=%s'
    vacant_legislators = []

    def scrape(self, chamber, term):
        session = term.split('-')[0]
        if chamber == 'upper':
            self.scrape_senators(chamber, session, term)
        elif chamber == 'lower':
            self.scrape_reps(chamber, session, term)

    def scrape_senators(self, chamber, session, term):
        url = (self.senator_url % (session[2:], session))
        with self.urlopen(url) as senator_xls:
            with open('mo_senate.xls', 'w') as f:
                f.write(senator_xls)

        wb = xlrd.open_workbook('mo_senate.xls')
        sh = wb.sheet_by_index(0)

        for rownum in xrange(0, sh.nrows):
            district = str(int(sh.cell(rownum, 0).value))
            party = sh.cell(rownum, 1).value
            if party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'
            last_name = sh.cell(rownum, 2).value
            first_name = sh.cell(rownum, 4).value
            middle_name = sh.cell(rownum, 5).value
            full_name = ' '.join([n
                for n in [first_name, middle_name, last_name] if n])
            address = sh.cell(rownum, 6).value + ' ' + sh.cell(rownum, 7).value

            phone = sh.cell(rownum, 8).value
            if not phone.startswith(self.assumed_telephone_prefix):
                # Add the prefix for the region (assuming it's right)
                phone = self.assumed_telephone_prefix + '-' + phone
            leg = Legislator(term, chamber, district, full_name,
                            first_name, last_name, middle_name,
                            party,
                            office_address=address,
                            office_phone=phone)
            leg.add_source(url)
            self.save_legislator(leg)

    def scrape_reps(self, chamber, session, term):
        url = (self.reps_url % (session))
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            # This is the ASP.net table container
            table_xpath = ('id("ctl00_ContentPlaceHolder1_'
                            'gridMembers_DXMainTable")')
            table = page.xpath(table_xpath)[0]
            for tr in table.xpath('tr'):
                tds = tr.xpath('td')
                leg_code = tds[0].xpath('a[1]')[0].attrib.get('href')
                last_name = tds[0].text_content().strip()
                first_name = tds[1].text_content().strip()
                full_name = '%s %s' % (first_name, last_name)
                district = str(int(tds[2].text_content().strip()))
                party = tds[3].text_content().strip()
                if party == 'Democrat':
                    party = 'Democratic'
                phone = tds[4].text_content().strip()
                room = tds[5].text_content().strip()
                address = self.assumed_address_fmt % (room if room else '')
                if last_name == 'Vacant':
                    leg = Legislator(term, chamber, district, full_name=full_name,
                                first_name=first_name, last_name=last_name,
                                party=party, phone=phone,
                                office_address=address,
                                _code=leg_code)
                    leg.add_source(url)
                    self.save_vacant_legislator(leg)
                else:
                    url = (self.rep_details_url % (session,district))
                    with self.urlopen(url) as details_page:
                        page = lxml.html.fromstring(details_page)
                        picture = page.xpath('//*[@id="ContentPlaceHolder1_imgPhoto"]/@src')
                        if len(picture) > 0:
                            #print "Found picture : %s" % picture[0]
                            picture = picture[0]
                        else:
                            picture = None
                        email = page.xpath('//*[@id="ContentPlaceHolder1_lblAddresses"]/table/tr[4]/td/a/@href')
                        if len(email) > 0 and email[0] != 'mailto:':
                            #print "Found email : %s" % email[0]
                            email = email[0].split(':')[1]
                        else:
                            email = None
                        # TODO the detailed page also includes:
                        # sponsored bills
                        # committees
                        # when elected
                        # terms served
                        # counties
                        # hometown
                        # biography
                        # home address
                        # district map details
                        leg = Legislator(term, chamber, district, full_name=full_name,
                                  first_name=first_name, last_name=last_name,
                                  party=party, phone=phone, office_address=address,
                                  photo_url=picture, email=email, 
                                  _code=leg_code)
                        # TODO are both sources supposed to be saved?
                        leg.add_source(url)
                        self.save_legislator(leg)

    def save_vacant_legislator(self,leg):
        # Here is a stub to save the vacant records - but its not really being used
        # since the current infrastructure pays attention to the legislators and not
        # the seats. See: http://bit.ly/jOtrhd
        self.vacant_legislators.append(leg)
