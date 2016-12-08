import re
import lxml.html
from openstates.utils import LXMLMixin

from billy.scrape.legislators import LegislatorScraper, Legislator


class DELegislatorScraper(LegislatorScraper,LXMLMixin):
    jurisdiction = 'de'

    def scrape(self, chamber, term):

        url = {
            'upper': 'http://legis.delaware.gov/legislature.nsf/sen?openview',
            'lower': 'http://legis.delaware.gov/Legislature.nsf/Reps?openview',
            }[chamber]

        doc = self.lxmlize(url)

        if chamber == "upper":
            #for the senate, it's the same table
            #but the html is hard-coded in js.
            table_js = doc.xpath('.//script')[-1].text_content()
            table = None
            for line in table_js.split("\n"):
                if line.strip().startswith("var") and "sen=" in line:
                    table = line.replace("var","")
                    table = table.replace('sen="<','<')
                    table = table.replace('>";','>')
                    break

            assert table is not None, "Senate table could not be found"

            table = lxml.html.fromstring(table)
            table.make_links_absolute(url)
            trs = table.xpath('//tr')


        else:
            #same table for the house, but kindly in actual html
            trs = doc.xpath('//tr')

        base_url = "http://legis.delaware.gov"

        for tr in trs:

            name_and_url = tr.xpath('.//a')[0]
            bio_url = name_and_url.attrib["href"]
            bio_url = bio_url.replace("JavaScript:window.top.location.href=","")
            bio_url = bio_url.replace('"','')
            name = name_and_url.text_content()
            if name.strip() == "." or name.strip() == "":
                continue
            if name.strip().lower().startswith("vacant"):
                continue
            re_spaces=re.compile(r'\s{1,5}')
            name = ' '.join(re_spaces.split(name))
            district = tr.xpath('.//td')[2].text_content()
            district = district.replace("District:","").strip()


            leg = self.scrape_bio(term, chamber, district, name, bio_url)
            leg.add_source(bio_url, page="legislator detail page")
            leg.add_source(url, page="legislator list page")
            self.save_legislator(leg)

    def scrape_bio(self, term, chamber, district, name, url):
        # this opens the committee section without having to do another request
        url += '&TableRow=1.5.5'
        frame_doc = self.lxmlize(url)
        actual_url = frame_doc.xpath("//frame[@name='right']/@src")[0]
        doc = self.lxmlize(actual_url)

        # party is in one of these
        party = doc.xpath('//div[@id="page_header"]')[0].text.strip()[-3:]
        if '(D)' in party:
            party = 'Democratic'
        elif '(R)' in party:
            party = 'Republican'
        else:
            raise AssertionError("No party found for {name}".format(name=name))

        leg = Legislator(term, chamber, district, name, party=party)

        photo_url = doc.xpath('//img[contains(@src, "jpg")]/@src')
        if photo_url:
            leg['photo_url'] = photo_url[0]

        contact_info = self.scrape_contact_info(doc)
        leg.update(contact_info)
        return leg

    def scrape_contact_info(self, doc):

        # Email
        email = doc.xpath(".//a[contains(@href,'mailto')]")
        email = email[0].text_content().strip()
        leg_email = None
        dist_email = None
        try:
            emails = email.split(";")
        except AttributeError:
            pass
        else:
            for e in emails:
                e = e.strip()
                if e:
                    if "state.de.us" in e:
                        leg_email = e
                    else:
                        dist_email = e
        

        # Offices

        leg_office = dict(name="Capitol Office", type="capitol",
                        phone=None, fax=None, email=leg_email, address=None)
        dist_office = dict(name="Outside Office", type="capitol",
                        phone=None,fax=None, email=dist_email, address=None) 

        #this is enormously painful, DE.
        office_list = doc.xpath("//tr")
        for office in office_list:
            title_td = 0
            #in some trs the photo is the first td
            if len(office.xpath("./td/img")) > 0:
                title_td = 1
            try:
                title_text = office.xpath("./td")[title_td].text_content().lower()
                content = office.xpath("./td")[title_td+1].text_content()

            except IndexError:
                continue

            leg_office = self.add_contact("legislative",
                    title_text,content,leg_office)
            dist_office = self.add_contact("outside",
                    title_text,content,dist_office)

        offices = [o for o in [leg_office,dist_office] if o["address"]]
        assert len(offices) > 0, "No offices with addresses found "\
            "make sure we're not losing any data."
        return {"offices":offices}

    def add_contact(self,office_type,
                    title_text,content,office):
        #office type is the name of the office
        #either "legislative" or "outside"
        if "{} office".format(office_type) in title_text:
            office["address"] = content.strip()
        if "{} phone".format(office_type) in title_text:
            phones = content.lower().split("\n")
            if len(phones) == 1:
                phone = self.clean_phone(phones[0])
                if phone:
                    office["phone"] = phone
            else:
                for line in phones:
                    if "phone" in line:
                        phone = self.clean_phone(line)
                        if phone:
                            office["phone"] = phone
                    elif "fax" in line:
                        phone = self.clean_phone(line)
                        if phone:
                            office["fax"] = phone
        return office

    def clean_phone(self,phone):
        if not phone.strip():
            return
        if not re.search("\d",phone):
            return
        if not ":" in phone:
            return phone
        return phone.split(":")[1].strip()

