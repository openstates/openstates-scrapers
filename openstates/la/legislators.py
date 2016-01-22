import re

from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


def xpath_one(el, expr):
    ret = el.xpath(expr)
    if len(ret) != 1:
        print(ret, expr)
        raise Exception
    return ret[0]


class LALegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'la'
    latest_only = True

    def scrape_upper_leg_page(self, term, url, who):
        page = self.lxmlize(url)

        (who, ) = [x for x in
                   page.xpath('//tr/td/font/text()') if
                   x.strip().startswith("Senator ")
                   ]
        who = re.search(r'(?u)^\s*Senator\s*(.*?)\s*$', who).group(1)

        (district, ) = [x for x in
                        page.xpath('//tr/td/font/text()') if
                        x.strip().startswith("District - ")
                        ]
        district = re.search(
            r'(?u)^\s*District\s*-\s*(.*?)\s*$', district).group(1)

        info = [x.strip() for x in
                page.xpath('//font[contains(text(), "Information:")]/'
                'ancestor::table[1]//text()') if
                x.strip()
                ]

        parties = {
            "Republican": "Republican",
            "Democrat": "Democratic",
        }
        party_index = info.index("Party:") + 1
        party = parties[info[party_index]]

        phone_index = info.index("District Phone") + 1
        phone = info[phone_index]
        assert (sum(c.isdigit() for c in phone) == 9,
                "Phone number is invalid: {}".format(phone))

        # Address exists for all lines between party and phone
        address = "\n".join(info[party_index + 2:phone_index - 1])
        address = address.replace("\r", "")

        if not address:
            address = "No Address Found"
        
        fax_index = info.index("Fax") + 1
        fax = info[fax_index]
        assert (sum(c.isdigit() for c in fax) == 9,
                "Fax number is invalid: {}".format(fax))

        email_index = info.index("E-mail Address") + 1
        email = info[email_index]
        assert "@" in email, "Email info is not valid: {}".format(email)

        leg = Legislator(term,
                         'upper',
                         district,
                         who,
                         party=party)

        leg.add_office('district',
                       'District Office',
                       address=address,
                       phone=phone,
                       fax=fax,
                       email=email)

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

        photo = xpath_one(page, '//a[@rel="lightbox"]').attrib['href']
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
            '//div[@class="FullName"]//following-sibling::text()[1]')
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