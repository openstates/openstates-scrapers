import re
import string

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

import lxml.html
import xlrd

excel_mapping = {
    'district': 0,
    'town_represented': 2,
    'full_name': 3,
    'party': 4,
    'address': 5,
    'email': 6,
}

class RILegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ri'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'upper':
            url = ('http://webserver.rilin.state.ri.us/Documents/Senators.xls')
            rep_type = 'Senator'
            source_url = 'http://www.rilin.state.ri.us/senators/default.aspx'
            source_url_title_replacement = rep_type
            contact_url = 'http://webserver.rilin.state.ri.us/Email/SenEmailListDistrict.asp'
        elif chamber == 'lower':
            url = ('http://webserver.rilin.state.ri.us/Documents/Representatives.xls')
            rep_type = 'Representative'
            source_url = 'http://www.rilin.state.ri.us/representatives/default.aspx'
            source_url_title_replacement = 'Rep. '
            contact_url = 'http://webserver.rilin.state.ri.us/Email/RepEmailListDistrict.asp'

        self.urlretrieve(url, 'ri_leg.xls')

        wb = xlrd.open_workbook('ri_leg.xls')
        sh = wb.sheet_by_index(0)

        # This isn't perfect but it's cheap and better than using the
        # XLS doc as the source URL for all legislators.
        # 374: RI: legislator url
        leg_source_url_map = {}
        leg_page = self.lxmlize(source_url)

        for link in leg_page.xpath('//td[@class="ms-vb2"]'):
            leg_name = link.text_content().replace(source_url_title_replacement,'')
            leg_url = link.xpath("..//a")[0].attrib['href']
            leg_source_url_map[leg_name] = leg_url

        for rownum in xrange(1, sh.nrows):
            d = {}
            for field, col_num in excel_mapping.iteritems():
                d[field] = sh.cell(rownum, col_num).value

            if d['full_name'].upper() == "VACANT":
                self.warning(
                    "District {}'s seat is vacant".format(int(d['district'])))
                continue

            slug = re.match(
                "(?P<class>sen|rep)-(?P<slug>.*)@(rilin\.state\.ri\.us|rilegislature\.gov)", d['email']
            )
            
            if 'asp' in d['email']:
                d['email'] = None

            if d['email'] is not None:
                info = slug.groupdict()
                info['chamber'] = "senators" if info['class'] == 'sen' else "representatives"

                url = ("http://www.rilin.state.ri.us/{chamber}/"
                       "{slug}/Pages/Biography.aspx".format(**info))

            dist = str(int(d['district']))
            district_name = dist

            assert d['full_name'].startswith(rep_type), "Improper name found"
            full_name = re.sub(r"^{}(?=\s?[A-Z].*$)".format(rep_type), '', d['full_name']).strip()
            translate = {
                "Democrat"    : "Democratic",
                "Republican"  : "Republican",
                "Independent" : "Independent"
            }

            homepage_url = None
            url_names = lxml.html.fromstring(self.get(source_url).text)
            url_names = url_names.xpath('//td[@class="ms-vb2"]/a/@href')
            modified_name = re.sub(r'[^\w\s]', '', full_name)
            modified_name = modified_name.replace(' ', '').strip('').lower()

            for el in url_names:
                if 'default.aspx' in el:
                    el = el.replace('default.aspx', '')
                    el = el.strip('')
                if el[-1] == '/':
                    el = el[:-1]
                el = el.lower()
                url_name_array = el.split('/')
                if url_name_array[-1] in modified_name:
                    #remove '/default.aspx' and add last name
                    homepage_url = source_url[:-12] + url_name_array[-1]

            kwargs = {
                "town_represented": d['town_represented'],
            }

            contact = self.lxmlize(contact_url)
            contact_phone = contact.xpath('//tr[@valign="TOP"]//td[@class="bodyCopy"]/text() | //td[@class="bodyCopy"]//center/text()')

            phone = None
            for el in contact_phone:
                if len(el) <= 2 and dist == el:
                    number = contact_phone.index(el)
                    phone = contact_phone[number + 2]
                    phone = phone.strip()

            email = None
            if d['email'] is not None:
                email = d['email']

            if homepage_url is not None:
                kwargs['url'] = homepage_url

            if d['address'] is '':
                d['address'] = 'No Address Found'

            leg = Legislator(term, chamber, district_name, full_name,
                             '', '', '',
                             translate[d['party']],
                             **kwargs)

            leg.add_office('district', 'Dictrict Office', address=d['address'], phone=phone, email=email)
            leg.add_source(source_url)
            leg.add_source(contact_url)
            if homepage_url:
                leg.add_source(homepage_url)
            self.save_legislator(leg)
