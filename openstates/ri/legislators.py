import re
import datetime

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

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

class RILegislatorScraper(LegislatorScraper):
    jurisdiction = 'ri'
    latest_only = True

    def lxmlize(self, url):
        page = self.urlopen(url)
        if page.response.code != 200:
            raise ValueError("HTTP: {}".format(page.response.code))
        root = lxml.html.fromstring(page)
        root.make_links_absolute(url)
        return root

    def scrape(self, chamber, term):
        if chamber == 'upper':
            url = ('http://webserver.rilin.state.ri.us/Documents/Senators.xls')
            rep_type = 'Senator '
            source_url = 'http://www.rilin.state.ri.us/senators/default.aspx'
            source_url_title_replacement = rep_type
        elif chamber == 'lower':
            url = ('http://webserver.rilin.state.ri.us/Documents/Representatives.xls')
            rep_type = 'Representative '
            source_url = 'http://www.rilin.state.ri.us/representatives/default.aspx'
            source_url_title_replacement = 'Rep. '

        self.urlretrieve(url, 'ri_leg.xls')

        wb = xlrd.open_workbook('ri_leg.xls')
        sh = wb.sheet_by_index(0)

        # This isn't perfect but it's cheap and better than using the
        # XLS doc as the source URL for all legislators.
        # 374: RI: legislator url
        leg_source_url_map = {}
        leg_page = lxml.html.fromstring(self.urlopen(source_url))
        leg_page.make_links_absolute(source_url)

        for link in leg_page.xpath('//td[@class="ms-vb2"]'):
            leg_name = link.text_content().replace(source_url_title_replacement,'')
            leg_url = link.xpath("..//a")[0].attrib['href']
            leg_source_url_map[leg_name] = leg_url

        for rownum in xrange(1, sh.nrows):
            d = {
                "phone": None
            }
            for field, col_num in excel_mapping.iteritems():
                d[field] = sh.cell(rownum, col_num).value

            if d['full_name'] == "VACANT":
                self.warning(
                    "District {}'s seat is vacant".format(int(d['district'])))
                continue

            slug = re.match(
                "(?P<class>sen|rep)-(?P<slug>.*)@rilin\.state\.ri\.us", d['email']
            )
            if 'asp' in d['email']:
                d['email'] = None

            if d['email'] is not None:
                info = slug.groupdict()
                info['chamber'] = "senators" if info['class'] == 'sen' else "representatives"

                url = ("http://www.rilin.state.ri.us/{chamber}/"
                       "{slug}/Pages/Biography.aspx".format(**info))

                page = self.lxmlize(url)
                for el in page.xpath("//div[@id='WebPartWPQ4']//div//span/text()"):
                    if re.match("\(\d{3}\) \d{3}-\d{4}", el):
                        d['phone'] = el


            dist = str(int(d['district']))
            district_name = dist
            full_name = re.sub(rep_type, '', d['full_name']).strip()
            translate = {
                "Democrat"    : "Democratic",
                "Republican"  : "Republican",
                "Independent" : "Independent"
            }

            homepage_url = None
            if full_name in leg_source_url_map.keys():
                homepage_url = leg_source_url_map[full_name]

            kwargs = {
                "town_represented": d['town_represented'],
            }

            if d['email'] is not None:
                kwargs['email'] = d['email']

            if d['phone'] is not None:
                kwargs['phone'] = d['phone']

            if homepage_url is not None:
                kwargs['url'] = homepage_url

            leg = Legislator(term, chamber, district_name, full_name,
                             '', '', '',
                             translate[d['party']],
                             **kwargs)

            leg.add_office('district', 'Address', address=d['address'])
            leg.add_source(source_url)
            if homepage_url:
                leg.add_source(homepage_url)
            self.save_legislator(leg)
