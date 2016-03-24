import urlparse
import lxml.etree

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import clean_committee_name

import scrapelib
import os.path


CAP_ADDRESS = """P. O. Box 1018
Jackson, MS 39215"""

class MSLegislatorScraper(LegislatorScraper):
    jurisdiction = 'ms'

    def scrape(self, chamber, term_name):
        self.validate_term(term_name, latest_only=True)
        self.scrape_legs(chamber, term_name)

    def scrape_legs(self, chamber, term_name):
        if chamber == 'upper':
            url = 'http://billstatus.ls.state.ms.us/members/ss_membs.xml'
            range_num = 5
        else:
            url = 'http://billstatus.ls.state.ms.us/members/hr_membs.xml'
            range_num = 6

        leg_dir_page = self.get(url)
        root = lxml.etree.fromstring(leg_dir_page.content)
        for mr in root.xpath('//LEGISLATURE/MEMBER'):
            for num in range(1, range_num):
                leg_path = "string(M%s_NAME)" % num
                leg_link_path = "string(M%s_LINK)" % num
                leg = mr.xpath(leg_path)
                leg_link = mr.xpath(leg_link_path)
                role = "member"
                self.scrape_details(chamber, term_name, leg, leg_link, role)
        if chamber == 'lower':
            chair_name = root.xpath('string(//CHAIR_NAME)')
            chair_link = root.xpath('string(//CHAIR_LINK)')
            role = root.xpath('string(//CHAIR_TITLE)')
            self.scrape_details(chamber, term_name, chair_name, chair_link, role)
        else:
            #Senate Chair is the Governor. Info has to be hard coded
            chair_name = root.xpath('string(//CHAIR_NAME)')
            role = root.xpath('string(//CHAIR_TITLE)')
            # TODO: if we're going to hardcode the governor, do it better
            #district = "Governor"
            #leg = Legislator(term_name, chamber, district, chair_name,
            #                 first_name="", last_name="", middle_name="",
            #                 party="Republican", role=role)

        protemp_name = root.xpath('string(//PROTEMP_NAME)')
        protemp_link = root.xpath('string(//PROTEMP_LINK)')
        role = root.xpath('string(//PROTEMP_TITLE)')
        self.scrape_details(chamber, term_name, protemp_name, protemp_link, role)

    def scrape_details(self, chamber, term, leg_name, leg_link, role):
        if not leg_link:
            # Vacant post, likely:
            if "Vacancy" in leg_name:
                return
            raise Exception("leg_link is null. something went wrong")
        try:
            url = 'http://billstatus.ls.state.ms.us/members/%s' % leg_link
            url_root = os.path.dirname(url)
            details_page = self.get(url)
            root = lxml.etree.fromstring(details_page.content)
            party = root.xpath('string(//PARTY)')

            district = root.xpath('string(//DISTRICT)')

            photo = "%s/%s" % (url_root, root.xpath('string(//IMG_NAME)'))

            home_phone = root.xpath('string(//H_PHONE)')

            home_address = root.xpath('string(//H_ADDRESS)')
            home_address2 = root.xpath('string(//H_ADDRESS2)')
            home_city = root.xpath('string(//H_CITY)')
            home_zip = root.xpath('string(//H_ZIP)')

            home_address_total = "%s\n%s\n%s\n%s" % (
                home_address,
                home_address2,
                home_city,
                home_zip
            )

            bis_phone = root.xpath('string(//B_PHONE)')
            capital_phone = root.xpath('string(//CAP_PHONE)')
            other_phone = root.xpath('string(//OTH_PHONE)')
            org_info = root.xpath('string(//ORG_INFO)')
            email_name = root.xpath('string(//EMAIL_ADDRESS)').strip()
            cap_room = root.xpath('string(//CAP_ROOM)')

            if leg_name in ('Lataisha Jackson', 'John G. Faulkner'):
                assert not party, "Remove special-casing for this Democrat without a listed party: {}".format(leg_name)
                party = 'Democratic'
            elif leg_name in ('James W. Mathis', 'J. Walter Michel'):
                assert not party, "Remove special-casing for this Republican without a listed party: {}".format(leg_name)
                party = 'Republican'
            elif party == 'D':
                party = 'Democratic'
            elif party == 'R':
                party = 'Republican'
            else:
                raise AssertionError(
                    "A member with no identifiable party was found: {}".format(leg_name))

            leg = Legislator(term, chamber, district, leg_name, party=party, role=role,
                             org_info=org_info, url=url, photo_url=photo)
            leg.add_source(url)

            kwargs = {}

            if email_name != "":
                if "@" in email_name:
                    email = email_name
                else:
                    email = '%s@%s.ms.gov' % (email_name,
                                              {"upper": "senate", "lower": "house"}[chamber])
                kwargs['email'] = email

            if capital_phone != "":
                kwargs['phone'] = capital_phone

            if cap_room != "":
                kwargs["address"] = "Room %s\n%s" % (cap_room, CAP_ADDRESS)
            else:
                kwargs['address'] = CAP_ADDRESS

            leg.add_office('capitol', 'Capitol Office', **kwargs)

            kwargs = {}
            if home_phone != "":
                kwargs['phone'] = home_phone

            if home_address_total != "":
                kwargs['address'] = home_address_total

            if kwargs != {}:
                leg.add_office('district', 'District Office', **kwargs)

            self.save_legislator(leg)
        except scrapelib.HTTPError, e:
            self.warning(str(e))

