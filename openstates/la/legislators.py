import re

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin

from .common import BackoffScraper


def xpath_one(el, expr):
    ret = el.xpath(expr)
    if len(ret) != 1:
        print(ret, expr)
        raise Exception
    return ret[0]


class LALegislatorScraper(LegislatorScraper, BackoffScraper, LXMLMixin):
    jurisdiction = 'la'
    latest_only = True

    def scrape_upper_leg_page(self, term, url, who):
        page = self.lxmlize(url)
        who = page.xpath("//font[@size='4']")
        who = who[0].text_content()
        who = re.sub("\s+", " ", who)
        who, district = (x.strip() for x in who.rsplit(" ", 1))
        who = who.replace("Senator", "").strip()
        district = district.replace("District", "").strip()

        infopane = page.xpath("//table[@cellpadding='2']")

        infos = [x.tail.strip() if x.tail else ""
                 for x in infopane[1].xpath(".//b")]
        infos2 = [x.tail.strip() if x.tail else ""
                  for x in infopane[1].xpath(".//br")]
        infos3 = [x.strip() for x in infopane[1].xpath(
            ".//a[contains(@href, 'mailto')]/text()")]

        keys = ["party", "district-office", "phone", "fax", "staffer", "email"]
        nodes = [[]]
        for node in infos:
            if node == "":
                if nodes[-1] != []:
                    nodes.append([])
                continue
            nodes[-1].append(node)
        for node in infos2:
            if node == "":
                if nodes[-1] != []:
                    nodes.append([])
                continue
            nodes[-1].append(node)
        for node in infos3:
            if node == "":
                if nodes[-1] != []:
                    nodes.append([])
                continue
            nodes[-1].append(node)

        data = dict(zip(keys, nodes))

        district_office = "\n".join(data['district-office'])

        parties = {
            "Republican": "Republican",
            "Democrat": "Democratic",
        }

        party = 'other'
        for slug in parties:
            for key, value in data.iteritems():
                if slug in value:
                    party = parties[slug]

        if party == 'other':
            raise Exception

        kwargs = {
            "party": party
        }

        leg = Legislator(term,
                         'upper',
                         district,
                         who,
                         **kwargs)

        leg.add_office('district',
                       'District Office',
                       address=district_office)

        leg.add_source(url)

        self.save_legislator(leg)

    def scrape_upper(self, chamber, term):
        url = "http://senate.la.gov/Senators/"
        page = self.lxmlize(url)
        table = page.xpath("//table[@width='96%']")[0]
        legs = table.xpath(".//tr//a[contains(@href, 'senate.la.gov')]")
        for leg in legs:
            who = leg.text_content().strip()
            if who == "":
                continue
            self.scrape_upper_leg_page(term, leg.attrib['href'], who)

    def scrape_lower_legislator(self, url, leg_info, term):
        page = self.lxmlize(url)

        name = page.xpath('//div[@class="FullName"]/text()')[0].strip()
        if name.startswith("District ") or name.startswith("Vacant "):
            self.warning("Seat is vacant: {}".format(name))
            return

        photo = xpath_one(page, '//img[@rel="lightbox"]').attrib['src']
        infoblk = xpath_one(
            page, '//td/b[contains(text(), "CAUCUS/DELEGATION MEMBERSHIP")]')
        infoblk = infoblk.getparent()
        cty = xpath_one(infoblk, "./b[contains(text(), 'ASSIGNMENTS')]")
        cty = cty.getnext()

        party_flags = {
            "Democrat": "Democratic",
            "Republican": "Republican",
            "Independent": "Independent"
        }
        party_info = page.xpath(
            '//div[@class="FullName"]/ancestor::td[1]/text()')
        (party_info, ) = [x.strip() for x in party_info if x.strip()]
        party_info = party_info.split('-')[0].strip()
        party = party_flags[party_info]

        kwargs = {"url": url,
                  "party": party,
                  "photo_url": photo}

        leg = Legislator(term,
                         'lower',
                         leg_info['dist'],
                         leg_info['name'],
                         **kwargs)

        kwargs = {
            "address": leg_info['office'],
            "phone": leg_info['phone'],
            "email": leg_info['email'],
        }
        for key in kwargs.keys():
            if not kwargs[key].strip():
                kwargs[key] = None

        leg.add_office('district',
                       'District Office',
                       **kwargs)

        leg.add_source(url)
        self.save_legislator(leg)

    def scrape_lower(self, chamber, term):
        url = "http://house.louisiana.gov/H_Reps/H_Reps_FullInfo.asp"
        page = self.lxmlize(url)
        meta = ["name", "dist", "office", "phone", "email"]
        for tr in page.xpath("//table[@id='table61']//tr"):
            tds = tr.xpath("./td")
            if tds == []:
                continue

            info = {}
            for i in range(0, len(meta)):
                info[meta[i]] = tds[i].text_content().strip()

            hrp = tr.xpath(
                ".//a[contains(@href, 'H_Reps')]")[0].attrib['href']

            self.scrape_lower_legislator(hrp, info, term)

    def scrape(self, chamber, term):
        if chamber == "upper":
            return self.scrape_upper(chamber, term)
        if chamber == "lower":
            return self.scrape_lower(chamber, term)
