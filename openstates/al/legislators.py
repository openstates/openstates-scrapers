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

        party_dict = {'(D)': 'Democratic', '(R)': 'Republican', 
                          '(I)': 'Independent'}

        urls = {
            "upper":"http://www.legislature.state.al.us/aliswww/SenatorsPicture.aspx",
            "lower":"http://www.legislature.state.al.us/aliswww/Representatives.aspx"
        }

        sponsor_ids = None
        if chamber == "lower":
            sponsor_ids = self.get_sponsor_ids()
            self.scrape_rep_info(urls["lower"],sponsor_ids,term)



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
            rows = rep_page.xpath("//table[contains(@id,'TabCommittees')]//tr")
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
                            chamber="lower",
                            committee=comm_name,
                            position=role)
            leg.add_source(rep_sponsor_url)
            self.save_legislator(leg)



