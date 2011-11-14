import lxml.html
import lxml.html.soupparser

from billy.scrape.legislators import LegislatorScraper, Legislator

class MOLegislatorScraper(LegislatorScraper):
    state = 'mo'
    assumed_telephone_prefix = '573'
    assumed_address_fmt = ('201 West Capitol Avenue %s, ' 'Jefferson City, MO 65101')
    senator_url = 'http://www.senate.mo.gov/%sinfo/senalpha.htm'
    senator_details_url = 'http://www.senate.mo.gov/%sinfo/members/mem%02d.htm'
    senator_address_url = 'http://www.senate.mo.gov/%sinfo/members/d%02d/OfficeInfo.htm'
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
        url = self.senator_url % (session[2:])
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            table = page.xpath('//*[@id="mainContent"]/table//table/tr')
            rowcount = 0
            for tr in table:
                rowcount += 1
                # the first two rows are headers, skip:
                if rowcount < 2:
                    continue
                tds = tr.xpath('td')
                full_name = tds[0].xpath('div/a')[0].text_content().strip()
                party_and_district = tds[1].xpath('div')[0].text_content().strip().split('-')
                if party_and_district[0] == 'D':
                    party = 'Democratic'
                elif party_and_district[0] == 'R':
                    party = 'Republican'
                senator_key = "%s%s" % (party_and_district[0].lower(),party_and_district[1])
                district = party_and_district[1]
                phone = tds[3].xpath('div')[0].text_content().strip()
                leg = Legislator(term, chamber, district, full_name, '', '', '', party)
                leg.add_source(url)
                url = self.senator_details_url % (session[2:],int(district))
                with self.urlopen(url) as details_page:
                    leg.add_source(url)
                    
                    #Using soupparser as legislator pages are very soupy
                    page = lxml.html.soupparser.fromstring(details_page)
                    photo_url = page.xpath('//html/body/div[2]/div/img/@src')[0]
                    committees = page.xpath('//html/body/div[2]//span[@class="style3"]/a')
                    for c in committees:
                        if c.attrib.get('href').find('info/comm/') == -1:
                            continue
                        parts = c.text_content().split('\n')
                        #print "committee = '%s'" % parts[0].strip()
                        subcommittee = None
                        if len(parts) > 1:
                            subcommittee = parts[1].strip().replace('- ','').replace(', Vice-Chairman','').replace(', Chairman','')
                        committee = parts[0].strip().replace(', Vice-Chairman','').replace(', Chairman','')
                        if subcommittee:
                            leg.add_role('committee member', term, committee=committee, subcommittee=subcommittee, chamber=chamber)
                        else:
                            leg.add_role('committee member', term, committee=committee, chamber=chamber)
                url = self.senator_address_url % (session[2:],int(senator_key[1:]))
                with self.urlopen(url) as details_page:
                    leg.add_source(url)
                    page = lxml.html.fromstring(details_page)
                    address = page.xpath('/html/body//span[2]')[0].text_content().split('\n')
                    email = page.xpath('/html/body/p/span[2]/a/@href')
                    # TODO This is only true if the href doesn't contain 'mail_form'. If it does,
                    # then there is only a webform. So...no email?
                    # TODO a lot of these have fax numbers. Include?
                leg['office_phone'] = phone
                leg['office_address'] = "%s%s" % (address[0],address[1])
                leg['photo_url'] = photo_url
                if email and len(email) > 0 and email[0] != 'mailto:':
                    leg['email'] = email[0].split(':')[1]
                    #print "em = %s" % email
                self.save_legislator(leg)

    def scrape_reps(self, chamber, session, term):
        url = (self.reps_url % (session))
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            # This is the ASP.net table container
            table_xpath = ('id("ContentPlaceHolder1_'
                            'gridMembers_DXMainTable")')
            table = page.xpath(table_xpath)[0]
            for tr in table.xpath('tr')[1:]:
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
                    leg = Legislator(term, chamber, district, full_name=full_name,
                              first_name=first_name, last_name=last_name,
                              party=party, phone=phone, office_address=address,
                              _code=leg_code)
                    leg.add_source(url)
                    url = (self.rep_details_url % (session,district))
                    leg.add_source(url)
                    with self.urlopen(url) as details_page:
                        page = lxml.html.fromstring(details_page)
                        picture = page.xpath('//*[@id="ContentPlaceHolder1_imgPhoto"]/@src')
                        email = page.xpath('//*[@id="ContentPlaceHolder1_lblAddresses"]/table/tr[4]/td/a/@href')
                        terms = page.xpath('//*[@id="ContentPlaceHolder1_lblElected"]')
                        committees = page.xpath('//*[@id="ContentPlaceHolder1_lblCommittees"]/li/a')
                        for c in committees:
                            leg.add_role('committee member', term, committee=c.text_content().strip(), chamber=chamber)
                        # TODO home address?
                        if len(email) > 0 and email[0] != 'mailto:':
                            #print "Found email : %s" % email[0]
                            leg['email'] = email[0].split(':')[1]
                        if len(picture) > 0:
                            #print "Found picture : %s" % picture[0]
                            leg['photo_url'] = picture[0]
                        leg.add_source(url)
                        self.save_legislator(leg)

    def save_vacant_legislator(self,leg):
        # Here is a stub to save the vacant records - but its not really being used
        # since the current infrastructure pays attention to the legislators and not
        # the seats. See: http://bit.ly/jOtrhd
        self.vacant_legislators.append(leg)
