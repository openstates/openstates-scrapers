from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from billy.scrape.committees  import Committee

import lxml.html
import re, contextlib

CO_BASE_URL = "http://www.leg.state.co.us/"

def clean_input( line ):
    if line != None:
        return re.sub( " +", " ", re.sub( "(\n|\r)+", " ", line ))

class COLegislatorScraper(LegislatorScraper):
    state = 'co'

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
        with self.urlopen(next_page) as html:
            page = lxml.html.fromstring(html)
            # Alright. We'll get all the districts.
            dID = page.xpath( "//div[@id='viewBody']" )[0] # should be only one
            distr = dID.xpath( "./table/tr/td/b/font/a" ) # What a mess...
            for d in distr:
                url = CO_BASE_URL + d.attrib['href']
                ret[d.text] = url

            nextPage = page.xpath( "//table/tr" )
            navBar = nextPage[0]
            np = CO_BASE_URL + navBar[len(navBar) - 1][0].attrib['href']
            #     ^ TR   ^^^^ TD         ^^^ a
            if not next_page == np:
                subnodes = self.scrape_directory( np, chamber, session )
                for node in subnodes:
                    ret[node] = subnodes[node]
            return ret

    def normalize_party( self, party_id ):
        try:
            return { "R" : "Republican", "D" : "Democrat" }[party_id]
        except KeyError as e:
            return "Other"

    def parse_homepage_for_ctty( self, hp_url ):
        ret = []
        with self.urlopen(hp_url) as html:
            page = lxml.html.fromstring(html)
            ctty_apptmts = page.xpath('//ul/li/b/a')
            for ctty in ctty_apptmts:
                cttyid = clean_input(ctty.text)
                if cttyid != None:
                    ret.append(cttyid)
        return ret

    def process_person( self, p_url ):
        ret = {}

        with self.urlopen(p_url) as html:
            page = lxml.html.fromstring(html)
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

            if len(urls) > 0:
                home_page = urls[0]
                # home_page.attrib['href']
                ret['ctty'] = self.parse_homepage_for_ctty(
                    home_page.attrib['href'] )

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
                occupation=metainf['occupation'])
            p.add_source( p_url )

            if 'ctty' in metainf:
                print metainf['ctty']
                for ctty in metainf['ctty']:
                    p.add_role( 'committee member',
                        term=session,
                        chamber=chamber,
                        committee=ctty,
                        position="member"
                    )
            self.save_legislator( p )
