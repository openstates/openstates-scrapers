from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from billy.scrape.committees  import Committee

import lxml.html
import re, contextlib

CO_BASE_URL = "http://www.leg.state.co.us/"

CTTY_BLACKLIST = [ # Invalid HTML causes us to snag these tags. Super annoying.
    "Top",
    "State Home",
    "Colorado Legislature"
]


def clean_committee(name):
    committee_name = name.replace("&", " and ")
    return re.sub("\s+", " ", committee_name).strip()


def clean_input( line ):
    if line != None:
        return re.sub( " +", " ", re.sub( "(\n|\r)+", " ", line ))


class COLegislatorScraper(LegislatorScraper):
    jurisdiction = 'co'

    def get_district_list(self, chamber, session ):
        session = session[:4] + "A"

        chamber = {
            "upper" : "%5Ce.%20Senate%20Districts%20&%20Members",
            "lower" : "h.%20House%20Districts%20&%20Members"
        }[chamber]

        url = "http://www.leg.state.co.us/clics/clics" + session + \
            "/directory.nsf/Pink%20Book/" + chamber + "?OpenView&Start=1"
        return url

    def scrape_directory(self, next_page, chamber, session):
        ret = {}
        html = self.urlopen(next_page)
        page = lxml.html.fromstring(html)
        # Alright. We'll get all the districts.
        dID = page.xpath( "//div[@id='viewBody']" )[0] # should be only one
        distr = dID.xpath( "./table/tr/td/b/font/a" ) # What a mess...
        for d in distr:
            url = CO_BASE_URL + d.attrib['href']
            if "Save Conflict" in d.text:
                continue

            ret[d.text] = url

        nextPage = page.xpath( "//table/tr" )
        navBar = nextPage[0]
        np = CO_BASE_URL + navBar[len(navBar) - 1][0].attrib['href']
        if not next_page == np:
            subnodes = self.scrape_directory( np, chamber, session )
            for node in subnodes:
                ret[node] = subnodes[node]
        return ret

    def normalize_party( self, party_id ):
        try:
            return { "R" : "Republican", "D" : "Democratic" }[party_id]
        except KeyError as e:
            return "Other"

    def parse_homepage( self, hp_url ):
        image_base = "http://www.state.co.us/gov_dir/leg_dir/senate/members/"
        ret = []
        obj = {}
        image = ""
        html = self.urlopen(hp_url)
        page = lxml.html.fromstring(html)
        page.make_links_absolute(hp_url)

        try:
            email = page.xpath("//a[contains(@href, 'mailto')]")[0]
            email = email.attrib['href']
            email = email.split(":", 1)[1]
            obj['email'] = email
        except IndexError:
            pass
        infoblock = page.xpath("//div[@align='center']")
        info = infoblock[0].text_content()

        number = re.findall("(\d{3})(-|\))?(\d{3})-(\d{4})", info)
        if len(number) > 0:
            number = number[0]
            number = "%s %s %s" % (
                number[0],
                number[2],
                number[3]
            )
            obj['number'] = number
        ctty_apptmts = [clean_input(x) for x in
                         page.xpath("//a[contains(@href, 'CLC')]//font/text()")]

        new = []
        for entry in ctty_apptmts:
            if "--" in entry:
                ctty, _ = entry.split("--")
                new.append(ctty.strip())

        ctty_apptmts = filter(lambda x: x.strip() != "" and
                              x not in CTTY_BLACKLIST, new)

        try:
            (image,) = page.xpath("//img[contains(@src, '.jpg')]/@src")
        except ValueError:
            (image,) = page.xpath("//img[contains(@src, '.png')]/@src")

        obj.update({
            "ctty"  : ctty_apptmts,
            "photo" : image
        })
        return obj

    def process_person( self, p_url ):
        ret = { "homepage" : p_url }

        html = self.urlopen(p_url)
        page = lxml.html.fromstring(html)
        page.make_links_absolute(p_url)

        info = page.xpath( '//table/tr' )[1]
        tds = {
            "name"  : 0,
            "dist"  : 1,
            "party" : 3,
            "occup" : 4,
            "cont"  : 6
        }

        party_id = info[tds['party']].text_content()

        person_name = clean_input(info[tds['name']].text_content())
        person_name = clean_input(re.sub( '\(.*$', '', person_name).strip())
        occupation  = clean_input(info[tds['occup']].text_content())

        urls = page.xpath( '//a' )
        ret['photo_url'] = ""
        home_page = page.xpath("//a[contains(text(), 'Home Page')]")

        if home_page != []:
            home_page = home_page[0]
            ret['homepage'] = home_page.attrib['href'].strip()
            homepage = self.parse_homepage(
                home_page.attrib['href'].strip() )

            ret['ctty'] = homepage['ctty']
            ret['photo_url'] = homepage['photo']
            if "email" in homepage:
                ret['email'] = homepage['email']
            if "number" in homepage:
                ret['number'] = homepage['number']

        ret['party'] = self.normalize_party(party_id)
        ret['name']  = person_name
        ret['occupation'] = occupation
        return ret

    def scrape(self, chamber, session):
        url = self.get_district_list(chamber, session)
        people_pages = self.scrape_directory( url, chamber, session )

        for person in people_pages:
            district = person
            p_url = people_pages[district]
            metainf = self.process_person( p_url )

            p = Legislator( session, chamber, district, metainf['name'],
                party=metainf['party'],
                # some additional things the website provides:
                occupation=metainf['occupation'],
                photo_url=metainf['photo_url'],
                url=metainf['homepage'])
            if "email" in metainf:
                p['email'] = metainf['email']
            if "number" in metainf:
                p.add_office('capitol', 'Capitol Office',
                             phone=metainf['number'],
                             address='200 E. Colfax\nDenver, CO 80203'
                            )

            p.add_source( p_url )
            self.save_legislator( p )
