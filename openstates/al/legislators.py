import re
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html
import requests
from lxml import etree

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

        sponsor_ids = None
        if chamber == "lower":
            sponsor_ids = self.get_sponsor_ids()
            self.scrape_rep_info(urls["lower"],sponsor_ids,term)
        else:
            self.scrape_senate_info(urls["upper"], term)



    def get_sponsor_ids(self):
        #this is only going to work for the current session
        #TODO make it possible to do different terms/sessions?
        sponsor_id_url = "http://alisondb.legislature.state.al.us/acas/SESSBillsBySponsorSelection.asp"
        request_session = requests.Session()

        #need to visit main alison page to start session
        request_session.get("http://alisondb.legislature.state.al.us/acas/acasloginFire.asp")
    
        #now we can hit the menu we care about
        html = request_session.get(sponsor_id_url).text
        doc = lxml.html.fromstring(html)
        name_to_sponsor = {}
        sponsor_ids = doc.xpath("//select[@id='Representatives']/option")
        for sponsor in sponsor_ids:
            name_to_sponsor[sponsor.text.strip()] = sponsor.attrib["value"].strip()
        return name_to_sponsor

    def scrape_rep_info(self, url, sponsor_ids, term):

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
            rep_name = rep_name.strip()

            #match rep to sponsor_id if possible
            ln,fn = rep_name.split(",")
            last_fi_key = "{ln} ({fi})".format(ln=ln.strip(), fi=fn.strip()[0])
            leg = Legislator(term,
                            "lower",
                            district,
                            rep_name,
                            party= party.strip())
            leg.add_office('capitol',
                            'Capitol Office',
                            address=office_address,
                            phone=phone.strip())
            leg.add_source(url)
            if ln.strip() in sponsor_ids:
                sponsor_id = sponsor_ids[ln]
            elif last_fi_key in sponsor_ids:
                sponsor_id = sponsor_ids[last_fi_key]

            #custom logic for people with the same first AND last names. arg.
            elif rep_name == "Williams, Jack J. D.":
                sponsor_id = sponsor_ids["Williams (JD)"]
            elif rep_name == "Williams, Jack W.":
                sponsor_id = sponsor_ids["Williams (JW)"]

            else:
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
            person_id = senator.attrib["alt"]
            sponsor_id = senator.attrib["longdesc"]
            senator_link = base_senator_url.format(person_id = person_id, sponsor_id = sponsor_id)
            sen_html = self.urlopen(senator_link)
            sen_page = lxml.html.fromstring(sen_html)
            photo_url = sen_page.xpath("//input[contains(@id,'imgLEG')]/@src")[0]
            sen_name = sen_page.xpath("//span[@id = 'SenMainContent_lblMember']")[0].text_content().replace("SENATOR","").strip()
            sen_trs = sen_page.xpath("//table[@id='SenMainContent_TabSenator_TabPanel1_gvLEG']//tr")
            district_trs = sen_page.xpath("//table[@id='SenMainContent_TabSenator_TabBIO_gvBIO']//tr")
            info_dict = {}
            for tr in sen_trs:
                key,value = tr.xpath(".//td")
                info_dict[key.text_content().replace(":","").lower().strip()] = value.text_content().strip()
            for tr in district_trs:
                key,value = tr.xpath(".//td")
                info_dict[key.text_content().replace(":","").lower().strip()+" district"] = value.text_content().strip()

            leg = Legislator(term,
                            "upper",
                            info_dict["district"].replace("Senate District","").strip(),
                            sen_name,
                            party = party_dict[info_dict["affiliation"].strip()]
                            )

            address_parts = ["street","office","city","state","postal code"]
            cap_address = [info_dict[a].strip() for a in address_parts if info_dict[a].strip() != ""]
            dist_address = [info_dict[a+" district"].strip() for a in address_parts if info_dict[a+" district"].strip() != ""]


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
        rows = leg_page.xpath("//table[contains(@id,'TabCommittees')]//tr")
        for row in rows:
            tds = [r.text_content() for r in row.xpath(".//td")]
            if len(tds) == 0:
                continue
            role = "member"
            comm_name = tds[1].lower().strip()
            if tds[2].strip().lower() in ["chairperson", "ranking minority member", "vice chairperson"]:
                role = tds[2].strip().lower()
            
            leg.add_role('committee member',
                        term=term,
                        chamber=chamber,
                        committee=comm_name,
                        position=role)

