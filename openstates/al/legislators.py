import lxml.html
import requests

from billy.scrape.legislators import LegislatorScraper, Legislator


class ALLegislatorScraper(LegislatorScraper):
    jurisdiction = 'al'

    def scrape(self, chamber, term):

        #the url for each rep is unfindable (by me)
        #and the parts needed to make it up do not appear in the html or js.
        #we can find basic information on the main rep page, and sponsor
        #info on a version of their indivdual page called using only their
        #sponsor ID (which we have to scrape from ALISON)
        #we can't get detailed information without another ID
        #which I have not been able to find.

        #For senators, the pieces needed to go to their link are findable
        #so we just do that.

        #basically, here goes nothing.
        

        urls = {
            "upper":"http://www.legislature.state.al.us/aliswww/SenatorsPicture.aspx",
            "lower":"http://www.legislature.state.al.us/aliswww/Representatives.aspx"
        }

        if chamber == "lower":
            self.scrape_rep_info(urls["lower"],term)
        else:
            self.scrape_senate_info(urls["upper"], term)


    def get_sponsor_ids(self):
        ''' Map member's district to a member's sponsor ID '''

        #TODO make it possible to do different terms/sessions?
        sponsor_id_url = "http://alisondb.legislature.state.al.us/alison/SESSBillsByHouseSponsorSelect.aspx"
        request_session = requests.Session()

        #need to visit main alison page to start session
        request_session.get("http://alisondb.legislature.state.al.us/alison/alisonlogin.aspx")
    
        html = request_session.get(sponsor_id_url).text
        doc = lxml.html.fromstring(html)

        district_to_sponsor_id = {}
        sponsors = doc.xpath('//div[@class="housesponsors"]//td/input')
        for sponsor in sponsors:
            district = sponsor.attrib['title'].replace("House District", "").strip()
            district_to_sponsor_id[district] = sponsor.attrib["alt"]
        return district_to_sponsor_id


    def scrape_rep_info(self, url, term):
        district_to_sponsor_id = self.get_sponsor_ids()

        #get reps
        html = self.urlopen(url)
        page = lxml.html.fromstring(html)
        reps = page.xpath("//table[contains(@id,'HseMainContent_tabByName_TabPanel')]//tr")
        for rep in reps:
            #get basic rep info
            info = rep.xpath(".//td")
            if len(info) == 0:
                continue
            rep_name,party,district,suite,phone = [i.text_content() for i in info]
            district = district.replace("House District","").strip()
            office_address = '{}\n11 S. Union Street\nMontgomery, AL 36130'.format(suite)

            assert rep_name.count(",") == 1, "Unable to parse representative's name: {}".format(rep_name)
            full_name_parts = [x.strip() for x in rep_name.split(",")]
            full_name = "{0} {1}".format(full_name_parts[1], full_name_parts[0])

            PARTIES = {
                    'R': "Republican",
                    'D': "Democratic"
                    }
            party = PARTIES[party.strip()]

            #add basic leg info and main office
            leg = Legislator(term,
                            "lower",
                            district,
                            full_name,
                            party=party)
            leg.add_office('capitol',
                            'Capitol Office',
                            address=office_address,
                            phone=phone.strip())

            #match rep to sponsor_id if possible
            ln,fn = rep_name.split(",")
            last_fi_key = "{ln} ({fi})".format(ln=ln.strip(), fi=fn.strip()[0])

            leg.add_source(url)

            try:
                sponsor_id = district_to_sponsor_id[district]
            except KeyError:
                #can't find rep's sponsor_id, do what we can and get out!
                self.logger.warning("Legislator {name} does not match any sponsor_id and thus will not be linked to bills or committees".format(name=rep_name))
                self.save_legislator(leg)
                continue

            #scrape rep's additional info from sponsor page
            rep_sponsor_url = "http://www.legislature.state.al.us/aliswww/Representative.aspx?OID_SPONSOR={}".format(sponsor_id)
            rep_html = self.urlopen(rep_sponsor_url)
            rep_page = lxml.html.fromstring(rep_html)

            leg["photo_url"] = rep_page.xpath("//input[contains(@id,'imgLEG')]/@src")[0]
            self.add_committees(rep_page,leg,"lower",term)
            leg.add_source(rep_sponsor_url)
            self.save_legislator(leg)


    def scrape_senate_info(self, url, term):

        party_dict = {'(D)': 'Democratic', '(R)': 'Republican', 
                          '(I)': 'Independent'}

        base_senator_url = "http://www.legislature.state.al.us/aliswww/Senator.aspx?OID_SPONSOR={sponsor_id}&OID_PERSON={person_id}&SESSNAME="
        html = self.urlopen(url)
        page = lxml.html.fromstring(html)
        
        senators = page.xpath("//input[contains(@id,'SenMainContent_Img')]") + page.xpath("//input[contains(@id,'SenMainContent_img')]")
        for senator in senators:
            #the 2 ids needed to generate the url are in alt and longdesc. awesome.
            person_id = senator.attrib["alt"]
            sponsor_id = senator.attrib["longdesc"]
            
            senator_link = base_senator_url.format(person_id = person_id, sponsor_id = sponsor_id)
            sen_html = self.urlopen(senator_link)
            sen_page = lxml.html.fromstring(sen_html)
            
            #stuff that's easy to grab
            photo_url = sen_page.xpath("//input[contains(@id,'imgLEG')]/@src")[0]
            sen_name = sen_page.xpath("//span[@id = 'SenMainContent_lblMember']")[0].text_content().replace("SENATOR","").strip()
            sen_trs = sen_page.xpath("//table[@id='SenMainContent_TabSenator_TabPanel1_gvLEG']//tr")
            district_trs = sen_page.xpath("//table[@id='SenMainContent_TabSenator_TabBIO_gvBIO']//tr")
            
            assert sen_name.count(",") == 1, "Unable to parse representative's name: {}".format(sen_name)
            full_name_parts = [x.strip() for x in sen_name.split(",")]
            full_name = "{0} {1}".format(full_name_parts[1], full_name_parts[0])

            #putting the stuff in the table in a dictionary
            #with the first td as the key and the 2nd as the value
            info_dict = {}
            for tr in sen_trs:
                key,value = tr.xpath(".//td")
                info_dict[key.text_content().replace(":","").lower().strip()] = value.text_content().strip()
            
            #the district table has similar info. Sometimes they use the same names.
            #throwing " district" on the end of those keys to avoid overwriting
            for tr in district_trs:
                key,value = tr.xpath(".//td")
                info_dict[key.text_content().replace(":","").lower().strip()+" district"] = value.text_content().strip()

            leg = Legislator(term,
                            "upper",
                            info_dict["district"].replace("Senate District","").strip(),
                            full_name,
                            party = party_dict[info_dict["affiliation"].strip()]
                            )

            #putting addresses together, skipping empty fields
            address_parts = ["street","office","city","state","postal code"]
            cap_address = [info_dict[a].strip() for a in address_parts if info_dict[a].strip() != ""]
            dist_address = [info_dict[a+" district"].strip() for a in address_parts if info_dict[a+" district"].strip() != ""]


            #turning empties to nones
            for k,v in info_dict.items():
                if v.strip() == "":
                    info_dict[k] = None
                else:
                    info_dict[k] = v.strip()
                if k == "fax number": #sometimes use "fax", sometimes "fax number"
                    info_dict["fax"] = info_dict[k]


            leg.add_office('capitol',
                            'Capitol Office',
                            address=" ".join(cap_address),
                            phone=info_dict["phone number"],
                            email=info_dict["email"],
                            fax=info_dict["fax"])

            #sometimes there is no district office
            if len(dist_address) > 0:
                leg.add_office('district',
                                "District Office",
                                address=" ".join(dist_address),
                                phone=info_dict["district phone district"],
                                fax=info_dict["district fax district"])

            leg.add_source(url)
            leg.add_source(senator_link)

            self.add_committees(sen_page,leg,"upper",term)

            self.save_legislator(leg)


    def add_committees(self,leg_page,leg,chamber,term):
        #as of today, both chambers do committees the same way! Yay!
        rows = leg_page.xpath("//table[contains(@id,'TabCommittees')]//tr")
        for row in rows:
            tds = [r.text_content() for r in row.xpath(".//td")]
            if len(tds) == 0:
                continue
            role = "member"
            comm_name = tds[1].strip()
            if tds[2].strip().lower() in ["chairperson", "ranking minority member", "vice chairperson"]:
                role = tds[2].strip().lower()
            
            leg.add_role('committee member',
                        term=term,
                        chamber=chamber,
                        committee=comm_name,
                        position=role)
