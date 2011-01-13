import urlparse
import lxml.etree

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.ms.utils import clean_committee_name

import scrapelib

class MSLegislatorScraper(LegislatorScraper):
    state = 'ms'

    def scrape(self, chamber, term_name):
        self.save_errors=False
        if int(term_name[0:4]) < 2008:
            raise NoDataForPeriod(term_name)
        self.scrape_legs(chamber, term_name)

    def scrape_legs(self, chamber, term_name):
        if chamber == 'upper':
            url = 'http://billstatus.ls.state.ms.us/members/ss_membs.xml'
            range_num = 5
        else:
            url = 'http://billstatus.ls.state.ms.us/members/hr_membs.xml'
            range_num = 6

        with self.urlopen(url) as leg_dir_page:
            root = lxml.etree.fromstring(leg_dir_page, lxml.etree.HTMLParser())
            for mr in root.xpath('//legislature/member'):
                for num in range(1, range_num):
                    leg_path = "string(m%s_name)" % num
                    leg_link_path = "string(m%s_link)" % num
                    leg = mr.xpath(leg_path)
                    leg_link = mr.xpath(leg_link_path)
                    role = "member"
                    self.scrape_details(chamber, term_name, leg, leg_link, role)
            if chamber == 'lower':
                chair_name = root.xpath('string(//chair_name)')
                chair_link = root.xpath('string(//chair_link)')
                role = root.xpath('string(//chair_title)')
                self.scrape_details(chamber, term_name, chair_name, chair_link, role)
            else:
                #Senate Chair is the Governor. Info has to be hard coded
                chair_name = root.xpath('string(//chair_name)')
                role = root.xpath('string(//chair_title)')
                # TODO: if we're going to hardcode the governor, do it better
                district = "Governor"
                leg = Legislator(term_name, chamber, district, chair_name,
                                 first_name="", last_name="", middle_name="",
                                 party="Republican", role=role)

            protemp_name = root.xpath('string(//protemp_name)')
            protemp_link = root.xpath('string(//protemp_link)')
            role = root.xpath('string(//protemp_title)')
            self.scrape_details(chamber, term_name, protemp_name, protemp_link, role)

    def scrape_details(self, chamber, term, leg_name, leg_link, role):
        try:
            url = 'http://billstatus.ls.state.ms.us/members/%s' % leg_link
            with self.urlopen(url) as details_page:
                details_page = details_page.decode('latin1').encode('utf8', 'ignore')
                root = lxml.etree.fromstring(details_page, lxml.etree.HTMLParser())
                party = root.xpath('string(//party)')
                district = root.xpath('string(//district)')
                first_name, middle_name, last_name = "", "", ""

                home_phone = root.xpath('string(//h_phone)')
                bis_phone = root.xpath('string(//b_phone)')
                capital_phone = root.xpath('string(//cap_phone)')
                other_phone = root.xpath('string(//oth_phone)')
                org_info = root.xpath('string(//org_info)')
                email_name = root.xpath('string(//email_address)')
                email = '%s@%s.ms.gov' % (email_name, chamber)
                if party == 'D':
                    party = 'Democratic'
                else:
                    party = 'Republican'

                leg = Legislator(term, chamber, district, leg_name, first_name,
                                 last_name, middle_name, party, role=role,
                                 home_phone = home_phone, bis_phone=bis_phone,
                                 capital_phone=capital_phone,
                                 other_phone=other_phone, org_info=org_info,
                                 email=email)
                leg.add_source(url)
                self.save_legislator(leg)
        except scrapelib.HTTPError, e:
            self.warning(str(e))

